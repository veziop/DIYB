"""
filename: models.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definitions all the project's models.
"""
from datetime import datetime

from database import Base
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey


class Transaction(Base):
    __tablename__ = "transaction"
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        doc="Unique identifier of the transaction entry",
    )
    payee = Column(String, name="payee", doc="Name/title of the payee")
    creation_date = Column(
        DateTime,
        default=datetime.now,
        doc="Date/time of creation of the transaction entry",
    )
    last_update_date = Column(
        DateTime,
        default=datetime.now,
        doc="Date/time of the last update operation of the transaction entry",
    )
    transaction_date = Column(
        DateTime,
        doc="Date/time of the transaction between the user and the payee",
    )
    description = Column(
        String,
        default="no description",
        doc="User defined description of the transaction entry",
    )
    amount_cents = Column(
        Integer,
        doc="""Transaction amount in cents; 
        positive for inflow, negative for outflow;
        ie amount_cents of -1450 represent -14.50€""",
    )
    amount_whole = Column(
        Float,
        doc="""Transaction amount in euros; 
        this column is generated from the user's input in <ammount_cents>""",
    )


class Balance(Base):
    __tablename__ = 'balance'
    id = Column(Integer, primary_key=True, index=True)
    datetime = Column(DateTime)
    amount = Column(Float)
    transaction_id = Column(Integer, ForeignKey('transaction.id'))
