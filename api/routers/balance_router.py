"""
filename: balance_router.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definitions of routes related to the Balance model.
"""
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from starlette import status

from api.database import db_dependency
from api.models import Balance

router = APIRouter(prefix="/balance", tags=["balance"])


def create_balance_entry(db: db_dependency, transaction_id: int, transaction_amount: Decimal):
    """
    Auxiliary function to create a balance entry when creating a transaction entry. This is
    deliberately not an enpoint as creating a balance entry directly is not allowed. It must
    derrive from creating, updating or deleting a transaction entry.

    :param db: (db_dependancy) SQLAlchemy ORM session.
    :param transaction_id: (int) ID of the transaction entry.
    :returns: None
    """
    # Fetch the current total
    current_total_entry = db.query(Balance).filter(Balance.is_current).first()
    # If it is the first transaction the current is 0
    if current_total_entry:
        current_total = current_total_entry.running_total
    else:
        current_total = Decimal(0)
    # Overwrite all entries as not current
    db.query(Balance).update({Balance.is_current: False})
    # Create the balance model
    balance_model = Balance(
        entry_datetime=datetime.now().replace(microsecond=0),
        running_total=current_total + transaction_amount,
        is_current=True,
        transaction_id=transaction_id,
    )
    db.add(balance_model)
    db.commit()


@router.get("/current", status_code=status.HTTP_200_OK)
async def get_current_balance(db: db_dependency, all_data: bool = False):
    """
    Fetch the current account balance by using the "is_current" flag. Optiona

    :param db: (db_dependancy) SQLAlchemy ORM session.
    :param all_data: (bool) Optionally return the complete balance entry instead of the scalar.
    :returns: either balance entry or current balance value.
    """
    current_balance = db.query(Balance).filter(Balance.is_current).first()
    if not current_balance:
        raise HTTPException(status_code=522, detail="Internal error, no current balance found")
    if all_data:
        return current_balance
    return current_balance.running_total


@router.get("/filter/{id}", status_code=status.HTTP_200_OK)
async def get_transactions(db: db_dependency, id: int = Path(gt=0)):
    """
    Fetch the balance entries that are linked to a particular transaction.

    :param db: (db_dependancy) SQLAlchemy ORM session.
    :param id: (int) ID of the transaction entry.
    :returns: (list) all the balance entries that match the transaction ID.
    """
    return db.query(Balance).filter(Balance.transaction_id == id).all()
