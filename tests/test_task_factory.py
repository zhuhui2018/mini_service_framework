"""任务工厂：按类的 __init__ 签名，只把"它认识的参数"传进去。

为什么要它：下游分支统一传 result/original_task_name，
但 ReportTask 不认识 test_dir、PytestTask 不认识 archive_dir。
没有工厂，就得为每个类写一堆 if —— 加新任务就要改调用方。
"""
import pytest

from framework.core.task_factory import TaskFactory
from framework.tasks.tasks import LogArchiveTask, ReportTask


def test_only_passes_known_params(tmp_path):
    """ReportTask 不认识 test_dir，传了也不会报错，会被丢弃。"""
    task = TaskFactory.create(
        ReportTask,
        name="report",
        result={"total": 1, "passed": 1, "failed": 0},
        test_dir=str(tmp_path),
    )
    assert isinstance(task, ReportTask)
    assert task.name == "report"
    assert not hasattr(task, "test_dir")


def test_missing_required_param_raises():
    """必需参数没给，照样报 TypeError —— 工厂不是万能的。

    这也是它在面试里的价值：它解决的是"多余参数"，不是"缺参数"。
    缺参数属于调用方写错了，就该早点炸。
    """
    with pytest.raises(TypeError):
        TaskFactory.create(ReportTask, name="report")


def test_builds_log_archive_task(tmp_path):
    task = TaskFactory.create(
        LogArchiveTask,
        name="archive",
        log_dirs=str(tmp_path),
        archive_dir=str(tmp_path / "archive"),
        result=None,
    )
    assert isinstance(task, LogArchiveTask)
    assert task.log_dirs == [str(tmp_path)]


def test_string_log_dir_is_wrapped_in_list(tmp_path):
    """LogArchiveTask 自己会兼容"传一个字符串"和"传一个列表"。"""
    task = TaskFactory.create(
        LogArchiveTask,
        name="archive",
        log_dirs=str(tmp_path),
        archive_dir=str(tmp_path / "archive"),
    )
    assert isinstance(task.log_dirs, list)
    assert len(task.log_dirs) == 1
