"""pytest 任务：扫目录 -> 拼 nodeid -> 交给 pytest 跑 -> 把结果翻译成框架要的格式。

关键手法：把模块级的 `pytest` 换成一个假的（monkeypatch），
这样就不会在测试里再嵌套跑一遍 pytest。
真要嵌嵌套跑，pytest 会报 "cannot run pytest nested"，
而且耗时、还会污染当前会话的结果——所以这里必须打桩。
"""
import os

import pytest

from framework.tasks.tasks import PytestTask


class FakePytest:
    """冒充 pytest 模块：只需要一个 main()。"""

    def __init__(self, passed=(), failed=(), skipped=()):
        self._passed = list(passed)
        self._failed = list(failed)
        self._skipped = list(skipped)
        self.last_args = None

    def main(self, args, plugins):
        self.last_args = args
        collector = plugins[0]
        collector.passed.extend(self._passed)
        collector.failed.extend(self._failed)
        collector.skipped.extend(self._skipped)
        return 1 if self._failed else 0


@pytest.fixture
def case_dir(tmp_path):
    d = tmp_path / "cases"
    d.mkdir()
    (d / "test_demo.py").write_text(
        "def test_a():\n    assert 1 == 1\n\n\ndef test_b():\n    assert 1 == 2\n",
        encoding="utf-8",
    )
    return d


@pytest.fixture
def patch_pytest(monkeypatch):
    def _patch(**kwargs):
        fake = FakePytest(**kwargs)
        monkeypatch.setattr("framework.tasks.tasks.pytest", fake)
        return fake
    return _patch


def test_run_all_cases(case_dir, patch_pytest):
    node_a = f"{case_dir / 'test_demo.py'}::test_a"
    node_b = f"{case_dir / 'test_demo.py'}::test_b"
    patch_pytest(passed=[node_a], failed=[node_b])

    result = PytestTask("PytestTask", str(case_dir)).run()

    assert result["status"] == "failure"
    assert result["total"] == 2
    assert result["passed"] == 1
    assert result["failed"] == 1
    assert result["details"]["exit_code"] == 1


def test_failed_items_become_absolute_paths(case_dir, patch_pytest):
    """失败项要变成绝对路径，因为下一次重试要拿它当"要跑哪些用例"的输入。"""
    node_b = f"{case_dir / 'test_demo.py'}::test_b"
    patch_pytest(passed=[], failed=[node_b])

    result = PytestTask("PytestTask", str(case_dir)).run()

    assert result["failed_items"] == [os.path.abspath(node_b)]


def test_nodeids_are_file_double_colon_case(case_dir, patch_pytest):
    """nodeid 的格式必须是 文件::用例名，两个冒号。"""
    fake = patch_pytest()
    PytestTask("PytestTask", str(case_dir)).run()

    nodeids = fake.last_args[1:]
    assert len(nodeids) == 2
    assert all("::" in n for n in nodeids)
    assert fake.last_args[0] == "-q"


def test_only_run_given_case_names(case_dir, patch_pytest):
    """指定 case_names：只跑点名的，其余不跑。"""
    fake = patch_pytest()
    PytestTask("PytestTask", str(case_dir), case_names=["test_a"]).run()

    nodeids = fake.last_args[1:]
    assert len(nodeids) == 1
    assert nodeids[0].endswith("::test_a")


def test_retry_mode_uses_failed_items(case_dir, patch_pytest):
    """重试模式：result 里带着上次的 failed_items，只重跑这些。"""
    node_b = f"{case_dir / 'test_demo.py'}::test_b"
    fake = patch_pytest()

    PytestTask(
        "failed_retry",
        str(case_dir),
        result={"failed_items": [node_b]},
    ).run()

    nodeids = fake.last_args[1:]
    assert len(nodeids) == 1
    assert nodeids[0].endswith("::test_b")


def test_success_status(case_dir, patch_pytest):
    node_a = f"{case_dir / 'test_demo.py'}::test_a"
    patch_pytest(passed=[node_a])

    result = PytestTask("PytestTask", str(case_dir)).run()

    assert result["status"] == "success"
    assert result["failed"] == 0


def test_missing_dir_returns_none(tmp_path):
    """现状：目录不存在时 run() 返回 None，不报错也不给结果。

    这是真缺陷：调度器会把 None 记进结果列表，
    然后 Service 里 last["result"].get("failed") 直接 AttributeError，
    分支逻辑线程静默崩掉，而主线程还在 sleep 等它。

    修法：返回 {"status": "failure", "failed": 0, "err": "..."} 这种结构化结果。
    先钉住现状。
    """
    assert PytestTask("PytestTask", str(tmp_path / "没有这个目录")).run() is None


def test_empty_dir_sends_bare_q_flag(case_dir, patch_pytest):
    """现状：目录里一个用例都没有时，nodeids 是空列表。

    于是 pytest.main(["-q"]) —— 没有指定任何目标，pytest 会去跑
    当前工作目录下的全部用例。这是"没扫到用例"和"跑整个仓库"的区别，
    也是个真实风险：在别人机器上可能跑出完全无关的一大堆用例。

    修法：nodeids 为空时直接返回"无用例"结果，不要调用 pytest。
    """
    empty = case_dir / "空目录"
    empty.mkdir()
    fake = patch_pytest()

    PytestTask("PytestTask", str(empty)).run()

    assert fake.last_args == ["-q"]
