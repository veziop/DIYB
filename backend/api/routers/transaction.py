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
from pydantic import BaseModel, Field, condecimal, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette import status

from api.database import db_dependency
from api.models.account import Account
from api.models.balance import Balance
from api.models.category import Category
from api.models.transaction import Transaction
from api.routers.balance import (
    create_balance_entry,
    delete_balance_entries,
    get_time_based_current,
)
from api.routers.category import update_category_amount
from api.utils.tools import today_factory, validate_entries_in_db

router = APIRouter(prefix="/transaction", tags=["transaction"])


class TransactionRequest(BaseModel):
    """
    Request model for data validation
    """

    payee: str = Field(min_length=1)
    transaction_date: date = Field(default_factory=today_factory)
    description: str = Field(max_length=100)
    amount: Decimal = Field(decimal_places=2)
    category_id: int | None = Field(default=None, gt=0)
    account_id: int = Field(default=1, gt=0)

    @field_validator("transaction_date")
    def validate_not_future_date(cls, value: date):
        """Validate that the the transaction date is not set in the future"""
        if value > today_factory():
            raise ValueError("Date cannot be in the future")
        return value

    @field_validator("amount")
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
    transaction_date: date | None = Field(default_factory=today_factory)
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
    is_transfer: bool
    category_id: int | None
    account_id: int


def create_new_transaction_entry(
    db: Session, transaction_data: dict, datetime_now: datetime = None
):
    """
    Function for creating new Transaction entries. Useful for reusing in:
        1. endpoint for creating new Transactions.
        2. endpoint for creating two "transfer" Transactions between two Accounts.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param transaction_data: (dict) data for the new entry.
    :param datetime_now: (datetime) optional; current date-time.
    """
    # Determine when is now
    if datetime_now is None:
        datetime_now = datetime.now().replace(microsecond=0)
        # Discard microseconds from the time data
        transaction_data["creation_datetime"] = datetime_now
        transaction_data["last_update_datetime"] = datetime_now
    # Abort if no account is found
    validate_entries_in_db(
        db=db,
        entries=[
            {
                "model": Account,
                "id_value": transaction_data["account_id"],
                "return_model": False,
            },
        ],
    )
    # Validate category (if new transaction is not a transfer between accounts)
    if transaction_data.get("category_id") and not transaction_data.get("is_transfer"):
        category_model = validate_entries_in_db(
            db=db,
            entries=[
                {
                    "model": Category,
                    "id_value": transaction_data["category_id"],
                    "return_model": True,
                },
            ],
        )["Category"]
        # Abort if the operation results in a negative category amount
        if transaction_data["amount"] + category_model.assigned_amount < 0:
            raise HTTPException(
                status_code=400, detail="Category assigned amount would become negative"
            )
    # Create the transaction model
    transaction_model = Transaction(**transaction_data)
    # Fetch the stage category
    stage_category_model = db.query(Category).filter(Category.is_stage).first()
    # If money inflow, overwrite the default 'stage' category
    if transaction_model.amount > 0 and not transaction_model.is_transfer:
        transaction_model.category_id = 1
    # If money outflow, halt if the category is the 'stage' category
    if (
        transaction_model.amount < 0
        and transaction_model.category_id == stage_category_model.id
    ):
        raise HTTPException(
            status_code=403, detail="Cannot have money outflow from 'stage' category"
        )
    # Add the model to the database
    db.add(transaction_model)
    # Flush the session so to get access to the id before the entry is committed
    db.flush()
    # Update the category entry's amount (if not a transfer between accounts)
    if transaction_model.category_id is not None and not transaction_model.is_transfer:
        update_category_amount(
            db=db, category_id=transaction_model.category_id, amount=transaction_model.amount
        )
    # Create the balance model
    create_balance_entry(
        db=db,
        transaction_id=transaction_model.id,
        account_id=transaction_model.account_id,
        amount_difference=transaction_model.amount,
    )


def create_transfer_transactions(
    db: Session,
    from_account_model: Account,
    to_account_model: Account,
    transfer_date: date,
    amount: Decimal,
    description: str,
):
    """
    Function to create Transaction and Balance entries for transfers between Accounts. A common
    datetime object is computed for current datetime at runtime and shared between both
    Transactions so to guarantee the same time of day. Same idea with the <transfer_date>
    parameter, but this one is not computed but rather input by the user.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param from_account_model: (Account) Account model to transfer from (origin).
    :param to_account_model: (Account) Account model to transfer to (destination).
    :param transfer_date: (date) date of the transfer between the accounts.
    :param amount: (Decimal) amount to transfer between the accounts.
    :param description: (str) description of the transfer, duplicated in both Transactions.
    """
    datetime_now = datetime.now().replace(microsecond=0)
    # Origin account's transaction
    transaction_from_data = {
        # Label the payee as the other account's name to help the user with identifying
        "payee": f"Transfer: {to_account_model.name}",
        "transaction_date": transfer_date,
        "description": description,
        "creation_datetime": datetime_now,
        "last_update_datetime": datetime_now,
        "amount": -abs(amount),
        "is_transfer": True,
        "category_id": None,
        "account_id": from_account_model.id,
    }
    create_new_transaction_entry(db, transaction_from_data)
    # Destination account's transaction
    transaction_to_data = {
        # Label the payee as the other account's name to help the user with identifying
        "payee": f"Transfer: {from_account_model.name}",
        "transaction_date": transfer_date,
        "description": description,
        "creation_datetime": datetime_now,
        "last_update_datetime": datetime_now,
        "amount": abs(amount),
        "is_transfer": True,
        "category_id": None,
        "account_id": to_account_model.id,
    }
    create_new_transaction_entry(db, transaction_to_data)


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
    create_new_transaction_entry(db, transaction_request.model_dump())


@router.get("/{id}", status_code=status.HTTP_200_OK, response_model=TransactionResponse)
async def get_transaction(db: db_dependency, id: int = Path(gt=0)):
    """
    Endpoint to get a specific transaction entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param id: (int) ID of the transaction entry.
    """
    # Validate the ID and return the model
    return validate_entries_in_db(
        db=db, entries=[{"model": Transaction, "id_value": id, "return_model": True}]
    )["Transaction"]


@router.patch("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def partially_update_transaction(
    db: db_dependency,
    transaction_partial_request: TransactionPartialRequest,
    id: int = Path(gt=0),
):
    """
    Endpoint to partially modify an existing transaction entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param transaction_partial_request: (TransactionPartialRequest) data to be used to update
        the transaction entry.
    :param id: (int) ID of the transaction entry.
    """
    # Collect attributes to modify
    update_data = transaction_partial_request.model_dump(exclude_unset=True)
    # Validate the requested IDs
    validations = validate_entries_in_db(
        db=db,
        entries=[
            {"model": Transaction, "id_value": id, "return_model": True},
            (
                {
                    "model": Account,
                    "id_value": update_data["account_id"],
                    "return_model": True,
                }
                if update_data.get("account_id")
                else None
            ),
            (
                {
                    "model": Category,
                    "id_value": update_data["category_id"],
                    "return_model": True,
                }
                if update_data.get("category_id")
                else None
            ),
        ],
    )
    # Collect the transaction and account model from the validation
    transaction_model, account_model = validations["Transaction"], validations.get("Account")
    # If no new category was requested, fetch the transaction's category
    category_model = validations.get(
        "Category",
        db.query(Category).filter(Category.id == transaction_model.category_id).first(),
    )
    # If money outflow, halt if the category is the 'stage' category
    if (update_data.get("amount", 0) < 0 or transaction_model.amount < 0) and (
        update_data.get("category_id", 0) == 1 or category_model.is_stage
    ):
        raise HTTPException(
            status_code=403, detail="Cannot have money outflow from 'stage' category"
        )
    # Detect changes to the amount
    amount_changed = (
        "amount" in update_data and update_data["amount"] != transaction_model.amount
    )
    amount_difference = update_data.get("amount", 0) - transaction_model.amount
    # Detect a change in the <category_id>
    category_changed = (
        update_data.get("category_id")
        and update_data["category_id"] != transaction_model.category_id
    )
    # Detect a change in the <account_id>
    account_changed = account_model and account_model.id != transaction_model.account_id
    # Abort if the result of the operation is a negative category assigned_amount
    if amount_changed and category_model.assigned_amount + amount_difference < 0:
        raise HTTPException(
            status_code=400, detail="Category assigned amount would become negative"
        )
    if category_changed:
        # If category changed, undo the previous category's amount
        update_category_amount(
            db=db, category_id=transaction_model.category_id, amount=-transaction_model.amount
        )
        # Update the new category's amount
        update_category_amount(
            db=db,
            category_id=update_data["category_id"],
            amount=update_data.get("amount", transaction_model.amount),
        )
    # Abort if the result of the operation is a negative account <running_total>
    origin_account_total = (
        db.query(Balance)
        .join(Transaction)
        .filter(
            Balance.is_current,
            Transaction.account_id == transaction_model.account_id,
        )
        .first()
        .running_total
    )
    if not account_changed and amount_changed and origin_account_total + amount_difference < 0:
        raise HTTPException(
            status_code=400, detail="Account running total would become negative"
        )
    if account_changed:
        # Halt if operation results in any negative account amount
        destination_account_total = getattr(
            db.query(Balance)
            .join(Transaction)
            .filter(
                Balance.is_current,
                Transaction.account_id == update_data["account_id"],
            )
            .first(),
            "running_total",
            0,
        )
        previous_balance_model = (
            db.query(Balance)
            .join(Transaction)
            .filter(
                Transaction.id == transaction_model.id,
                Transaction.account_id == transaction_model.account_id,
            )
            .order_by(Balance.entry_datetime.desc())
            .first()
        )
        # Key question is: by undoing the transaction or creating a new one would we end up with
        # negative account amounts?
        negative_accounts = [
            (
                not amount_changed
                and transaction_model.amount > 0
                and origin_account_total - transaction_model.amount < 0
            ),
            (
                not amount_changed
                and transaction_model.amount < 0
                and destination_account_total + transaction_model.amount < 0
            ),
            (
                amount_changed
                and update_data["amount"] > 0
                and origin_account_total - update_data["amount"] < 0
            ),
            (
                amount_changed
                and update_data["amount"] < 0
                and destination_account_total + update_data["amount"] < 0
            ),
        ]
        if any(negative_accounts):
            raise HTTPException(
                status_code=400,
                detail="Previous or new account's running total would become negative",
            )
        # If the previous balance model was flagged as <is_current>, flag the previous Balance
        # entry (table-wide) according to the datetime
        if (
            get_time_based_current(db, transaction_model.account_id).id
            == previous_balance_model.id
        ):
            delete_balance_entries(db=db, transaction_id=id)
            get_time_based_current(db=db, account_id=transaction_model.account_id, _set=True)
        else:
            # Delete the previous transaction's balance entry/ies
            delete_balance_entries(db=db, transaction_id=id)
        # Create new balance entry if amount has not changed so to guarantee that a balance
        # entry is created
        if not amount_changed:
            create_balance_entry(
                db=db,
                transaction_id=id,
                account_id=update_data["account_id"],
                amount_difference=transaction_model.amount,
                transaction_amount=transaction_model.amount,
            )
        # Overwrite the amount_difference so to reflect the new entry's amount
        else:
            amount_difference = update_data["amount"]
    # Update the existing model with the new data
    transaction_model.last_update_datetime = datetime.now().replace(microsecond=0)
    for attribute, value in update_data.items():
        setattr(transaction_model, attribute, value)
    # Update the data in database
    db.add(transaction_model)
    # Create new balance entry and update the category
    if amount_changed:
        # Avoid re-running the update of category amount if it has already run
        if not category_changed:
            update_category_amount(
                db=db, category_id=transaction_model.category_id, amount=amount_difference
            )
        create_balance_entry(
            db=db,
            transaction_id=id,
            account_id=transaction_model.account_id,
            amount_difference=amount_difference,
            transaction_amount=update_data["amount"],
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
    # Validate the requested ID and collect the model
    transaction_model = validate_entries_in_db(
        db=db, entries=[{"model": Transaction, "id_value": id, "return_model": True}]
    )["Transaction"]
    # Undo this transaction's balance influence
    create_balance_entry(
        db=db,
        transaction_id=id,
        account_id=transaction_model.account_id,
        amount_difference=-transaction_model.amount,
    )
    # Undo this transaction's category influence
    update_category_amount(
        db=db, category_id=transaction_model.category_id, amount=-transaction_model.amount
    )
    # Delete the transaction
    db.delete(transaction_model)
