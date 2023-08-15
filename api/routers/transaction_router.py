from fastapi import APIRouter

from database import db_dependency
from models import Transaction

router = APIRouter(prefix='/transactions')

@router.get('/all')
async def read_all_transactions(db: db_dependency):
    return db.query(Transaction).all()
