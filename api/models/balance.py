"""
filename: balance.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definition of the balance model.
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric

from api.database import Base


class Balance(Base):
    __tablename__ = "balance"
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        doc="Unique identifier of the balance entry",
    )
    entry_datetime = Column(DateTime, doc="Date/time of the balance entry")
    transaction_amount_record = Column(
        Numeric(10, 2),
        doc="Record of the transaction amount that was set when the balance entry "
        "was created/modified. Note: this is deliberately not a foreign key.",
    )
    running_total = Column(
        Numeric(10, 2), doc="Total amount in the bank account at the moment of <entry_datetime>"
    )
    is_current = Column(Boolean, doc="Whether this entry represent the actual state")
    transaction_id = Column(
        Integer,
        ForeignKey("transaction.id"),
        doc="Foreign key link to the transaction entry associated to this balance entry",
    )
