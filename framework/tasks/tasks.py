# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22
import os
from datetime import datetime

import pytest
import requests

from framework.plugins.pytest_result_collector import PytestResultCollector


class FileMergeTask:
    def __init__(self, name, input_dir, output_file):
        self.name = name
        self.input_dir = input_dir
        self.output_file = output_file

    def run(self):
        files = os.listdir(self.input_dir)

        txt_files = []
        for file in files:
            if file.endswith(".txt"):
                full_path = os.path.join(self.input_dir, file)
                txt_files.append(full_path)

        result = {
            "total_files": len(txt_files),
            "success": [],
            "failed": []
        }

        for file in txt_files:
            context_file = []
            try:
                with open(file, "r", encoding="utf-8") as f:
                    for line in f:
                        context_file.append(line.strip())
                print("context_file", context_file)

                with open(self.output_file, "a", encoding="utf-8") as f:
                    for line in context_file:
                        f.write(line + "\n")
                result["success"].append(file)

            except Exception:
                result["failed"].append(file)

        return result


class HttpProbeTask:
    def __init__(self, name, url, timeout):
        self.name = name
        self.url = url
        self.timeout = timeout

    def run(self):

        result = {
            "success": None,
            "status_code": None,
            "url": self.url,
            "failed": None
        }

        try:
            resp = requests.get(self.url, timeout=self.timeout)
            # 拿到状态码
            status_code = resp.status_code
            result["status_code"] = status_code
            result["success"] = "success"
        except requests.RequestException as e:
            result["failed"] = str(e)

        return result


class LogCleanTask:
    def __init__(self, name, log_dir):
        self.name = name
        self.log_dir = log_dir

    def run(self):

        result = {
            "success": None,
            "failed": None,
            "err_info": None
        }

        # 为了防止删错或者漏掉先统计下找到的log_file是不是完整的
        log_files = []
        files = os.listdir(self.log_dir)
        try:
            for file in files:
                if file.endswith(".log"):
                    full_path = os.path.join(self.log_dir, file)
                    log_files.append(full_path)
            print("log_files", log_files)

            for file_path in log_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"已删除: {file_path}")
            result["success"] = "success"
        except Exception as e:
            result["failed"] = "failed"
            result["err_info"] = str(e)

        return result


class LogArchiveTask:
    retryable=True
    max_retries = 3

    def __init__(self, name, log_dirs, archive_dir,
                 result=None, original_task_name=None):
        if isinstance(log_dirs, str):
            self.log_dirs = [log_dirs]
        else:
            self.log_dirs = log_dirs
        self.name = name
        self.archive_dir = archive_dir
        self.result = result
        self.original_task_name = original_task_name

    def run(self):
        # 创建归档日期
        today = datetime.now().strftime('%Y-%m-%d')
        # 创建归档路径
        archive_path = os.path.join(self.archive_dir, today)
        os.makedirs(archive_path, exist_ok=True)
        # 找到所有.log结尾的日志文件，并放入到log_files列表中

        success_files = []
        failed_files = []
        failed_paths = []
        log_files = []

        if not self.result:
            # 首次执行：收集所有 .log 文件
            for log_dir in self.log_dirs:
                for file in os.listdir(log_dir):
                    if file.endswith(".log"):
                        src_path = os.path.join(log_dir, file)
                        log_files.append(src_path)     # 只收集，不移动
        else:
            # 重试：只处理上次失败的文件
            log_files = self.result["failed_items"]

        # 统一处理 log_files 中的每个文件
        for src_path in log_files:
            file_name = os.path.basename(src_path)
            src_dir_name = os.path.basename(os.path.dirname(src_path))
            dst_dir = os.path.join(archive_path, src_dir_name)
            os.makedirs(dst_dir, exist_ok=True)
            dst_path = os.path.join(dst_dir, file_name)
            try:
                os.rename(src_path, dst_path)
                success_files.append(file_name)
            except Exception as e:
                failed_files.append((file_name, str(e)))
                failed_paths.append(src_path)



        result = {
            "status": "success" if len(failed_files) == 0 else "failure",
            "total": len(success_files) + len(failed_files),
            "passed": len(success_files),
            "failed": len(failed_files),
            "failed_items": failed_paths,
            "details": {
            "success_files": success_files,
            "failed_files": failed_files
            }
        }

        print(result)
        return result


class PytestTask:
    retryable=True
    max_retries = 3

    def __init__(self, name, test_dir,  result=None,
                 case_names=None, original_task_name=None):
        print(f"任务 {name} 收到的 original_task_name = {original_task_name}")
        self.name = name
        self.test_dir = test_dir
        self.result = result
        self.case_names = case_names
        self.original_task_name = original_task_name
        self.case_map = {}

    def run(self):
        test_target = self.test_dir

        if not os.path.exists(test_target):
            return

        test_cases = []
        for root, dirs, files in os.walk(self.test_dir):
            for f in files:
                # 只处理.py文件
                if f.endswith(".py"):
                    path_file = os.path.join(root, f)

                    # 读取文件内容
                    with open(path_file, "r", encoding="utf-8") as fd:
                        lines = fd.readlines()

                    # 遍历行，找出以 test 开头且以 "(self):" 结尾的函数
                    for line in lines:
                        if line.strip().startswith("def test_"):
                            case_name = line.split("(")[0].replace("def ", "")
                            test_cases.append({
                                "file_path": path_file,
                                "case_name": case_name
                            })

                            # 构建正确的 nodeid（两个冒号）
                            nodeid = f"{path_file}::{case_name}"
                            if case_name not in self.case_map:
                                self.case_map[case_name] = []
                            self.case_map[case_name].append(nodeid)

        collector = PytestResultCollector()
        nodeids = []

        if self.result:
            # 从result中取failed_items
            case_names = self.result.get("failed_items", [])
        elif self.case_names:
            # 用指定的 case_names
            case_names = self.case_names
        else:
            # 没有指定，跑所有用例
            case_names = None

        if not case_names:
            for case in test_cases:
                nodeid = f"{case['file_path']}::{case['case_name']}"
                nodeids.append(nodeid)
        else:
            if isinstance(case_names, str):
                case_names = [case_names]

            for target_name in case_names:
                case_name = target_name.split("::")[-1]
                if case_name not in self.case_map:
                    continue
                for nodeid in self.case_map[case_name]:
                    nodeids.append(nodeid)

        exit_code = pytest.main(
            [
                "-q",
                *nodeids
            ],
            plugins=[collector],
        )
        failed_items = [os.path.abspath(case) for case in collector.failed]
        result = {
            "status": "success" if len(collector.failed) == 0 else "failure",
            "total": len(nodeids),
            "passed": len(collector.passed),
            "failed": len(collector.failed),
            "failed_items": failed_items,
            "original_task_name": self.original_task_name,
            "details": {
                "exit_code": int(exit_code),
                "skipped": len(collector.skipped),
                "passed_cases": collector.passed,
                "skipped_cases": collector.skipped
            }
        }
        print(f"任务 {self.name} 返回的 original_task_name = {self.original_task_name}")

        return result

class ReportTask:
    is_terminal = True

    def __init__(self, name, result):
        self.name = name
        self.result = result

    def run(self):
        total = self.result.get("total", 0)
        passed = self.result.get("passed", 0)
        failed = self.result.get("failed", 0)
        failed_cases = self.result.get("failed_items", [])

        print("=" * 40)
        print("测试报告")
        print("=" * 40)
        print(f"总用例数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {failed}")
        if failed:
            print("\n失败用例:")
            for case in failed_cases:
                print(f"  - {case}")
        else:
            print("\n无失败用例")
        print("=" * 40)

        return {"status": "report_generated", "total": total, "passed": passed, "failed": failed}


class AlertTask:
    is_terminal = True
    def __init__(self, name, message):
        self.name = name
        self.message = message

    def run(self):
        print(f"[ALERT] {self.name} {self.message}")
        return {"status": "alert_sent", "message": self.message}


















