"""调度器：一个队列 + 几个集合，保证"同一个任务不会被塞两次"。

调度器是多线程的（Service 里起了 3 个 worker），所以这里的用例
要么不起线程（只测队列状态），要么起一个线程并确保能退出。
"""
import threading

from framework.core.executor import Executor
from framework.core.result_recorder import ResultRecorder
from framework.core.retry_policy import RetryPolicy
from framework.core.scheduler import Scheduler


def make_scheduler(on_complete=None):
    return Scheduler(
        Executor(),
        ResultRecorder(),
        RetryPolicy(max_retry_count=0, gap_time=0),
        on_task_complete=on_complete,
    )


def drain_one(s):
    """让 worker 跑一轮：放一个 None 当结束信号，它取到就退出。"""
    t = threading.Thread(target=s.run_task)
    t.start()
    s.tasks.put(None)
    t.join(timeout=5)
    assert not t.is_alive(), "worker 没退出来，可能死锁了"


def test_store_tasks_dedup_same_name(make_task):
    """同名任务重复入队，只进一次。

    注意用的是"名字"去重，不是"对象"去重——
    两个不同的对象只要 name 一样，第二个就进不来。
    """
    s = make_scheduler()
    t = make_task(name="t1")
    s.store_tasks(t)
    s.store_tasks(t)
    assert s.tasks.qsize() == 1


def test_two_different_names_both_enter(make_task):
    s = make_scheduler()
    s.store_tasks(make_task(name="t1"))
    s.store_tasks(make_task(name="t2"))
    assert s.tasks.qsize() == 2


def test_done_task_will_not_be_queued_again(make_task):
    """跑成功的任务名会被记住，之后再入队直接被拒。

    这是防止"任务成功之后又被分支逻辑拉回来跑一遍"的保险。
    副作用：如果你真想重跑一个成功的任务，得先骗它（换个名字）。
    """
    s = make_scheduler()
    t = make_task(name="t1")
    s.store_tasks(t)
    drain_one(s)
    assert "t1" in s.success_task_names

    again = make_task(name="t1")
    s.store_tasks(again)
    assert s.tasks.qsize() == 0


def test_result_is_recorded_and_callback_fires(make_task):
    """任务跑完先记结果、再回调 —— 顺序不能反。

    Service 的 _check_and_trigger_downstream 全靠"最后一条结果"做判断，
    如果先回调后记录，它读到的永远是上一条。
    """
    called = []
    s = make_scheduler(on_complete=lambda: called.append("done"))
    s.store_tasks(make_task(name="t1", result={"failed": 0}))

    drain_one(s)

    assert s.result_recorder.results == [{"task_name": "t1", "result": {"failed": 0}}]
    assert called == ["done"]


def test_failed_task_is_not_recorded(make_task):
    """任务抛异常：打印 traceback，但不写结果、也不进 success 集合。

    这是一个已知的设计缺口：失败的任务在结果列表里"不存在"，
    所以分支逻辑看不到它（也就不会触发重试链）。
    执行器外面还有一层重试兜着，所以短期没暴露；
    等你做第 9 项（下游结束逻辑）时，这里必须补一条失败记录。
    """
    s = make_scheduler()
    s.store_tasks(make_task(name="bad", fail_times=999))

    drain_one(s)

    assert s.result_recorder.results == []
    assert "bad" not in s.success_task_names
