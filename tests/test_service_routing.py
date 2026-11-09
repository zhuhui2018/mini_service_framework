"""编排层：任务跑完之后，下一步派谁。

这是整个框架里最像"大脑"的一段逻辑，也是最好用用例钉住的地方——
因为它的输入只有一个（最后一条结果），输出只有一个（队列里多了什么任务）。
"""
import pytest

from framework.service import Service
from framework.support.branch_chain import BranchChain
from framework.tasks.tasks import PytestTask, ReportTask


def build_service(tmp_path):
    svc = Service()
    svc.register_task("PytestTask", PytestTask("PytestTask", str(tmp_path)))
    svc.add_branch(BranchChain(
        upstream_name="PytestTask",
        branches=[
            {
                "condition": {"failed": ">0"},
                "downstream_class": PytestTask,
                "downstream_name": "failed_retry",
                "extra_params": {"test_dir": str(tmp_path)},
            },
            {
                "condition": {"failed": "==0"},
                "downstream_class": ReportTask,
                "downstream_name": "generate_report",
            },
        ],
    ))
    return svc


def next_task(svc):
    assert svc.scheduler.tasks.qsize() == 1, "队列里应该正好有一个下游任务"
    return svc.scheduler.tasks.get_nowait()


def test_no_result_does_nothing(tmp_path):
    svc = build_service(tmp_path)
    svc._check_and_trigger_downstream()
    assert svc.scheduler.tasks.qsize() == 0


def test_failed_result_spawns_retry_task(tmp_path):
    svc = build_service(tmp_path)
    svc.result_recorder.record("PytestTask", {
        "failed": 2, "total": 3, "passed": 1, "failed_items": ["a.py::test_x"],
    })

    svc._check_and_trigger_downstream()

    task = next_task(svc)
    assert isinstance(task, PytestTask)
    assert task.name.startswith("PytestTask_retry")
    assert task.original_task_name == "PytestTask"


def test_passed_result_spawns_report_task(tmp_path):
    svc = build_service(tmp_path)
    svc.result_recorder.record("PytestTask", {
        "failed": 0, "total": 3, "passed": 3, "failed_items": [],
    })

    svc._check_and_trigger_downstream()

    task = next_task(svc)
    assert isinstance(task, ReportTask)
    assert task.result["total"] == 3


def test_terminal_task_stops_service(tmp_path):
    """报告任务跑完 -> 整个框架停下（对应你清单里的第 9 项）。"""
    svc = build_service(tmp_path)
    svc.is_running = True
    svc.register_task("ReportTask", ReportTask("ReportTask", {"failed": 0}))
    svc.result_recorder.record("ReportTask", {"failed": 0})

    svc._check_and_trigger_downstream()

    assert svc.is_running is False
    assert svc.scheduler.tasks.qsize() == 0


def test_unknown_upstream_is_ignored(tmp_path):
    """上游名字对不上任何分支：什么也不派。

    这就是你第 8 项优化的起点——现在只有一个 upstream_name 能匹配，
    多链并行时会漏。用例先把这个"现状"写下来，改的时候才有对照。
    """
    svc = build_service(tmp_path)
    svc.register_task("OtherTask", PytestTask("OtherTask", str(tmp_path)))
    svc.result_recorder.record("OtherTask", {"failed": 1})

    svc._check_and_trigger_downstream()

    assert svc.scheduler.tasks.qsize() == 0


def test_retry_chain_stalls_and_never_stops(tmp_path):
    """现状（真实缺陷）：重试也失败之后，整个框架"什么都不做，也停不下来"。

    走一遍真实顺序：
        第 1 轮  PytestTask 失败 -> 派一个重试任务（名字 PytestTask_retry_2）
        第 2 轮  重试任务也失败 -> 队列空了，但 is_running 还是 True

    为什么第 2 轮不再派任务：
        分支匹配那行写的是
            last["task_name"] == branch.upstream_name
            or last["task_name"].startswith("failed_retry")
        而重试任务的名字是 PytestTask_retry_2，两条件都不满足，
        所以所有分支都被跳过 —— 链条在这里断了。

    后果：main.py 里的
            while service.is_running: time.sleep(0.5)
        会一直转下去，程序不退出、告警不触发。
    这正是你清单第 9 项要解决的问题，先用用例把它固定下来。
    """
    svc = build_service(tmp_path)
    svc.is_running = True

    svc.result_recorder.record("PytestTask", {
        "failed": 2, "total": 3, "passed": 1, "failed_items": [],
    })
    svc._check_and_trigger_downstream()
    retry_task = next_task(svc)
    assert isinstance(retry_task, PytestTask)
    assert retry_task.name.startswith("PytestTask_retry")

    svc.register_task(retry_task.name, retry_task)
    svc.result_recorder.record(retry_task.name, {
        "failed": 2, "total": 2, "passed": 0,
        "failed_items": [], "original_task_name": "PytestTask",
    })
    svc._check_and_trigger_downstream()

    assert svc.scheduler.tasks.qsize() == 0, "链断了，不会再派任务"
    assert svc.is_running is True, "但服务没停 —— 这就是卡死"
