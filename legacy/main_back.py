# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22
import time
import threading
import yaml

from service import Service
from task import PytestTask, ReportTask, AlertTask, LogArchiveTask
from trigger import Trigger
from validate import FileValidator
from branch_chain import BranchChain

# 加载 YAML 配置
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# 类名映射
class_map = {
    "PytestTask": PytestTask,
    "ReportTask": ReportTask,
    "AlertTask": AlertTask,
    "LogArchiveTask": LogArchiveTask,
}

# 创建 Service
service = Service(class_map=class_map)

# 1. 注册任务
for task_config in config.get("tasks", []):
    task_cls = class_map[task_config["type"]]
    task = task_cls(name=task_config["name"], **task_config["params"])
    service.register_task(task_config["name"], task)


# 2. 创建 Validator（先硬编码，后续可移到 YAML）
test_dir = config["tasks"][0]["params"]["test_dir"]
validator = FileValidator(test_dir)

# 3. 创建触发器
for trigger_config in config.get("triggers", []):
    trigger = Trigger(
        name=trigger_config["name"],
        registry=service.registry,
        scheduler=service.scheduler,
        validator=validator,
        interval=trigger_config.get("interval"),
        cron=trigger_config.get("cron"),
    )
    service.store_triggers(trigger)
    trigger.start()

# 4. 创建分支链条
parsed_branches = []
for b in config["branches"]:
    b["downstream_class"] = class_map[b["downstream_class"]]
    parsed_branches.append(b)

branch = BranchChain(
    upstream_name=config["upstream_name"],
    branches=parsed_branches
)
service.add_branch(branch)

# 5. 启动框架
service_thread = threading.Thread(target=service.start)
service_thread.start()

# 等待触发
while not trigger.has_triggered:
    time.sleep(0.1)

# 等待任务执行
time.sleep(10)

# 停止
trigger.stop()
service.stop()
service_thread.join()