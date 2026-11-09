# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22

from queue import Queue
import threading
import time

q = Queue()

# 放一个任务进队列
q.put("任务1")


def worker():
    task = q.get()
    print(f"取到了: {task}")
    # 注意：这里不调用 task_done()
    q.task_done()  # 故意注释掉


# 启动 worker 线程
t = threading.Thread(target=worker)
t.start()

# 等待队列清空
print("开始等待队列清空...")
q.join()  # 这会永远卡住
print("队列清空了！")  # 这行永远不会打印
