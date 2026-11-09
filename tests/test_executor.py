"""执行器：只管"把任务跑起来"，失败了按策略重试。

这里有个坑值得记住：异常最终还是会往上抛，由调度器兜住并打 traceback；
执行器不吞异常——吞掉就等于静默失败。
"""
import pytest

from framework.core.executor import Executor
from framework.core.retry_policy import RetryPolicy


def test_execute_returns_run_result(make_task):
    task = make_task(name="t1", result={"failed": 0, "total": 3})
    result = Executor().execute(task)
    assert result == {"failed": 0, "total": 3}
    assert task.calls == 1


def test_retry_then_success(make_task):
    """前两次抛异常，第三次成功：最终拿到结果，一共调用 3 次。"""
    task = make_task(name="flaky", result={"failed": 0}, fail_times=2)
    policy = RetryPolicy(max_retry_count=3, gap_time=0)
    result = Executor().execute_with_retry(task, policy)
    assert result == {"failed": 0}
    assert task.calls == 3


def test_always_fail_raises_after_three_attempts(make_task):
    """一直失败：仍然抛出，一共执行 3 次。

    ★ 这里有个命名和实际不符的问题（用例把它钉住了）：
      max_retry_count=3 看起来像"重试 3 次"（应该一共跑 4 次），
      但 should_retry 的判定是 try_count < 3，而 try_count 在第 1 次失败后就变成 1，
      所以真正发生的是"总共跑 3 次 = 1 次首发 + 2 次重试"。

      两种改法：
        A. 改语义，让它真的是"重试 3 次"：判定改成 try_count <= max_retry_count
        B. 改名字，叫 max_attempts，承认它是"最多跑几次"
      面试里被问"重试次数怎么算"，能说清这个差一问题就是加分项。
    """
    task = make_task(name="broken", fail_times=999)
    policy = RetryPolicy(max_retry_count=3, gap_time=0)
    with pytest.raises(RuntimeError):
        Executor().execute_with_retry(task, policy)
    assert task.calls == 3


def test_no_retry_policy_zero(make_task):
    """max_retry_count=0：只跑一次，不重试。"""
    task = make_task(name="once", fail_times=999)
    policy = RetryPolicy(max_retry_count=0, gap_time=0)
    with pytest.raises(RuntimeError):
        Executor().execute_with_retry(task, policy)
    assert task.calls == 1
