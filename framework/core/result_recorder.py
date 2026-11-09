# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22

class ResultRecorder:
    def __init__(self):
        self.results = []

    def record(self, task_name, result):
        self.results.append({
            "task_name": task_name,
            "result": result
        })
