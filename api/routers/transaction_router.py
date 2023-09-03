"""
filename: transaction_router.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definitions of routes related to the Transaction model.
"""
from datetime import datetime

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from starlette import status

from database import db_dependency
from models import Transaction

router = APIRouter(prefix='/transactions')


# Data verification using pydantic
class TransactionRequest(BaseModel):
    payee: str = Field(min_length=2)
    creation_date: datetime = Field(default=datetime.now())
    transaction_date: datetime
    description: str = Field(min_length=2, max_length=100)
    amount: float = Field()


@router.get('/all', status_code=status.HTTP_200_OK)
async def read_all_transactions(db: db_dependency):
    return db.query(Transaction).all()


@router.post('/create', status_code=status.HTTP_201_CREATED)
async def create_new_transaction(db: db_dependency, transaction_request: TransactionRequest):
    transaction_model = Transaction(**transaction_request.dict())
    db.add(transaction_model)
    db.commit()


@router.get('/{transaction_id}', status_code=status.HTTP_200_OK)
async def get_one_transaction(db: db_dependency, transaction_id: int = Path(gt=0)):
    transaction_model = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if transaction_model:
        return transaction_model
    raise HTTPException(status_code=404, detail='Transaction not found')


@router.put('/update/{transaction_id}', status_code=status.HTTP_204_NO_CONTENT)
async def update_one_transaction(
    db: db_dependency,
    transaction_request: TransactionRequest,
    transaction_id: int = Path(gt=0),
):
    transaction_model = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction_model:
        raise HTTPException(status_code=404, detail='Transaction not found')
    transaction_model.payee = transaction_request.payee
    transaction_model.creation_date = transaction_request.creation_date
    transaction_model.transaction_date = transaction_request.transaction_date
    transaction_model.description = transaction_request.description
    transaction_model.amount = transaction_request.amount
    db.add(transaction_model)
    db.commit()
