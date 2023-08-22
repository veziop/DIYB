from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field
from starlette import status

from database import db_dependency
from models import Transaction

router = APIRouter(prefix='/transactions')


class TransactionModel(BaseModel):
    payee: str = Field(min_length=2)
    creation_date: datetime = Field(default=datetime.now())
    transaction_date: datetime
    description: str = Field(min_length=2, max_length=100)
    amount: float = Field()


@router.get('/all')
async def read_all_transactions(db: db_dependency):
    return db.query(Transaction).all()


@router.post('/create', status_code=status.HTTP_201_CREATED)
async def create_new_transaction(db: db_dependency, transaction_request: TransactionModel):
    transaction_model = Transaction(**transaction_request.dict())
    db.add(transaction_model)
    db.commit()
