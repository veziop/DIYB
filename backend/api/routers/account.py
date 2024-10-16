"""
filename: account.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definitions of routes related to the Account model.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field, field_validator
from starlette import status

from api.database import db_dependency, sql_session
from api.models.account import Account
from api.models.balance import Balance
from api.models.transaction import Transaction
from api.routers.transaction import create_transfer_transactions
from api.utils.tools import validate_entries_in_db

router = APIRouter(prefix="/account", tags=["account"])


class AccountRequest(BaseModel):
    name: str = Field(min_length=2, max_length=30)
    description: str = Field(default="", max_length=100)
    iban_tail: str | None = Field(default=None, max_length=4, pattern="^[0-9]{4}$")


class AccountResponse(BaseModel):
    id: int
    name: str
    description: str
    is_checking: bool
    iban_tail: str | None
    running_total: float | None


class AccountPartialRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=30)
    description: str | None = Field(default=None, max_length=100)
    iban_tail: str | None = Field(default=None, max_length=4, pattern="^[0-9]{4}$")


class AccountTransferRequest(BaseModel):
    transfer_date: date
    amount: Decimal = Field(decimal_places=2, gt=0)
    description: str = Field(max_length=100)

    @field_validator("transfer_date")
    def validate_not_future_date(cls, value: date):
        """Validate that the date set as the transfer date is not set in the future"""
        if value > date.today():
            raise ValueError("Date cannot be in the future")
        return value


def create_checking_account() -> None:
    """Create the 'checking' account as the default account"""
    with sql_session() as db:
        accounts = db.query(Account).count()
        if accounts:
            return
        checking = Account(
            name="checking", description="default account", is_checking=True, iban_tail=None
        )
        db.add(checking)


@router.get(
    "/all",
    status_code=status.HTTP_200_OK,
    response_model=list[AccountResponse],
    response_model_exclude_defaults=True,
)
async def read_all_accounts(db: db_dependency):
    """
    Endpoint to retrieve all account entries from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    """
    return [
        {
            "id": account.id,
            "name": account.name,
            "description": account.description,
            "is_checking": account.is_checking,
            "iban_tail": account.iban_tail if account.iban_tail else None,
            "running_total": getattr(
                db.query(Balance)
                .join(Transaction)
                .filter(Balance.is_current, Transaction.account_id == account.id)
                .first(),
                "running_total",
                None,
            ),
        }
        for account in db.query(Account).all()
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_account(db: db_dependency, account_request: AccountRequest):
    """
    Endpoint to create an account entry the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param account_request: (AccountRequest) data to be used to create the account entry.
    """
    # Create the model
    account_model = Account(**account_request.model_dump())
    # Raise exception if values for <name> or <iban_tail> are not unique
    if db.query(Account).filter(Account.name == account_model.name).count():
        raise HTTPException(status_code=400, detail="Account name not unique")
    if (
        account_model.iban_tail
        and db.query(Account).filter(Account.iban_tail == account_model.iban_tail).count()
    ):
        raise HTTPException(status_code=400, detail="Account IBAN not unique")
    # Add the model to the database
    db.add(account_model)


@router.get(
    "/{id}",
    status_code=status.HTTP_200_OK,
    response_model=AccountResponse,
    response_model_exclude_unset=True,
)
async def get_account(db: db_dependency, id: int = Path(gt=0)):
    """
    Endpoint to retrieve an existing account entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param id: (int) ID of the account entry.
    """
    # Get the model from the database
    account_model = validate_entries_in_db(
        db=db,
        entries=[{"model": Account, "id_value": id, "return_model": True}],
    )["Account"]
    return {
        "id": account_model.id,
        "name": account_model.name,
        "description": account_model.description,
        "is_checking": account_model.is_checking,
        "iban_tail": account_model.iban_tail,
        "running_total": getattr(
            db.query(Balance)
            .join(Transaction)
            .filter(Balance.is_current, Transaction.account_id == id)
            .first(),
            "running_total",
            None,
        ),
    }


@router.patch("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def partially_update_account(
    db: db_dependency, account_partial_request: AccountPartialRequest, id: int = Path(gt=0)
):
    """
    Endpoint to partially modify an existing account entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param account_partial_request: (AccountPartialRequest) data to be used to update the
        account entry.
    :param id: (int) ID of the category entry.
    """
    # Fetch the model
    account_model = validate_entries_in_db(
        db=db,
        entries=[{"model": Account, "id_value": id, "return_model": True}],
    )["Account"]
    # Collect attributes to modify
    update_data = account_partial_request.model_dump(exclude_unset=True)
    # Update the model with the new data
    for attribute, value in update_data.items():
        setattr(account_model, attribute, value)
    # Update the data in database
    db.add(account_model)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(db: db_dependency, id: int = Path(gt=0)):
    """
    Endpoint to delete an existing account entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param id: (int) ID of the account entry.
    """
    # Fetch the model
    account_model = validate_entries_in_db(
        db=db, entries=[{"model": Account, "id_value": id, "return_model": True}]
    )["Account"]
    # If last account then abort deletion
    if db.query(Account).count() == 1:
        raise HTTPException(
            status_code=403, detail="Cannot delete last account entry in the database"
        )
    # Protect the "checking" account from deletion
    if account_model.is_checking:
        raise HTTPException(status_code=403, detail="Cannot delete the 'checking' account")
    # Protect accounts with funds (positive running totals)
    if getattr(
        db.query(Balance)
        .join(Transaction)
        .filter(Balance.is_current, Transaction.account_id == id)
        .first(),
        "running_total",
        None,
    ):
        raise HTTPException(
            status_code=403,
            detail="Cannot delete an account with funds. Please transfer funds and try again",
        )
    # Delete the account
    db.delete(account_model)


@router.post("/{id_from}/transfer/{id_to}", status_code=status.HTTP_204_NO_CONTENT)
async def transfer_between_accounts(
    db: db_dependency,
    transfer_request: AccountTransferRequest,
    id_from: int = Path(gt=0),
    id_to: int = Path(gt=0),
):
    """
    Transfer amounts from one account to another. The passed amount will be deducted
    from the "id_from" account to the "id_to" account. This process is done by creating new
    Transaction entries, one for each account. These entries will not have any category
    assigned to them.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param id_from: (int) ID of the account to transfer from.
    :param id_to: (int) ID of the account to transfer to.
    :param transfer_request: (AccountTransferRequest) body of request containing the amount to
        transfer between accounts.
    """
    # Validate the IDs
    from_account_model = validate_entries_in_db(
        db=db,
        entries=[{"model": Account, "id_value": id_from, "return_model": True}],
    )["Account"]
    to_account_model = validate_entries_in_db(
        db=db,
        entries=[{"model": Account, "id_value": id_to, "return_model": True}],
    )["Account"]
    # Halt if remaining is negative
    current_running_total = getattr(
        db.query(Balance)
        .join(Transaction)
        .filter(Balance.is_current, Transaction.account_id == id_from)
        .first(),
        "running_total",
        None,
    )
    if (
        current_running_total is not None
        and current_running_total - transfer_request.amount < 0
    ):
        raise HTTPException(
            status_code=403,
            detail="Transfer request would result in negative 'from account' amount",
        )
    create_transfer_transactions(
        db=db,
        from_account_model=from_account_model,
        to_account_model=to_account_model,
        transfer_date=transfer_request.transfer_date,
        amount=transfer_request.amount,
        description=transfer_request.description,
    )
