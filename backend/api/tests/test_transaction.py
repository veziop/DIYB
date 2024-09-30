"""
filename: test_transaction.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Test module for testing the transaction routes.
"""

from datetime import date

from api.models.transaction import Transaction


def test_create_transaction(client, db_session):
    transaction = Transaction(
        payee="test payee",
        creation_datetime=date.today(),
        last_update_datetime=date.today(),
        transaction_date=date.today(),
        description="test description",
        amount=100,
        category_id=1,
        account_id=1,
    )
    db_session.add(transaction)
    db_session.commit()
    assert transaction.id
