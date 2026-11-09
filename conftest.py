"""测试公共配置：把项目根目录放进 sys.path，并提供两个常用 fixture。

为什么需要这一句 sys.path.insert：
    tests/ 里写的是 `from framework.core.executor import Executor`，
    而 pytest 是从 tests/ 目录往下收集的。不把项目根目录加进去，
    import 就会报 ModuleNotFoundError。
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeTask:
    """假任务：只实现 name + run()，用来测调度器和执行器。
    """

    def __init__(self, name="fake", result=None, fail_times=0):
        self.name = name
        self.result = result if result is not None else {"failed": 0}
        self.fail_times = fail_times
        self.calls = 0

    def run(self):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError(f"{self.name} 第 {self.calls} 次失败")
        return self.result


@pytest.fixture
def make_task():
    """用法：t = make_task(name="t1", fail_times=2)"""
    def _make(**kwargs):
        return FakeTask(**kwargs)
    return _make


@pytest.fixture
def log_dir(tmp_path):
    """造一个装着两个 .log 的目录。"""
    d = tmp_path / "logs"
    d.mkdir()
    (d / "app1.log").write_text("line1\n", encoding="utf-8")
    (d / "app2.log").write_text("line2\n", encoding="utf-8")
    return d
