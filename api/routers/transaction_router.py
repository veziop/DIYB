"""
filename: transaction_router.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definitions of routes related to the Transaction model.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Path
from pydantic import BaseModel, Field
from sqlalchemy import func
from starlette import status

from api.database import db_dependency
from api.models import Balance, Transaction
from api.routers.balance_router import create_balance_entry

router = APIRouter(prefix="/transaction", tags=["transaction"])


# Data verification using pydantic
class TransactionRequest(BaseModel):
    payee: str = Field(min_length=1)
    transaction_date: date = Field(default=date.today())
    description: str = Field(max_length=100)
    amount: Decimal = Field(decimal_places=2)


class TransactionResponse(BaseModel):
    id: int
    payee: str
    transaction_date: date
    creation_datetime: datetime
    last_update_datetime: datetime
    description: str
    amount: float


@router.get("/all", status_code=status.HTTP_200_OK, response_model=list[TransactionResponse])
async def read_all_transactions(db: db_dependency):
    """
    Endpoint to fetch all transaction entries from the database.

    :param db: (db_dependancy) SQLAlchemy ORM session.
    """
    return db.query(Transaction).all()


@router.get("/all/sum", status_code=status.HTTP_200_OK)
async def get_transactions_sum(db: db_dependency) -> float:
    """
    Endpoint to get the sum of all the transactions' amounts. Useful to check the validity of
    the Balance table and its "is_current" flag.

    :param db: (db_dependancy) SQLAlchemy ORM session.
    """
    return db.query(func.sum(Transaction.amount)).scalar()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_new_transaction(db: db_dependency, transaction_request: TransactionRequest):
    """
    Endpoint to create a new transaction entry in the database.

    :param db: (db_dependancy) SQLAlchemy ORM session.
    :param transaction_request: (TransactionRequest) data to be used to build a new
        transaction entry.
    """
    # Discard microseconds from the time data
    transaction_request_data = transaction_request.dict()
    transaction_request_data["creation_datetime"] = datetime.now().replace(microsecond=0)
    transaction_request_data["last_update_datetime"] = datetime.now().replace(microsecond=0)
    # Create the transaction model
    transaction_model = Transaction(**transaction_request_data)
    db.add(transaction_model)
    db.commit()
    # Create the balance model
    create_balance_entry(
        db=db,
        transaction_id=transaction_model.id,
        transaction_amount=transaction_model.amount,
    )


@router.get("/{id}", status_code=status.HTTP_200_OK, response_model=TransactionResponse)
async def get_transaction(db: db_dependency, id: int = Path(gt=0)):
    """
    Endpoint to get a specific transaction entry from the database.

    :param db: (db_dependancy) SQLAlchemy ORM session.
    :param id: (int) ID of the transaction entry.
    """
    # Fetch the model
    transaction_model = db.query(Transaction).filter(Transaction.id == id).first()
    # If found return the model
    if transaction_model:
        return transaction_model
    # If not found raise exception
    raise HTTPException(status_code=404, detail="Transaction not found")


@router.put("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_transaction(
    db: db_dependency,
    transaction_request: TransactionRequest,
    id: int = Path(gt=0),
):
    """
    Endpoint to modify an existing transaction entry from the database.

    :param db: (db_dependancy) SQLAlchemy ORM session.
    :param transaction_request: (TransactionRequest) data to be used to update the transaction
        entry.
    :param id: (int) ID of the transaction entry.
    """
    # Fetch the model
    transaction_model = db.query(Transaction).filter(Transaction.id == id).first()
    # If not found raise exception
    if not transaction_model:
        raise HTTPException(status_code=404, detail="Transaction not found")
    # Detect changes to the amount
    amount_changed = transaction_model.amount != transaction_request.amount
    amount_differance = transaction_request.amount - transaction_model.amount
    # Modify the existing data
    transaction_model.payee = transaction_request.payee
    transaction_model.transaction_date = transaction_request.transaction_date
    transaction_model.last_update_datetime = datetime.now().replace(microsecond=0)
    transaction_model.description = transaction_request.description
    transaction_model.amount = transaction_request.amount
    # Confirm the changes
    db.add(transaction_model)
    db.commit()
    # Create new balance entry
    if amount_changed:
        create_balance_entry(
            db=db,
            transaction_id=id,
            transaction_amount=amount_differance,
        )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    db: db_dependency,
    id: int = Path(gt=0),
):
    """
    Endpoint to delete an existing transaction entry from the database.

    :param db: (db_dependancy) SQLAlchemy ORM session.
    :param id: (int) ID of the transaction entry.
    """
    # Fetch the model
    transaction_model = db.query(Transaction).filter(Transaction.id == id).first()
    # If not found raise exception
    if not transaction_model:
        raise HTTPException(status_code=404, detail="Transaction not found")
    # Undo this transaction's balance influence
    create_balance_entry(db=db, transaction_id=id, transaction_amount=-transaction_model.amount)
    # Delete the transaction
    db.delete(transaction_model)
    db.commit()
