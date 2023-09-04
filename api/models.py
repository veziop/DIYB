"""
filename: models.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definitions all the project's models.
"""
from datetime import datetime

from database import Base
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Numeric, Date


class Transaction(Base):
    __tablename__ = "transaction"
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        doc="Unique identifier of the transaction entry",
    )
    payee = Column(String, name="payee", doc="Name/title of the payee")
    creation_datetime = Column(
        DateTime,
        default=datetime.now,
        doc="Date/time of creation of the transaction entry in the database",
    )
    last_update_datetime = Column(
        DateTime,
        default=datetime.now,
        doc="Date/time of the last update operation of the transaction entry",
    )
    transaction_date = Column(
        Date,
        doc="Date of the transaction between the user and the payee",
    )
    description = Column(
        String,
        default="no description",
        doc="User defined description of the transaction entry",
    )
    amount = Column(
        Numeric(10, 2),
        name="amount",
        doc="""Transaction amount in euros, with a precision of two decimal places""",
    )


class Balance(Base):
    __tablename__ = 'balance'
    id = Column(Integer, primary_key=True, index=True)
    datetime = Column(DateTime)
    amount = Column(Float)
    transaction_id = Column(Integer, ForeignKey('transaction.id'))
