"""pytest 插件：只统计 call 阶段，把结果分成 passed / failed / skipped。

不启动真 pytest，直接造一个"假 report"喂给 hook ——
这就是单元测试的好处：被测对象只要一个带属性的对象，不用真跑。
"""
from framework.plugins.pytest_result_collector import PytestResultCollector


class FakeReport:
    def __init__(self, nodeid, when="call", outcome="passed"):
        self.nodeid = nodeid
        self.when = when
        self.passed = outcome == "passed"
        self.failed = outcome == "failed"
        self.skipped = outcome == "skipped"


def collect(reports):
    c = PytestResultCollector()
    for r in reports:
        c.pytest_runtest_logreport(r)
    return c


def test_passed_case():
    c = collect([FakeReport("t.py::test_a")])
    assert c.passed == ["t.py::test_a"]
    assert c.failed == []


def test_failed_case():
    c = collect([FakeReport("t.py::test_b", outcome="failed")])
    assert c.failed == ["t.py::test_b"]
    assert c.passed == []


def test_skipped_case():
    c = collect([FakeReport("t.py::test_c", outcome="skipped")])
    assert c.skipped == ["t.py::test_c"]


def test_one_case_three_phases_counted_once():
    """一个用例会走 setup / call / teardown 三个阶段，只能算一次。"""
    node = "t.py::test_a"
    c = collect([
        FakeReport(node, when="setup"),
        FakeReport(node, when="call"),
        FakeReport(node, when="teardown"),
    ])
    assert c.passed == [node]
    assert len(c.passed) == 1


def test_setup_failure_is_ignored():
    """现状：fixture 挂了（setup 阶段 failed）不计入 failed。

    后果：这种用例会被"漏掉"——报告里总数比实际跑的少，
    失败数也少一个，看起来一切正常。这是真实的统计缺口。

    修法：setup 阶段 failed 也要记（一般记为 error 单独一列）。
    先钉住现状，改的时候这条用例会红，提醒你"行为变了"。
    """
    c = collect([FakeReport("t.py::test_d", when="setup", outcome="failed")])
    assert c.failed == []


def test_mixed_results():
    c = collect([
        FakeReport("t.py::test_a"),
        FakeReport("t.py::test_b", outcome="failed"),
        FakeReport("t.py::test_c", outcome="skipped"),
    ])
    assert len(c.passed) == 1
    assert len(c.failed) == 1
    assert len(c.skipped) == 1
