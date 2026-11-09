# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22
import time


def test_login_success():
    assert 1 + 1 == 2


def test_login_failed():
    assert 1 + 1 == 3


def test_login_username():
    username = "admin"
    assert username == "admin"