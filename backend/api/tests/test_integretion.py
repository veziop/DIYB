"""
filename: test_integration.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Test module for defining a procedure to test different use cases.
"""

import datetime
from datetime import date
from decimal import Decimal

from api.models import Account, Balance, Category, Transaction


def test_integration_1(client, db_session):
    """
    TODO
    """
    accounts = [
        {
            "name": "test checking",
            "description": "Default checking account",
            "is_checking": True,
        },
        {
            "name": "test savings",
            "description": "Default savings account",
            "is_checking": False,
        },
    ]

    for account in accounts:
        response = client.post("/account/", json=account)
        assert response.status_code == 201
    assert db_session.query(Account).count() == 2

    categories = [
        {"title": "stage", "description": "test stage", "is_stage": True},
        {"title": "restaurant", "description": "test food", "is_stage": False},
        {"title": "transportation", "description": "test transportation", "is_stage": False},
        {"title": "misc", "description": "test miscellaneous", "is_stage": False},
    ]

    for category in categories:
        response = client.post("/category/", json=category)
        assert response.status_code == 201
    assert db_session.query(Category).count() == 4

    transactions = [
        {
            "payee": "test1",
            "creation_datetime": str(date.today()),
            "last_update_datetime": str(date.today()),
            "transaction_date": str(date.today()),
            "description": "test description",
            "amount": 1000,
            "category_id": 1,
            "account_id": 1,
        },
        {
            "payee": "test2",
            "creation_datetime": str(date.today()),
            "last_update_datetime": str(date.today()),
            "transaction_date": str(date.today()),
            "description": "test description",
            "amount": 5000,
            "category_id": 1,
            "account_id": 2,
        },
    ]

    for transaction in transactions:
        response = client.post("/transaction", json=transaction)
        assert response.status_code == 201
    assert db_session.query(Transaction).count() == 2
    assert db_session.query(Balance).count() == 2

    transaction = {
        "payee": "test test3",
        "creation_datetime": str(date.today()),
        "last_update_datetime": str(date.today()),
        "transaction_date": str(date.today() + datetime.timedelta(days=1)),  # tomorrow
        "description": "test description",
        "amount": 100,
        "category_id": 1,
        "account_id": 1,
    }
    response = client.post("/transaction", json=transaction)
    assert response.status_code == 422


def test_integration_2(client, db_session):
    """
    TODO
    """
    account = Account(
        name="test checking", description="Default checking account", is_checking=True
    )
    db_session.add(account)
    db_session.commit()

    categories = [
        Category(title="stage", description="test stage", is_stage=True, assigned_amount=0),
        Category(
            title="misc", description="test miscellaneous", is_stage=False, assigned_amount=50
        ),
    ]
    db_session.add_all(categories)
    db_session.commit()

    transaction = Transaction(
        payee="test paycheck1",
        creation_datetime=date.today() - datetime.timedelta(days=1),
        last_update_datetime=datetime.datetime.now(),
        transaction_date=date.today() - datetime.timedelta(days=1),
        description="",
        amount=50,
        category_id=1,
        account_id=1,
    )
    db_session.add(transaction)
    db_session.commit()

    balance = Balance(
        entry_datetime=date.today(),
        transaction_amount_record=50,
        running_total=50,
        is_current=True,
        transaction_id=1,
    )
    db_session.add(balance)
    db_session.commit()

    transactions = [
        {
            "payee": "test paycheck2",
            "creation_datetime": str(date.today()),
            "last_update_datetime": str(date.today()),
            "transaction_date": str(date.today()),
            "description": "test description",
            "amount": 100,
            "category_id": 1,
            "account_id": 1,
        },
        {
            "payee": "test store 1",
            "creation_datetime": str(date.today()),
            "last_update_datetime": str(date.today()),
            "transaction_date": str(date.today()),
            "description": "test description",
            "amount": -10.51,
            "category_id": 2,
            "account_id": 1,
        },
        {
            "payee": "test store 2",
            "creation_datetime": str(date.today()),
            "last_update_datetime": str(date.today()),
            "transaction_date": str(date.today()),
            "description": "test description",
            "amount": -21.14,
            "category_id": 1,  # intentional, cannot have money outflow from stage
            "account_id": 1,
        },
    ]

    for transaction in transactions:
        response = client.post("/transaction", json=transaction)
    assert response.status_code == 403
    assert db_session.query(Transaction).count() == 3
    assert (
        db_session.query(Balance).filter(Balance.is_current).first().running_total
    ) == Decimal("139.49")

    transaction_updates = [{"amount": -15.20}, {"amount": 80}]
    response1 = client.patch("/transaction/3", json=transaction_updates[0])
    response2 = client.patch("/transaction/2", json=transaction_updates[1])
    running_total = client.get("/balance/current")
    assert response1.status_code == 204
    assert response2.status_code == 204
    assert db_session.query(Transaction).filter_by(id=3).first().amount == Decimal("-15.20")
    assert db_session.query(Transaction).filter_by(id=2).first().amount == Decimal("80.00")
    assert running_total.status_code == 200
    assert running_total.json() == 114.8


def test_integration_3(client, db_session):
    """
    TODO
    """
    account = Account(
        name="test checking", description="Default checking account", is_checking=True
    )
    db_session.add(account)
    db_session.commit()

    categories = [
        Category(title="stage", description="test stage", is_stage=True, assigned_amount=500),
    ]
    db_session.add_all(categories)
    db_session.commit()

    transaction = Transaction(
        payee="test paycheck1",
        creation_datetime=date.today() - datetime.timedelta(days=1),
        last_update_datetime=datetime.datetime.now() - datetime.timedelta(days=1),
        transaction_date=date.today() - datetime.timedelta(days=1),
        description="",
        amount=500,
        category_id=1,
        account_id=1,
    )
    db_session.add(transaction)
    db_session.commit()

    balance = Balance(
        entry_datetime=date.today(),
        transaction_amount_record=500,
        running_total=500,
        is_current=True,
        transaction_id=1,
    )
    db_session.add(balance)
    db_session.commit()

    response1 = client.post("/category", json={"title": "dine", "description": "test dine"})
    response2 = client.post("/category", json={"title": "market", "description": "test market"})
    assert response1.status_code == 201
    assert response2.status_code == 201
    assert db_session.query(Category).count() == 3

    response3 = client.post("/category/1/move", json={"id_to": 2, "amount": 100})
    response4 = client.post("/category/1/move", json={"id_to": 3, "amount": 200})
    response5 = client.post("/category/1/move", json={"id_to": 3, "amount": 400})  # intentional
    assert response3.status_code == 200
    assert response4.status_code == 200
    assert response5.status_code == 403

    client.patch("/category/1", json={"assigned_amount": 100})
    assert (
        db_session.query(Category).filter_by(id=1).first().assigned_amount != Decimal("100.00"),
    )

    client.patch("/category/2", json={"description": "new description"})
    assert db_session.query(Category).filter_by(id=2).first().description != "test dine"

    response7 = client.delete("/category/1")  # intentional
    assert response7.status_code == 405

    transaction = {
        "payee": "test store 2",
        "creation_datetime": str(date.today()),
        "last_update_datetime": str(date.today()),
        "transaction_date": str(date.today()),
        "description": "test description",
        "amount": -42.78,
        "category_id": 2,
        "account_id": 1,
    }
    client.post("/transaction", json=transaction)
    assert (
        db_session.query(Category).filter_by(id=2).first().assigned_amount == Decimal("57.22"),
    )
