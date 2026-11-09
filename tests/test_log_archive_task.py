"""日志归档任务：把 .log 按 日期/来源目录/文件名 搬进归档区。

搬运类任务最适合用 tmp_path 测：真读真写真搬，不 mock 文件系统。
"""
import os
from datetime import datetime

from framework.tasks.tasks import LogArchiveTask


def today():
    return datetime.now().strftime("%Y-%m-%d")


def make_task(log_dir, archive_dir, result=None):
    return LogArchiveTask(
        name="LogArchiveTask",
        log_dirs=[str(log_dir)],
        archive_dir=str(archive_dir),
        result=result,
    )


def test_first_run_archives_all_logs(log_dir, tmp_path):
    archive = tmp_path / "archive"
    result = make_task(log_dir, archive).run()

    assert result["status"] == "success"
    assert result["total"] == 2
    assert result["passed"] == 2
    assert result["failed"] == 0
    assert sorted(result["details"]["success_files"]) == ["app1.log", "app2.log"]


def test_files_really_moved(log_dir, tmp_path):
    """不只是"报告说成功"，要断言文件真的到了目标位置。"""
    archive = tmp_path / "archive"
    make_task(log_dir, archive).run()

    dst = archive / today() / "logs" / "app1.log"
    assert dst.exists()
    assert dst.read_text(encoding="utf-8") == "line1\n"
    assert os.listdir(log_dir) == []


def test_retry_only_touches_failed_items(log_dir, tmp_path):
    """重试模式：result 里有 failed_items，就只搬这几个，不重新全量扫。"""
    archive = tmp_path / "archive"
    target = str(log_dir / "app1.log")

    result = make_task(log_dir, archive, result={"failed_items": [target]}).run()

    assert result["total"] == 1
    assert result["passed"] == 1
    assert (archive / today() / "logs" / "app1.log").exists()
    assert (log_dir / "app2.log").exists()


def test_move_failure_is_reported(log_dir, tmp_path):
    """源文件不存在（比如上一次已经搬走）：记成 failed，不崩。"""
    archive = tmp_path / "archive"
    ghost = str(log_dir / "已经没了.log")

    result = make_task(log_dir, archive, result={"failed_items": [ghost]}).run()

    assert result["status"] == "failure"
    assert result["failed"] == 1
    assert result["failed_items"] == [ghost]
    assert result["details"]["failed_files"][0][0] == "已经没了.log"


def test_empty_dir_is_success(tmp_path, log_dir):
    empty = tmp_path / "empty"
    empty.mkdir()
    result = make_task(empty, tmp_path / "archive").run()

    assert result["status"] == "success"
    assert result["total"] == 0
