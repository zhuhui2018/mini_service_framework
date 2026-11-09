"""结果记录器：一个只往后追加的列表，Service 靠"最后一条"做判断。"""
from framework.core.result_recorder import ResultRecorder


def test_record_keeps_order():
    r = ResultRecorder()
    r.record("t1", {"failed": 0})
    r.record("t2", {"failed": 3})

    assert [x["task_name"] for x in r.results] == ["t1", "t2"]
    assert r.results[-1]["result"] == {"failed": 3}


def test_starts_empty():
    assert ResultRecorder().results == []


def test_record_does_not_copy(make_task):
    """存的是同一个引用，不是拷贝。

    所以如果任务返回的 dict 之后被别处改了，这里记录的内容也会跟着变。
    现在没问题（没人改），但这是"共享可变对象"的经典隐患。
    """
    payload = {"failed": 1}
    r = ResultRecorder()
    r.record("t1", payload)
    payload["failed"] = 99
    assert r.results[0]["result"]["failed"] == 99
