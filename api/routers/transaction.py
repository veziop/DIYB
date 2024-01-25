"""
filename: transaction.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definitions of routes related to the Transaction model.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field, condecimal, validator
from sqlalchemy import func
from starlette import status

from api.database import db_dependency
from api.models.transaction import Transaction
from api.routers.balance import create_balance_entry
from api.routers.category import update_category_amount

router = APIRouter(prefix="/transaction", tags=["transaction"])


class TransactionRequest(BaseModel):
    """
    Request model for data validation
    """

    payee: str = Field(min_length=1)
    transaction_date: date = Field(default=date.today())
    description: str = Field(max_length=100)
    amount: Decimal = Field(decimal_places=2)
    category_id: int = Field(gt=0)
    account_id: int = Field(gt=0)

    @validator("transaction_date")
    def validate_not_future_date(cls, value: date):
        """Validate that the date set as the transaction date is not set in the future"""
        if value > date.today():
            raise ValueError("Date cannot be in the future")
        return value

    @validator("amount")
    def validate_amount_not_zero(cls, value: Decimal):
        """Validate that the amount has some positive or negative value, but not zero"""
        if value == Decimal(0):
            raise ValueError("Amount cannot be zero")
        return value


class TransactionPartialRequest(TransactionRequest):
    """
    Separate request model for partial updates. This distinction is needed for assigning
    default values to all attributes, thus allowing only some attributes to be submitted.
    Furthermore, model inheritance will reuse the validators.
    """

    payee: str | None = Field(default=None, min_length=1)
    transaction_date: date | None = Field(default=date.today())
    description: str | None = Field(default=None, max_length=100)
    amount: Annotated[condecimal(decimal_places=2) | None, Field(default=None)]
    category_id: int | None = Field(default=None, gt=0)
    account_id: int | None = Field(default=None, gt=0)


class TransactionResponse(BaseModel):
    """
    Response model to validate the response data.
    """

    id: int
    payee: str
    transaction_date: date
    creation_datetime: datetime
    last_update_datetime: datetime
    description: str
    amount: float
    category_id: int
    account_id: int


@router.get("/all", status_code=status.HTTP_200_OK, response_model=list[TransactionResponse])
async def read_all_transactions(db: db_dependency):
    """
    Endpoint to fetch all transaction entries from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    """
    return db.query(Transaction).all()


@router.get("/all/sum", status_code=status.HTTP_200_OK)
async def get_transactions_sum(db: db_dependency) -> float:
    """
    Endpoint to get the sum of all the transactions' amounts. Useful to check the validity of
    the Balance table and its "is_current" flag.

    :param db: (db_dependency) SQLAlchemy ORM session.
    """
    return db.query(func.sum(Transaction.amount)).scalar()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_new_transaction(db: db_dependency, transaction_request: TransactionRequest):
    """
    Endpoint to create a new transaction entry in the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param transaction_request: (TransactionRequest) data to be used to build a new
        transaction entry.
    """
    # Discard microseconds from the time data
    transaction_request_data = transaction_request.model_dump()
    transaction_request_data["creation_datetime"] = datetime.now().replace(microsecond=0)
    transaction_request_data["last_update_datetime"] = datetime.now().replace(microsecond=0)
    # Create the transaction model
    transaction_model = Transaction(**transaction_request_data)
    # If money inflow, overwrite the default 'stage' category
    if transaction_model.amount > 0:
        transaction_model.category_id = 1
    # Add the model to the database
    db.add(transaction_model)
    # Flush the session so to get access to the id before the row is commited
    db.flush()
    # Update the category entry's amount
    update_category_amount(
        db=db, category_id=transaction_model.category_id, amount=transaction_model.amount
    )
    # Create the balance model
    create_balance_entry(
        db=db,
        transaction_id=transaction_model.id,
        amount_difference=transaction_model.amount,
    )


@router.get("/{id}", status_code=status.HTTP_200_OK, response_model=TransactionResponse)
async def get_transaction(db: db_dependency, id: int = Path(gt=0)):
    """
    Endpoint to get a specific transaction entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param id: (int) ID of the transaction entry.
    """
    # Fetch the model
    transaction_model = db.query(Transaction).filter(Transaction.id == id).first()
    # If found return the model
    if transaction_model:
        return transaction_model
    # If not found raise exception
    raise HTTPException(status_code=404, detail="Transaction not found")


@router.put("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_transaction(
    db: db_dependency,
    transaction_request: TransactionRequest,
    id: int = Path(gt=0),
):
    """
    Endpoint to modify an existing transaction entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param transaction_request: (TransactionRequest) data to be used to update the transaction
        entry.
    :param id: (int) ID of the transaction entry.
    """
    # Fetch the model
    transaction_model = db.query(Transaction).filter(Transaction.id == id).first()
    # If not found raise exception
    if not transaction_model:
        raise HTTPException(status_code=404, detail="Transaction not found")
    # Detect changes to the amount
    amount_changed = transaction_model.amount != transaction_request.amount
    amount_difference = transaction_request.amount - transaction_model.amount
    # Modify the existing data
    transaction_model.payee = transaction_request.payee
    transaction_model.transaction_date = transaction_request.transaction_date
    transaction_model.last_update_datetime = datetime.now().replace(microsecond=0)
    transaction_model.description = transaction_request.description
    transaction_model.amount = transaction_request.amount
    transaction_model.category_id = transaction_request.category_id
    transaction_model.account_id = transaction_request.account_id
    # Confirm the changes
    db.add(transaction_model)
    # Create new balance entry and update the category
    if amount_changed:
        update_category_amount(
            db=db, category_id=transaction_model.category_id, amount=amount_difference
        )
        create_balance_entry(
            db=db,
            transaction_id=id,
            amount_difference=amount_difference,
            transaction_amount=transaction_request.amount,
        )


@router.patch("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def partially_update_transaction(
    db: db_dependency,
    new_data: TransactionPartialRequest,
    id: int = Path(gt=0),
):
    """
    Endpoint to partially modify an existing transaction entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param new_data: (TransactionPartialRequest) data to be used to update the transaction
        entry.
    :param id: (int) ID of the transaction entry.
    """
    # Fetch the model
    transaction_model = db.query(Transaction).filter(Transaction.id == id).first()
    # If not found raise exception
    if not transaction_model:
        raise HTTPException(status_code=404, detail="Transaction not found")
    # Collect attributes to modify
    update_data = new_data.model_dump(exclude_unset=True)
    # Detect changes to the amount
    amount_changed = "amount" in update_data
    amount_difference = update_data.get("amount", 0) - transaction_model.amount
    # Update the model with the new data
    transaction_model.last_update_datetime = datetime.now().replace(microsecond=0)
    for attribute, value in update_data.items():
        setattr(transaction_model, attribute, value)
    # Update the data in database
    db.add(transaction_model)
    # Create new balance entry and update the category
    if amount_changed:
        update_category_amount(
            db=db, category_id=transaction_model.category_id, amount=amount_difference
        )
        create_balance_entry(
            db=db,
            transaction_id=id,
            amount_difference=amount_difference,
            transaction_amount=update_data.get("amount"),
        )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    db: db_dependency,
    id: int = Path(gt=0),
):
    """
    Endpoint to delete an existing transaction entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param id: (int) ID of the transaction entry.
    """
    # Fetch the model
    transaction_model = db.query(Transaction).filter(Transaction.id == id).first()
    # If not found raise exception
    if not transaction_model:
        raise HTTPException(status_code=404, detail="Transaction not found")
    # Undo this transaction's balance influence
    create_balance_entry(db=db, transaction_id=id, amount_difference=-transaction_model.amount)
    # Undo this transaction's category influence
    update_category_amount(
        db=db, category_id=transaction_model.category_id, amount=-transaction_model.amount
    )
    # Delete the transaction
    db.delete(transaction_model)
