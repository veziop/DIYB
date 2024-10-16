"""
filename: category.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definition of the category model.
"""

from decimal import Decimal

from sqlalchemy import Boolean, Column, Integer, Numeric, String
from sqlalchemy.orm import relationship

from api.database import Base


class Category(Base):
    __tablename__ = "category"
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        doc="Unique identifier of the category entry",
    )
    title = Column(String(length=30), unique=True, doc="Title or name of the category entry")
    description = Column(
        String(length=100),
        default="no description",
        doc="User defined description of the category entry",
    )
    assigned_amount = Column(
        Numeric(10, 2),
        default=Decimal(0),
        doc="Remaining amount assigned to this category entry",
    )
    is_stage = Column(Boolean, default=False, doc='Flag to mark the "stage" category')
    transactions = relationship("Transaction")
