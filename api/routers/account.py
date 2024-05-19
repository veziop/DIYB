"""
filename: account.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definitions of routes related to the Account model.
"""

from decimal import Decimal

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
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
    is_current: bool
    iban_tail: str | None
    running_total: float | None


class AccountPartialRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=30)
    description: str | None = Field(default=None, max_length=100)
    iban_tail: str | None = Field(default=None, max_length=4, pattern="^[0-9]{4}$")


class AccountTransferRequest(BaseModel):
    amount: Decimal = Field(decimal_places=2, gt=0)


def create_current_account():
    """Create the 'current' account as the default account"""
    with sql_session() as db:
        accounts = db.query(Account).count()
        if accounts:
            return
        current = Account(
            name="current", description="default account", is_current=True, iban_tail=None
        )
        db.add(current)


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
            "is_current": account.is_current,
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
        "is_current": account_model.is_current,
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


@router.put("/{id}", status_code=status.HTTP_200_OK)
async def update_account(
    db: db_dependency, account_request: AccountRequest, id: int = Path(gt=0)
):
    """
    Endpoint to modify an existing account entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param account_request: (AccountRequest) data to be used to update the account entry.
    :param id: (int) ID of the account entry.
    """
    # Fetch the model
    account_model = validate_entries_in_db(
        db=db,
        entries=[{"model": Account, "id_value": id, "return_model": True}],
    )["Account"]
    # Modify the existing data
    account_model.name = account_request.name
    account_model.description = account_request.description
    if account_request.iban_tail:
        account_model.iban_tail = account_request.iban_tail
    # Confirm the changes
    db.add(account_model)


@router.patch("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def partially_update_account(
    db: db_dependency, new_data: AccountPartialRequest, id: int = Path(gt=0)
):
    """
    Endpoint to partially modify an existing account entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param new_data: (AccountPartialRequest) data to be used to update the account entry.
    :param id: (int) ID of the category entry.
    """
    # Fetch the model
    account_model = validate_entries_in_db(
        db=db,
        entries=[{"model": Account, "id_value": id, "return_model": True}],
    )["Account"]
    # Collect attributes to modify
    update_data = new_data.model_dump(exclude_unset=True)
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
        db=db,
        entries=[{"model": Account, "id_value": id, "return_model": True}],
    )["Account"]
    # If last account then abort deletion
    if db.query(Account).count() == 1:
        raise HTTPException(
            status_code=403, detail="Cannot delete last account entry in the database"
        )
    # Delete the category
    db.delete(account_model)


@router.post("/{id_from}/transfer/{id_to}", status_code=status.HTTP_204_NO_CONTENT)
async def transfer_between_accounts(
    db: db_dependency, id_from: int, id_to: int, transfer_request: AccountTransferRequest
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
        amount=transfer_request.amount,
    )
