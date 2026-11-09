# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22
import time
import threading
from pathlib import Path

from framework.service import Service
from framework.tasks.tasks import PytestTask, ReportTask, AlertTask, LogArchiveTask
from framework.core.trigger import Trigger
from framework.support.validate import FileValidator
from framework.support.branch_chain import BranchChain

BASE_DIR = Path(__file__).resolve().parent
log_dirs = str(BASE_DIR / "zhuhui")
archive_dir = str(BASE_DIR / "zhuhui" / "archive_dir")
test_dir = str(BASE_DIR / "zhuhui")
# 注册 LogArchiveTask
archive_task = LogArchiveTask("LogArchiveTask", log_dirs, archive_dir)

service = Service()

# 注册PytestTask任务
task = PytestTask("PytestTask", test_dir)
service.register_task("PytestTask", task)

# 注册LogArchiveTask任务
service.register_task("LogArchiveTask", archive_task)

# 创建校验器
validator = FileValidator(test_dir)

# 创建触发器
trigger = Trigger(
    name="PytestTask",
    registry=service.registry,
    scheduler=service.scheduler,
    validator=validator,
    interval=5
)
service.store_triggers(trigger)
trigger.start()

# 为它创建 Trigger
archive_trigger = Trigger(
    name="LogArchiveTask",
    registry=service.registry,
    scheduler=service.scheduler,
    validator=FileValidator(log_dirs),
    interval=5
)
service.store_triggers(archive_trigger)
archive_trigger.start()

# 创建分支链条
branch = BranchChain(
    upstream_name="PytestTask",
    branches=[
        {
            "condition": {"failed": ">0"},
            "downstream_class": PytestTask,
            "downstream_name": "failed_retry",
            "extra_params": {"test_dir": test_dir}
        },
        {
            "condition": {"failed": "==0"},
            "downstream_class": ReportTask,
            "downstream_name": "generate_report"
        }
    ]

)
service.add_branch(branch)
branch1 = BranchChain(
    upstream_name="LogArchiveTask",
    branches=[
        {
            "condition": {"failed": ">0"},
            "downstream_class": LogArchiveTask,
            "downstream_name": "failed_retry",
            "extra_params": {"log_dirs": log_dirs,
                             "archive_dir": archive_dir}
        },
        {
            "condition": {"failed": "==0"},
            "downstream_class": ReportTask,
            "downstream_name": "generate_report"
        }
    ]
)
service.add_branch(branch1)

# 启动框架
service_thread = threading.Thread(target=service.start)
service_thread.start()

# 等待触发
while not (trigger.has_triggered and archive_trigger.has_triggered):
    time.sleep(0.1)

print(">>> 开始等待 service 停止")
while service.is_running:
    time.sleep(0.5)
print(">>> service 已停止，准备停止 trigger")

trigger.stop()
archive_trigger.stop()
print(">>> trigger 已停止，准备停止 service")

service.stop()
print(">>> service 已停止，准备 join service_thread")

service_thread.join()
print(">>> 全部结束")