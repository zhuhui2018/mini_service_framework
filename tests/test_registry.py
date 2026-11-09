"""注册表：任务名 -> 任务对象。整个框架靠它"按名字找人"。"""
import pytest

from framework.core.registry import Registry


def test_register_then_get(make_task):
    task = make_task(name="PytestTask")
    r = Registry()
    r.register_tasks("PytestTask", task)
    assert r.get_task("PytestTask") is task


def test_exists(make_task):
    r = Registry()
    r.register_tasks("t1", make_task(name="t1"))
    assert r.exists("t1") is True
    assert r.exists("t2") is False


def test_get_missing_raises_keyerror():
    """现状：取不到直接 KeyError。

    这其实是框架的一个脆弱点——Trigger 里先 exists() 再 get_task()，
    两步之间有窗口期。真正的修法是 get_task 返回 None，
    由调用方决定怎么处理（这条留给你后续优化，先钉住现状）。
    """
    r = Registry()
    with pytest.raises(KeyError):
        r.get_task("不存在的任务")


def test_same_name_overwrites(make_task):
    """同名注册会静默覆盖，不报错也不提示。

    风险：重试任务叫 failed_retry，如果两个链都用这个名字，
    后一个会把前一个顶掉，而且是悄悄顶掉。
    """
    r = Registry()
    old = make_task(name="failed_retry")
    new = make_task(name="failed_retry")
    r.register_tasks("failed_retry", old)
    r.register_tasks("failed_retry", new)
    assert r.get_task("failed_retry") is new
