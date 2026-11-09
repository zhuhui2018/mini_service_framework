# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22


def test_create_user():
    user = {"name": "Tom", "age": 18}
    assert user["name"] == "Tom"


def test_user_age_failed():
    user = {"name": "Tom", "age": 18}
    assert user["age"] >= 20


def test_login_success():
    assert 1 + 1 == 2
