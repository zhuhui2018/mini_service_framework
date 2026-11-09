"""重试策略：只回答一个问题——"还要不要再试一次"。"""
import pytest

from framework.core.retry_policy import RetryPolicy


@pytest.mark.parametrize(
    "retry_count, expect",
    [
        (0, True),
        (1, True),
        (2, True),
        (3, False),
        (4, False),
    ],
)
def test_should_retry(retry_count, expect):
    policy = RetryPolicy(max_retry_count=3, gap_time=0)
    assert policy.should_retry(retry_count) is expect


def test_boundary_is_last_allowed():
    """边界：max=3 时，只有 0/1/2 会重试，3 不再重试。

    注意这个数字的含义容易说错：
    "最多重试 3 次" = 第一次失败后再试 3 次 = 一共执行 4 次。
    执行器那边的用例会把 4 这个数字验证一遍。
    """
    policy = RetryPolicy(max_retry_count=3, gap_time=0)
    assert policy.should_retry(2) is True
    assert policy.should_retry(3) is False
