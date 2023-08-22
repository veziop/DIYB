from datetime import datetime

from fastapi import APIRouter, HTTPException, Path
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


@router.get('/get/{transaction_id}', status_code=status.HTTP_200_OK)
async def get_one_transaction(db: db_dependency, transaction_id: int = Path(gt=0)):
    transaction_model = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if transaction_model:
        return transaction_model
    raise HTTPException(status_code=404, detail='Transaction not found')
