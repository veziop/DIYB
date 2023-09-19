"""
filename: transaction_router.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definitions of routes related to the Transaction model.
"""
from datetime import datetime, date
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from starlette import status

from database import db_dependency
from models import Transaction, Balance
from .balance_router import create_balance_entry

router = APIRouter(prefix="/transactions", tags=["transactions"])


# Data verification using pydantic
class TransactionRequest(BaseModel):
    payee: str = Field(min_length=1)
    transaction_date: date = Field(default=date.today())
    description: str = Field(max_length=100)
    amount: Decimal = Field(decimal_places=2)


@router.get("/all", status_code=status.HTTP_200_OK)
async def read_all_transactions(db: db_dependency):
    """
    Endpoint to fetch all transaction entries from the database.
    """
    return db.query(Transaction).all()


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_new_transaction(db: db_dependency, transaction_request: TransactionRequest):
    """
    Endpoint to create a new transaction entry in the database.
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


@router.get("/{transaction_id}", status_code=status.HTTP_200_OK)
async def get_one_transaction(db: db_dependency, transaction_id: int = Path(gt=0)):
    """
    Endpoint to get a specific transaction entry from the database.
    """
    # Fetch the model
    transaction_model = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    # If found return the model
    if transaction_model:
        return transaction_model
    # If not found raise exception
    raise HTTPException(status_code=404, detail="Transaction not found")


@router.put("/update/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_one_transaction(
    db: db_dependency,
    transaction_request: TransactionRequest,
    transaction_id: int = Path(gt=0),
):
    """
    Endpoint to modify an existing transaction entry from the database.
    """
    # Fetch the model
    transaction_model = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    # If not found raise exception
    if not transaction_model:
        raise HTTPException(status_code=404, detail="Transaction not found")
    # Modify the existing data
    transaction_model.payee = transaction_request.payee
    transaction_model.transaction_date = transaction_request.transaction_date
    transaction_model.last_update_datetime = datetime.now().replace(microsecond=0)
    transaction_model.description = transaction_request.description
    transaction_model.amount = transaction_request.amount
    # Confirm the changes
    db.add(transaction_model)
    db.commit()
