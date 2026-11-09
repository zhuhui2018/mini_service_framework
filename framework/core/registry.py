# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22

class Registry:
    def __init__(self):
        self.tasks = {}
        self.triggers = {}

    def register_tasks(self, name, task):
        self.tasks[name] = task

    def get_task(self, name):
        return self.tasks[name]

    def exists(self, name):
        return name in self.tasks

    def register_trigger(self, name, trigger):
        self.triggers[name] = trigger
