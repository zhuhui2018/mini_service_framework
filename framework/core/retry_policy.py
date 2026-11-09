# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22

class RetryPolicy:
    def __init__(self, max_retry_count, gap_time):
        self.max_retry_count = max_retry_count
        self.gap_time = gap_time

    def should_retry(self, retry_count):
        if retry_count < self.max_retry_count:
            return True
        else:
            return False























