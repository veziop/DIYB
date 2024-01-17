"""
filename: account.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definition of the account model.
"""
from sqlalchemy import Column, Integer, String

from api.database import Base


class Account(Base):
    __tablename__ = "account"
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        doc="Unique identifier of the account entry",
    )
    name = Column(String(30), unique=True, doc="Name or alias of the account entry")
    description = Column(
        String(100),
        default="no description",
        doc="User defined description of the account entry",
    )
    iban_tail = Column(
        String(4),
        unique=True,
        nullable=True,
        doc="(optional) Last four digits of the IBAN to help identification",
    )
