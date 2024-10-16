"""
filename: balance.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definitions of routes related to the Balance model.
"""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette import status

from api.database import db_dependency
from api.models.account import Account
from api.models.balance import Balance
from api.models.transaction import Transaction
from api.utils.tools import now_factory

router = APIRouter(prefix="/balance", tags=["balance"])


class BalanceResponse(BaseModel):
    id: int = Field(min=0)
    entry_datetime: datetime
    transaction_amount_record: float
    running_total: float
    is_current: bool
    transaction_id: int = Field(gt=0)


def create_balance_entry(
    db: Session,
    transaction_id: int,
    account_id: int,
    amount_difference: Decimal,
    transaction_amount: float = None,
) -> None:
    """
    Auxiliary function to create a balance entry when creating a transaction entry. This is
    deliberately not an endpoint as creating a balance entry directly is not allowed. It must
    derive from creating, updating or deleting a transaction entry.

    Also used to create new balance entries that cancel a previous' amount. This technique is
    preferred for the sake of keeping the order and work in a non-destructive manner. Instead of
    modifying existing rows (chances are they are not flagged as <is_current> anymore) from
    the entries history and losing the running total.

    :param db: (Session) SQLAlchemy ORM session.
    :param transaction_id: (int) ID of the transaction entry.
    :param account_id: (int) ID of the account entry.
    :param amount_difference: (Decimal) amount to adjust the current balance with.
    :param transaction_amount: (float) optional, new transaction amount for updating existing
     transactions.
    :returns: None
    """
    # Fetch the current total
    current_total_entry = (
        db.query(Balance)
        .join(Transaction)
        .filter(Transaction.account_id == account_id, Balance.is_current)
        .first()
    )
    # Determine latest balance entry by date/time if no entry is found
    if not current_total_entry:
        current_total_entry = get_time_based_current(db, account_id=account_id, _set=False)
    if current_total_entry:
        current_total = current_total_entry.running_total
    # If it is the first transaction the current is 0
    else:
        current_total = Decimal(0)
    # Overwrite all entries as not current
    entries = (
        db.query(Balance).join(Transaction).filter(Transaction.account_id == account_id).all()
    )
    if entries:
        db.query(Balance).filter(Balance.id.in_(entry.id for entry in entries)).update(
            {Balance.is_current: False}
        )
    # Create the balance model
    balance_model = Balance(
        entry_datetime=now_factory(),
        transaction_amount_record=(
            amount_difference if not transaction_amount else transaction_amount
        ),
        running_total=current_total + amount_difference,
        is_current=True,
        transaction_id=transaction_id,
    )
    db.add(balance_model)


def delete_balance_entries(db: Session, transaction_id: int) -> None:
    """
    Auxiliary function to delete all Balance entries associated with a specific Transaction
    entry.

    :param db: (Session) SQLAlchemy ORM session.
    :param transaction_id: (int) ID of the Transaction entry.
    :returns: None
    """
    db.query(Balance).filter(Balance.transaction_id == transaction_id).delete()


def get_time_based_current(db: Session, account_id: int = False, _set: bool = False) -> Balance:
    """
    Auxiliary function (in the case where no row has the <is_current> flag) to retrieve the
    running total based on the most current <entry_datetime> date and time.

    :param db: (Session) SQLAlchemy ORM session.
    :param account_id: (int) optional; Account ID to determine its current Balance row. If not
        provided it will determine the "checking" account's Balance row.
    :param _set: (bool) optional; if True overwrite the <is_current> flag.
    :returns: (Balance) entry that is deemed as most recent.
    """
    # Build the query
    query = db.query(Balance).join(Transaction)
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    else:
        query = query.join(Account).filter(Account.is_checking)
    # Run the query
    current_balance = query.order_by(Balance.entry_datetime.desc()).first()
    # Optionally set the flag
    if current_balance and _set:
        current_balance.is_current = True
        db.add(current_balance)
    return current_balance


@router.get("/current", status_code=status.HTTP_200_OK, response_model=None)
async def get_current_balance(db: db_dependency, all_data: bool = False) -> Decimal | Balance:
    """
    Fetch the current account balance by using the "is_current" flag. Optionally return the
    whole balance entry data instead of the running total value.

    Note: will only look into the 'checking' account

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param all_data: (bool) Optionally return the complete balance entry instead of the scalar.
    :returns: either balance entry or current balance value.
    """
    current_balance = (
        db.query(Balance)
        .join(Transaction)
        .join(Account)
        .filter(Balance.is_current, Account.is_checking)
        .first()
    )
    # Determine latest balance entry by date/time if no entry is found
    if not current_balance:
        current_balance = get_time_based_current(db, _set=True)
    if not current_balance:
        raise HTTPException(status_code=404, detail="No entry found")
    if all_data:
        return current_balance
    return current_balance.running_total


@router.get(
    "/filterby/transaction/{id}",
    status_code=status.HTTP_200_OK,
    response_model=list[BalanceResponse],
)
async def get_transactions(db: db_dependency, id: int = Path(gt=0)):
    """
    Fetch the balance entries that are linked to a particular transaction.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param id: (int) ID of the transaction entry.
    :returns: (list) all the balance entries that match the transaction ID.
    """
    return db.query(Balance).filter(Balance.transaction_id == id).all()
