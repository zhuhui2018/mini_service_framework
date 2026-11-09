# -*-coding:UTF-8 -*-
# author: 阿黄  time:2019/10/22

def test_create_order():
    order_id = 1001
    assert order_id is not None


def test_cancel_order():
    status = "cancelled"
    assert status == "cancelled"


def test_order_amount_failed():
    amount = 99
    assert amount > 100