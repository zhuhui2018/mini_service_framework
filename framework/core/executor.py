# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22

import time


class Executor:
    def execute(self, task):
        result = task.run()
        return result

    def execute_with_retry(self, task, retry_policy):
        try_count = 0
        while True:
            try:
                result = self.execute(task)
                return result
            except Exception as e:
                try_count += 1

                if retry_policy.should_retry(try_count):
                    time.sleep(retry_policy.gap_time)
                    continue

                raise e



















