# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22
import traceback
from queue import Queue
import threading


class Scheduler:
    def __init__(self, executor, result_recorder, retry_policy, on_task_complete=None):
        self.tasks = Queue()
        self.task_names = set()
        self.success_task_names = set()
        self.executor = executor
        self.retry_policy = retry_policy
        self.result_recorder = result_recorder
        self.lock = threading.Lock()
        self.on_task_complete = on_task_complete

    def store_tasks(self, task):
        with self.lock:
            if task.name in self.success_task_names:
                return

            if task.name in self.task_names:
                return

            self.tasks.put(task)
            self.task_names.add(task.name)

    def wait_all_done(self):
        """等待队列中所有任务完成（包括动态加入的下游任务）"""
        self.tasks.join()  # 阻塞，直到所有 task_done() 被调用

    def run_task(self):
        while True:
            task = self.tasks.get()
            if task is None:
                self.tasks.task_done()
                break
            try:
                result = self.executor.execute_with_retry(task, self.retry_policy)
                self.result_recorder.record(task_name=task.name, result=result)
                # 在任务执行完、记录结果之后
                if self.on_task_complete:
                    self.on_task_complete()
                print(f"[DEBUG] {threading.current_thread().name} 完成任务: {task.name}")

                with self.lock:
                    self.success_task_names.add(task.name)
            except Exception as e:
                traceback.print_exc()
                print(f"{task.name} 执行失败: {e}")
            finally:
                with self.lock:
                    self.task_names.discard(task.name)
                self.tasks.task_done()
