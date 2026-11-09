"""支撑层：校验器、分支定义等无状态小工具。

这些东西不参与调度，只被 service / trigger 调用。
它们没有自己的线程、不持有状态，所以最好测——见 tests/test_validate.py。
"""
