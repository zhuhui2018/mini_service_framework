"""校验器：触发器"要不要触发"就靠它回答一个 True/False。

这一层最适合练习写用例：没有线程、没有 sleep、输入是一个目录，输出是布尔值。
"""
import pytest

from framework.support.validate import (
    AndValidator,
    FilePatternValidator,
    FileValidator,
    LogArchiveValidator,
    LogValidator,
    PytestValidator,
)


def test_file_validator_exist_and_missing(tmp_path):
    assert FileValidator(str(tmp_path)).validate() is True
    assert FileValidator(str(tmp_path / "不存在")).validate() is False


def test_file_pattern_validator(log_dir):
    """.log 有匹配 -> True；.csv 没匹配 -> False。"""
    assert FilePatternValidator(str(log_dir), ".log").validate() is True
    assert FilePatternValidator(str(log_dir), ".csv").validate() is False


def test_file_pattern_validator_missing_dir(tmp_path):
    """目录不存在时返回 False，不抛异常——这是它比 LogArchiveValidator 稳的地方。"""
    assert FilePatternValidator(str(tmp_path / "没有这个目录"), ".log").validate() is False


def test_and_validator(log_dir):
    ok = FileValidator(str(log_dir))
    bad = FilePatternValidator(str(log_dir), ".csv")
    assert AndValidator(ok).validate() is True
    assert AndValidator(ok, ok).validate() is True
    assert AndValidator(ok, bad).validate() is False
    assert AndValidator(bad, ok).validate() is False


def test_log_validator_needs_txt(tmp_path):
    d = tmp_path / "txt_only"
    d.mkdir()
    (d / "a.txt").write_text("x", encoding="utf-8")
    assert LogValidator(str(d)).validate() is True


def test_log_archive_validator(log_dir):
    assert LogArchiveValidator(str(log_dir)).validate() is True


def test_log_archive_validator_missing_dir_raises(tmp_path):
    """现状：目录不存在时直接 FileNotFoundError，没做防御。

    这是真实缺陷：trigger 里 validate() 没有 try/except，
    一旦配错路径（比如换电脑后路径失效），触发器线程会直接崩掉，
    而且是"静默崩"——主线程还在 sleep，你看不出发生了什么。

    修法：目录不存在时返回 False（和 FilePatternValidator 保持一致）。
    先把这个行为钉住，等你优化时改这里，用例会提醒你"行为变了"。
    """
    with pytest.raises(FileNotFoundError):
        LogArchiveValidator(str(tmp_path / "不存在")).validate()


def test_pytest_validator_always_true():
    assert PytestValidator().validate() is True
