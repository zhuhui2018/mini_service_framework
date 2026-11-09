# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22

class Deduplicator:
    def __init__(self):
        self.tasks = set()
        self.task_names = set()

    def is_deduplication(self, task):
        if task.name not in self.task_names:
            self.tasks.add(task)
            self.task_names.add(task.name)
            return True
        else:
            return False
