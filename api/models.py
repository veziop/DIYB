"""
filename: models.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definitions all the project's models.
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String

from database import Base


class Transaction(Base):
    __tablename__ = "transaction"
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        doc="Unique identifier of the transaction entry",
    )
    payee = Column(String, doc="Name/title of the payee")
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
        doc="Transaction amount in euros, with a precision of two decimal places",
    )


class Balance(Base):
    __tablename__ = 'balance'
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        doc="Unique identifier of the balance entry",
    )
    entry_datetime = Column(
        DateTime,
        doc="Date/time of the balance entry",
    )
    running_total = Column(
        Numeric(10, 2),
        doc="Total amount in the bank account at the moment of <entry_datetime>"
    )
    is_current = Column(Boolean, doc="Whether this entry represent the actual state")
    transaction_id = Column(Integer, ForeignKey('transaction.id'))
