"""
filename: transaction.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definition of the transaction model.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from api.database import Base
from api.models.category import Category
from api.utils.tools import now_factory


class Transaction(Base):
    __tablename__ = "transaction"
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        doc="Unique identifier of the transaction entry",
    )
    payee = Column(String(100), doc="Name/title of the payee")
    creation_datetime = Column(
        DateTime,
        default=lambda _: now_factory,
        doc="Date/time of creation of the transaction entry in the database",
    )
    last_update_datetime = Column(
        DateTime,
        default=lambda _: now_factory,
        doc="Date/time of the last update operation of the transaction entry",
    )
    transaction_date = Column(
        Date, doc="Date of the transaction between the user and the payee"
    )
    description = Column(
        String(200),
        default="no description",
        doc="User defined description of the transaction entry",
    )
    amount = Column(
        Numeric(10, 2),
        doc="Transaction amount in euros, with a precision of two decimal places",
    )
    is_transfer = Column(
        Boolean,
        default=False,
        doc=(
            "Flag those transactions that record transferring between accounts; "
            "if True, <category_id> should be null"
        ),
    )
    category_id = Column(
        Integer,
        ForeignKey("category.id"),
        nullable=True,
        doc="Foreign key link to the category to which the transaction entry is bound to",
    )
    account_id = Column(
        Integer,
        ForeignKey("account.id"),
        doc="Foreign key link to the bank account associated to this transaction entry",
    )
    balances = relationship("Balance", cascade="delete")
    # TODO add column "is_orphaned" to mark transactions that have been left behind (category or account deleted)
