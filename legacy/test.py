import inspect

class TaskFactory:
    @staticmethod
    def create(cls, **kwargs):
        # 1. 透视这个类需要什么
        sig = inspect.signature(cls.__init__)

        # 2. 准备一个空盒子，只装它需要的
        valid_params = {}

        # 3. 遍历它需要的参数
        for name, param in sig.parameters.items():
            if name in kwargs:
                # 把需要的参数装进盒子
                valid_params[name] = kwargs[name]

        # 4. 拆开盒子，创建任务
        return cls(**valid_params)

