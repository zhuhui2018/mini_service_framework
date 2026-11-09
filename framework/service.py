# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22
import threading
import time

from framework.core.executor import Executor
from framework.core.registry import Registry
from framework.core.result_recorder import ResultRecorder
from framework.core.retry_policy import RetryPolicy
from framework.core.scheduler import Scheduler
from framework.core.task_factory import TaskFactory
from framework.tasks.tasks import AlertTask


class Service:
    def __init__(self):
        self.is_running = False
        self.registry = Registry()
        self.result_recorder = ResultRecorder()
        self.executor = Executor()
        self.retry_policy = RetryPolicy(max_retry_count=3, gap_time=1)
        self.scheduler = Scheduler(self.executor, self.result_recorder,
                                   self.retry_policy,
                                   on_task_complete=self._check_and_trigger_downstream)
        self.triggers = []
        self.workers = []
        self.chains = []
        self.branches = []

    def add_chain(self, chain):
        self.chains.append(chain)

    def add_branch(self, branch):
        self.branches.append(branch)

    def store_triggers(self, trigger):
        self.triggers.append(trigger)

    def register_task(self, name, task):
        self.registry.register_tasks(name, task)

    def start(self):
        if not self.is_running:
            self.is_running = True

            for i in range(3):
                worker = threading.Thread(target=self.scheduler.run_task)
                self.workers.append(worker)
                print(f"[DEBUG] 创建 {worker.name}")
                worker.start()

            while self.is_running:
                self._check_and_trigger_downstream()
                time.sleep(2)


    def _check_and_trigger_downstream(self):

        if not self.result_recorder.results:
            return

        last = self.result_recorder.results[-1]

        # ← 加在这里
        current_task = self.registry.get_task(last["task_name"])
        if getattr(current_task, "is_terminal", False):
            self.is_running = False
            return

        failure_counts = {}
        retry_count = 0
        task = None

        # 先确定当前这条链的源头
        original = last["result"].get("original_task_name") or last["task_name"]

        for item in self.result_recorder.results:
            task = self.registry.get_task(item["task_name"])
            if task.retryable:
                if item["result"].get("original_task_name") == original:
                    if item["result"].get("failed") >0:
                        retry_count += 1
                        failure_counts[item["task_name"]] = retry_count



        failed_task_name = f"{original}_retry_{retry_count + 1}"

        current_count = failure_counts.get(last["task_name"], 0)
        if current_count >= current_task.max_retries:
            alert_task = AlertTask(
                name="alert_task",
                message=f"任务 {last['task_name']} 连续失败 {retry_count} 次"
            )
            self.registry.register_tasks(name="alert_task", task=alert_task)
            self.scheduler.store_tasks(task=alert_task)
            return

        failed = last["result"].get("failed", 0)

        for branch in self.branches:
            if not last["task_name"] == branch.upstream_name and \
                not last["task_name"].startswith("failed_retry"):
                continue

            for b in branch.branches:

                matched = False

                if b["condition"].get("failed") == ">0" and failed > 0:
                    matched = True

                if b["condition"].get("failed") == "==0" and failed ==0:
                    matched = True

                if not matched:
                    continue

                print("创建任务时 original_task_name =", last["result"].get("original_task_name") or last["task_name"])
                # 修改后的代码
                task = TaskFactory.create(
                    b["downstream_class"],
                    name=failed_task_name,
                    result=last["result"],
                    original_task_name=last["result"].get("original_task_name") or last["task_name"],
                    **b.get("extra_params", {})
                )

                self.registry.register_tasks(name=failed_task_name, task=task)
                self.scheduler.store_tasks(task=task)
                break

    def stop(self):
        self.is_running = False
        for _ in self.workers:
            self.scheduler.tasks.put(None)
        for worker in self.workers:
            worker.join()

    def wait_all_done(self):
        """等待所有任务完成（包括下游触发产生的任务）
        scheduler中的代码是
        self.tasks.join() 意思是等所有任务结束
        """
        self.scheduler.wait_all_done()
