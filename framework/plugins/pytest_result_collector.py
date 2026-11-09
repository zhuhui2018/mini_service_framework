# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22

class PytestResultCollector:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.skipped = []

    def pytest_runtest_logreport(self, report):
        # 一个用例会有 setup / call / teardown 三个阶段
        # 我们这里只统计真正执行测试函数的 call 阶段
        if report.when != "call":
            return

        if report.passed:
            self.passed.append(report.nodeid)
        elif report.failed:
            self.failed.append(report.nodeid)
        elif report.skipped:
            self.skipped.append(report.nodeid)

