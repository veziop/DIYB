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
from models import Transaction

router = APIRouter(prefix="/transactions")


# Data verification using pydantic
class TransactionRequest(BaseModel):
    payee: str = Field(min_length=1)
    transaction_date: date = Field(default=date.today())
    description: str = Field(max_length=100)
    amount: Decimal = Field(decimal_places=2)


@router.get("/all", status_code=status.HTTP_200_OK)
async def read_all_transactions(db: db_dependency):
    return db.query(Transaction).all()


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_new_transaction(db: db_dependency, transaction_request: TransactionRequest):
    transaction_request_data = transaction_request.dict()
    transaction_request_data["creation_datetime"] = datetime.now().replace(microsecond=0)
    transaction_request_data["last_update_datetime"] = datetime.now().replace(microsecond=0)
    transaction_model = Transaction(**transaction_request_data)
    db.add(transaction_model)
    db.commit()


@router.get("/{transaction_id}", status_code=status.HTTP_200_OK)
async def get_one_transaction(db: db_dependency, transaction_id: int = Path(gt=0)):
    transaction_model = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if transaction_model:
        return transaction_model
    raise HTTPException(status_code=404, detail="Transaction not found")


@router.put("/update/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_one_transaction(
    db: db_dependency,
    transaction_request: TransactionRequest,
    transaction_id: int = Path(gt=0),
):
    transaction_model = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction_model:
        raise HTTPException(status_code=404, detail="Transaction not found")
    transaction_model.payee = transaction_request.payee
    transaction_model.transaction_date = transaction_request.transaction_date
    transaction_model.last_update_datetime = datetime.now().replace(microsecond=0)
    transaction_model.description = transaction_request.description
    transaction_model.amount = transaction_request.amount
    db.add(transaction_model)
    db.commit()
