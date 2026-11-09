# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22

import inspect

class TaskFactory:
    @staticmethod
    def create(cls, **kwargs):
        sig = inspect.signature(cls.__init__)

        valid_params = {}

        for name, param in sig.parameters.items():
            if name in kwargs:
                valid_params[name] = kwargs[name]

        return cls(**valid_params)


