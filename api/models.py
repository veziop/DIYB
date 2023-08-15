from database import Base
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey

class Transaction(Base):
    __tablename__ = 'transaction'
    id = Column(Integer, primary_key=True, index=True)
    payee = Column(String)
    datetime = Column(DateTime)
    description = Column(String)
    amount = Column(Float)


class Balance(Base):
    __tablename__ = 'balance'
    id = Column(Integer, primary_key=True, index=True)
    datetime = Column(DateTime)
    amount = Column(Float)
    transaction_id = Column(Integer, ForeignKey('transaction.id'))
