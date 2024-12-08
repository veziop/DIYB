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
    Test that focuses on the initial setup of the api by creating Accounts, Categories and
    Transaction.

    1. (act) Create 2 accounts
    2. (assert) Check that 2 accounts have been created
    3. (act) Create 4 categories
    4. (assert) Check that 4 categories have been created
    5. (act) Create 2 transactions, and 2 balances
    6. (assert) Check that 2 transactions and 2 balances have been created
    7. (act) Attempt to create a transaction with an invalid transaction_date
    8. (assert) Check that the transaction was not created
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
    Integration test that focuses on Transactions and Balances.

    1. (arrange) Create 1 account
    2. (arrange) Create 2 categories
    3. (arrange) Create 1 transaction
    4. (arrange) Create 1 balance
    5. (act) Create 3 transactions, one of which has an invalid category_id (stage)
    6. (assert) Check that the last transaction was not created
    7. (assert) Check that a total of 3 transactions have been created
    8. (assert) Check the balance of the account add up correctly
    9. (act) Update the amount of the a transaction
    10. (assert) Check that the transaction was updated
    11. (act)  Update the amount and account of the a transaction
    11. (assert) Check that the balance of the accounts add up correctly
    """
    accounts = (
        Account(name="test checking", description="Default checking account", is_checking=True),
        Account(name="test savings", description="Default savings account", is_checking=False),
    )
    db_session.add_all(accounts)
    db_session.commit()

    categories = (
        Category(title="stage", description="test stage", is_stage=True, assigned_amount=0),
        Category(
            title="misc", description="test miscellaneous", is_stage=False, assigned_amount=50
        ),
    )
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

    transaction_update1 = {"amount": -15.20}
    response1 = client.patch("/transaction/3", json=transaction_update1)
    assert response1.status_code == 204
    assert db_session.get(Transaction, 3).amount == Decimal("-15.20")
    assert client.get("/balance/current").json() == 134.80
    transaction_update2 = {"account_id": 2, "amount": 80}
    response2 = client.patch("/transaction/2", json=transaction_update2)
    assert response2.status_code == 204
    assert db_session.get(Transaction, 2).amount == Decimal("80.00")
    running_total = client.get("/balance/current")
    assert running_total.status_code == 200
    assert running_total.json() == 34.8


def test_integration_3(client, db_session):
    """
    Integration test that focuses on Categories.

    1. (arrange) Create 1 account
    2. (arrange) Create 1 stage category
    3. (arrange) Create 1 transaction
    4. (arrange) Create 1 balance
    5. (act) Create 2 categories
    6. (assert) Check that the 2 categories have been created
    7. (act) Move amounts from the stage category to the other categories, one move invalid
    8. (assert) Check that all requests to move were accepted (cannot directly query the
        "assigned_amount" field of each category as it is computed)
    9. (act) Attempt to directly modify a category's "assign_amount"
    10. (assert) Check that the category was not modified
    11. (act) Modify a category's description
    12. (assert) Check that the category's description was modified
    13. (act) Attempt to delete the stage category
    14. (assert) Check that the stage category was not deleted
    15. (act) Create a new transaction
    16. (assert) Check that the appropriate category's "assigned_amount" was updated
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

    client.patch("/category/1", json={"assigned_amount": 855})
    assert db_session.get(Category, 1).assigned_amount != Decimal("855.00")

    client.patch("/category/2", json={"description": "new description"})
    assert db_session.get(Category, 2).description != "test dine"

    response7 = client.delete("/category/1")  # intentional
    assert response7.status_code == 405
    assert db_session.get(Category, 1)

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
    assert db_session.get(Category, 2).assigned_amount == Decimal("57.22")


def test_integration_4(client, db_session):
    """
    Integration test that focuses on Accounts.

    1. (arrange) Create 1 account
    2. (arrange) Create 1 category
    3. (arrange) Create 1 transaction
    4. (arrange) Create 1 balance
    5. (act) Create 1 account
    6. (assert) Check that an account has been created
    7. (act) Create 1 transfer transaction between the 2 accounts
    8. (assert) Check that a transfer transactions have been created
    9. (act) Attempt to directly modify the account's "running_total"
    10. (assert) Check that the account was not modified
    11. (act) Update the description of the new account
    12. (assert) Check that the account's description was modified
    13. (act) Attempt to delete the account
    14. (assert) Check that the account was not deleted
    15. (act) Create a new transaction that empties the savings account
    16. (act) Delete the account
    17. (assert) Check that the account was deleted
    """
    account = Account(
        name="test checking", description="Default checking account", is_checking=True
    )
    db_session.add(account)
    db_session.commit()

    categories = (
        Category(title="stage", description="test stage", is_stage=True, assigned_amount=0),
        Category(title="other", description="test other", is_stage=False, assigned_amount=350),
    )
    db_session.add_all(categories)
    db_session.commit()

    transaction = Transaction(
        payee="test paycheck1",
        creation_datetime=date.today() - datetime.timedelta(days=1),
        last_update_datetime=datetime.datetime.now() - datetime.timedelta(days=1),
        transaction_date=date.today() - datetime.timedelta(days=1),
        description="",
        amount=350,
        category_id=1,
        account_id=1,
    )
    db_session.add(transaction)
    db_session.commit()

    balance = Balance(
        entry_datetime=date.today(),
        transaction_amount_record=350,
        running_total=350,
        is_current=True,
        transaction_id=1,
    )
    db_session.add(balance)
    db_session.commit()

    response1 = client.post(
        "/account", json={"name": "savings", "is_checking": False, "iban_tail": "1234"}
    )
    assert response1.status_code == 201
    assert len(client.get("/account/all").json()) == 2
    response2 = client.post(
        "/account/1/transfer/2",
        json={
            "transfer_date": str(date.today()),
            "description": "test transfer",
            "amount": 251.73,
        },
    )
    assert response2.status_code == 204
    assert db_session.query(Transaction).count() == 3
    assert db_session.get(Transaction, 2).is_transfer
    assert db_session.get(Transaction, 3).is_transfer
    client.patch("/account/2", json={"running_total": 1_000_000})  # intentional
    response3 = client.get("/account/2")
    assert response3.json() == {
        "id": 2,
        "name": "savings",
        "description": "",
        "is_checking": False,
        "iban_tail": "1234",
        "running_total": 251.73,
    }
    response4 = client.patch("/account/2", json={"description": "new description"})
    assert response4.status_code == 204
    assert db_session.get(Account, 2).description == "new description"
    response5 = client.delete("/account/2")  # intentional
    assert response5.status_code == 403
    client.post(
        "/transaction",
        json={
            "payee": "test store 2",
            "creation_datetime": str(date.today()),
            "last_update_datetime": str(date.today()),
            "transaction_date": str(date.today()),
            "description": "test description",
            "amount": -251.73,
            "category_id": 2,
            "account_id": 2,
        },
    )
    response6 = client.delete("/account/2")
    assert response6.status_code == 204
    assert len(client.get("/account/all").json()) == 1
