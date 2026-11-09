"""报告任务：把上一条任务的 result 打成人能看的几行。

它同时是"链的终点"（is_terminal = True），所以顺手断言这个标记——
Service 靠它决定"要不要停整个框架"。
"""
from framework.tasks.tasks import ReportTask


def test_report_with_failures(capsys):
    task = ReportTask(
        name="report",
        result={
            "total": 9,
            "passed": 7,
            "failed": 2,
            "failed_items": ["a.py::test_x", "b.py::test_y"],
        },
    )
    out = task.run()

    printed = capsys.readouterr().out
    assert "总用例数: 9" in printed
    assert "通过: 7" in printed
    assert "失败: 2" in printed
    assert "a.py::test_x" in printed
    assert out == {"status": "report_generated", "total": 9, "passed": 7, "failed": 2}


def test_report_without_failures(capsys):
    task = ReportTask(name="report", result={"total": 5, "passed": 5, "failed": 0})
    task.run()

    printed = capsys.readouterr().out
    assert "无失败用例" in printed


def test_report_is_terminal():
    assert ReportTask.is_terminal is True
