# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22
import threading
import time
from datetime import datetime
from croniter import croniter


class Trigger:
    # 定义一个trigger类，trigger的作用是触发条件时把任务加入到调度器中
    def __init__(self, name, registry, scheduler, validator,
                 interval=5, cron=None, max_triggers=1):
        # 初始化，需要任务名称，注册对象，调度对象和校验对象
        self.max_triggers = max_triggers
        self.trigger_count = 0
        self.name = name
        self.registry = registry
        self.scheduler = scheduler
        self.validator = validator
        self.interval = interval
        self.last_trigger_time = 0
        self.stop_event = threading.Event()
        self.thread = None
        self.has_triggered = False
        self.cron = cron

    def start(self):
        self.thread = threading.Thread(target=self._loop)
        self.thread.start()

    def _loop(self):
        while not self.stop_event.is_set():
            if self.cron:
                cron = croniter(self.cron, datetime.now())
                next_time = cron.get_next(datetime)
                wait_seconds = (next_time - datetime.now()).total_seconds()
                if self.stop_event.wait(timeout=wait_seconds):
                    break
            else:
                if self.stop_event.wait(timeout=self.interval):
                    break
            self.trigger()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join()

    def trigger(self):
        if self.trigger_count >= self.max_triggers:
            return
        self.trigger_count += 1

        print(f"[DEBUG] trigger() 被调用了，时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        # 定义一个trigger方法，如果说触发的任务不在注册表中，提示任务不存在，反之如果校验规则通过，则从注册对象中取出任务
        # 并且把任务加入到调度表中
        now = time.time()
        if now - self.last_trigger_time >= self.interval:
            self.last_trigger_time = now
            if not self.registry.exists(self.name):
                return
            if self.validator.validate():
                print("是否校验通过了")
                task = self.registry.get_task(self.name)
                print(f"[DEBUG] 从 registry 取任务: {self.name}, "
                      f"结果: {self.registry.get_task(self.name)}")
                self.scheduler.store_tasks(task)
                print(f"[DEBUG] 任务 {self.name} 已放入队列")
            self.has_triggered = True