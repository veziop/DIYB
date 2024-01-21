"""
filename: account.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definitions of routes related to the Account model.
"""
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from starlette import status

from api.database import db_dependency, sql_session
from api.models.account import Account

router = APIRouter(prefix="/account", tags=["account"])


class AccountRequest(BaseModel):
    name: str = Field(min_length=2, max_length=30)
    description: str = Field(max_length=100)
    iban_tail: str | None = Field(default=None, pattern="^[0-9]{4}$")


class AccountResponse(BaseModel):
    name: str
    description: str
    iban_tail: str | None = None


class AccountPartialRequest(BaseModel):
    name: str = None
    description: str = None
    iban_tail: str = None


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
    return db.query(Account).all()


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
    if db.query(Account).filter(Account.name == account_model.name).first():
        raise HTTPException(status_code=503, detail="Account name not unique")
    if (
        account_model.iban_tail
        and db.query(Account).filter(Account.iban_tail == account_model.iban_tail).first()
    ):
        raise HTTPException(status_code=503, detail="Account IBAN not unique")
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
    account_model = db.query(Account).filter(Account.id == id).first()
    # Return the model if found
    if account_model:
        return account_model
    raise HTTPException(status_code=404, detail="Account not found")


@router.put("/{id}", status_code=status.HTTP_200_OK)
async def update_account(
    db: db_dependency,
    account_request: AccountRequest,
    id: int = Path(gt=0),
):
    """
    Endpoint to modify an existing account entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param account_request: (AccountRequest) data to be used to update the account entry.
    :param id: (int) ID of the account entry.
    """
    # Fetch the model
    account_model = db.query(Account).filter(Account.id == id).first()
    # If not found raise exception
    if not account_model:
        raise HTTPException(status_code=404, detail="Account not found")
    # Modify the existing data
    account_model.name = account_request.name
    account_model.description = account_request.description
    # Confirm the changes
    db.add(account_model)


@router.patch("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def partially_update_account(
    db: db_dependency,
    new_data: AccountPartialRequest,
    id: int = Path(gt=0),
):
    """
    Endpoint to partially modify an existing account entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param new_data: (AccountPartialRequest) data to be used to update the account entry.
    :param id: (int) ID of the category entry.
    """
    # Fetch the model
    account_model = db.query(Account).filter(Account.id == id).first()
    # If not found raise exception
    if not account_model:
        raise HTTPException(status_code=404, detail="Acount not found")
    # Collect attributes to modify
    update_data = new_data.model_dump(exclude_unset=True)
    # Manual validation as pydantic partial model had none
    for attribute, value in update_data.items():
        match attribute:
            case "title":
                if len(value) > 40:
                    raise ValueError("Attr <title> must be less than 30 character in length")
                if len(value) < 2:
                    raise ValueError("Attr <title> must be at least 2 character in length")
            case "description":
                if len(value) > 100:
                    raise ValueError("Attr <description> cannot be over 100 characters")
        setattr(account_model, attribute, value)
    # Update the data in database
    db.add(account_model)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    db: db_dependency,
    id: int = Path(gt=0),
):
    """
    Endpoint to delete an existing account entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param id: (int) ID of the account entry.
    """
    # Fetch the model
    account_model = db.query(Account).filter(Account.id == id).first()
    # If not found raise exception
    if not account_model:
        raise HTTPException(status_code=404, detail="Account not found")
    # If last account then abort deletion
    if len(db.query(Account).all()) == 1:
        raise HTTPException(
            status_code=503, detail="Cannot delete last account entry in the database"
        )
    # Delete the category
    db.delete(account_model)
