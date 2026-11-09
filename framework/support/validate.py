# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22
import os


class FileValidator:
    def __init__(self, directory):
        self.directory = directory
    def validate(self):
        return os.path.exists(self.directory)


class FilePatternValidator:
    def __init__(self, directory, pattern):
        self.directory = directory
        self.pattern = pattern

    def validate(self):
        if not os.path.exists(self.directory):
            return False
        for file in os.listdir(self.directory):
            if file.endswith(self.pattern):
                return True
        return False

class AndValidator:
    def __init__(self, *validators):
        self.validators = validators

    def validate(self):
        for validator in self.validators:
            if not validator.validate():
                return False
        return True


class LogValidator:
    def __init__(self, log_dir):
        self.log_dir = log_dir

    def validate(self):
        files = os.listdir(self.log_dir)
        for file in files:
            if file.endswith(".txt"):
                return True
        return False


class LogArchiveValidator:
    def __init__(self, log_dir):
        self.log_dir = log_dir

    def validate(self):
        files = os.listdir(self.log_dir)

        for file in files:
            if file.endswith(".log"):
                return True

        return False


class PytestValidator:
    def validate(self):
        return True
