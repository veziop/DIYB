"""
filename: test_transaction.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Test module for testing the transaction routes.
"""

from datetime import date
from decimal import Decimal
from random import randint

import pytest

from api.models import Account, Balance, Category, Transaction


def test_create_transaction(client, db_session):
    random_amount = Decimal(f"100.{randint(1, 100)}")
    transaction_payload = {
        "payee": "employer",
        "creation_datetime": str(date.today()),
        "last_update_datetime": str(date.today()),
        "transaction_date": str(date.today()),
        "description": "test description",
        "amount": float(random_amount),
        "category_id": 1,
        "account_id": 1,
    }
    result = client.post("/transaction", json=transaction_payload)
    all_transactions = db_session.query(Transaction).order_by(Transaction.id.desc()).all()
    assert result.status_code == 201
    assert len(all_transactions) == 1
    assert all_transactions[0].amount == random_amount


def test_fetch_all_transactions(client, create_multiple_transactions):
    num_transactions = len(create_multiple_transactions)
    response = client.get("/transaction/all")
    assert response.status_code == 200
    assert len(response.json()) == num_transactions


@pytest.mark.parametrize(
    "payee, amount, category_id, account_id",
    [("employer", 200, 1, 1), ("taxi", -10.5, 1, 3), ("take-out", -20.74, 1, 2)],
)
def test_fetch_transaction_by_id(
    client, create_transaction, payee, amount, category_id, account_id
):
    create_transaction(
        payee=payee, amount=amount, category_id=category_id, account_id=account_id
    )
    response = client.get("/transaction/1")
    assert response.status_code == 200
    assert response.json().get("amount") == amount
