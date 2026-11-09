"""插件层：pytest 结果收集器。

它是 pytest 的插件（靠 pytest_runtest_logreport 这个 hook 被调用），
不是框架的"业务代码"。单独一层，是为了让"框架依赖 pytest"这件事看得见。
"""
