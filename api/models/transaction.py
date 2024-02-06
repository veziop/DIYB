"""
filename: transaction.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definition of the transaction model.
"""
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String

from api.database import Base
from api.models.category import Category


class Transaction(Base):
    __tablename__ = "transaction"
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        doc="Unique identifier of the transaction entry",
    )
    payee = Column(String(30), doc="Name/title of the payee")
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
        String(100),
        default="no description",
        doc="User defined description of the transaction entry",
    )
    amount = Column(
        Numeric(10, 2),
        doc="Transaction amount in euros, with a precision of two decimal places",
    )
    category_id = Column(
        Integer,
        ForeignKey("category.id"),
        doc="Foreign key link to the category to which the transaction entry is bound to",
    )
    account_id = Column(
        Integer,
        ForeignKey("account.id"),
        doc="Foreign key link to the bank account associated to this transaction entry",
    )
