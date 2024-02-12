"""
filename: category.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definitions of routes related to the Category model.
"""

from decimal import Decimal

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from starlette import status

from api.database import db_dependency, sql_session
from api.models.category import Category

router = APIRouter(prefix="/category", tags=["category"])


class CategoryRequest(BaseModel):
    title: str = Field(min_length=2, max_length=40)
    description: str = Field(max_length=100)


class CategoryResponse(BaseModel):
    id: int
    title: str
    description: str
    assigned_amount: float


class CategoryPartialRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=40)
    description: str | None = Field(default=None, max_length=100)


class MoveRequest(BaseModel):
    id_to: int = Field(default=2, gt=0)
    amount: Decimal = Field(gt=0, decimal_places=2)


def create_staging_category() -> None:
    """Create the main category from which to assign to all others."""
    with sql_session() as db:
        categories = db.query(Category).count()
        if categories:
            return
        stage_model = Category(
            title="stage",
            description="stage category to assign to all other categories",
        )
        db.add(stage_model)


def update_category_amount(db: db_dependency, category_id: int, amount: float) -> None:
    """Update the assigned amount of a category entry with the transaction amount."""
    # Fetch the category entry
    category_model = db.query(Category).filter(Category.id == category_id).first()
    # Update the assigned amount
    category_model.assigned_amount += amount
    # Apply the changes to the database
    db.add(category_model)


@router.get("/all", status_code=status.HTTP_200_OK, response_model=list[CategoryResponse])
async def read_all_categories(db: db_dependency):
    """
    Endpoint to fetch all category entries from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    """
    return db.query(Category).all()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_category(db: db_dependency, category_request: CategoryRequest):
    """
    Endpoint to create a new category entry in the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param category_request: (CategoryRequest) data to be used to build a new
        category entry.
    """
    # Create the category model
    category_model = Category(**category_request.model_dump())
    # Upload model to the database
    db.add(category_model)


@router.get("/{id}", status_code=status.HTTP_200_OK, response_model=CategoryResponse)
async def get_category(db: db_dependency, id: int = Path(gt=0)):
    """
    Endpoint to fetch a specific category entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param id: (int) ID of the category entry.
    """
    # Fetch the entry from the db
    category_model = db.query(Category).filter(Category.id == id).first()
    # If found return the model
    if category_model:
        return category_model
    # If not found raise exception
    raise HTTPException(status_code=404, detail="Category entry not found")


@router.put("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_category(
    db: db_dependency,
    category_request: CategoryRequest,
    id: int = Path(gt=0),
):
    """
    Endpoint to modify an existing category entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param category_request: (CategoryRequest) data to be used to update the category
        entry.
    :param id: (int) ID of the category entry.
    """
    # Fetch the model
    category_model = db.query(Category).filter(Category.id == id).first()
    # If not found raise exception
    if not category_model:
        raise HTTPException(status_code=404, detail="Category not found")
    # Modify the existing data
    category_model.title = category_request.title
    category_model.description = category_request.description
    # Confirm the changes
    db.add(category_model)


@router.patch("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def partially_update_category(
    db: db_dependency,
    new_data: CategoryPartialRequest,
    id: int = Path(gt=0),
):
    """
    Endpoint to partially modify an existing category entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param new_data: (CategoryPartialRequest) data to be used to update the category
        entry.
    :param id: (int) ID of the category entry.
    """
    # Fetch the model
    category_model = db.query(Category).filter(Category.id == id).first()
    # If not found raise exception
    if not category_model:
        raise HTTPException(status_code=404, detail="Category not found")
    # Collect attributes to modify
    update_data = new_data.model_dump(exclude_unset=True)
    # Update the model with the new data
    for attribute, value in update_data.items():
        setattr(category_model, attribute, value)
    # Update the data in database
    db.add(category_model)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    db: db_dependency,
    id: int = Path(gt=0),
):
    """
    Endpoint to delete an existing category entry from the database.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param id: (int) ID of the category entry.
    """
    # Fetch the model
    category_model = db.query(Category).filter(Category.id == id).first()
    # If not found raise exception
    if not category_model:
        raise HTTPException(status_code=404, detail="Category not found")
    # Protect the stage category from deletion
    if category_model.id == 1:
        raise HTTPException(status_code=405, detail="Cannot delete the stage category")
    # Transfer the remaining amount to the default stage category
    if category_model.assigned_amount:
        stage_model = db.query(Category).filter(Category.id == 1).first()
        stage_model.assigned_amount += category_model.assigned_amount
        db.add(stage_model)
    # Delete the category
    db.delete(category_model)


@router.post("/{id}/move", status_code=status.HTTP_200_OK)
async def move_amount(db: db_dependency, move_request: MoveRequest, id: int = Path(gt=0)):
    """
    Assign or move amounts from one category to another. The passed amount will be deducted
    from the "id_from" category to the "id_to" category.

    :param db: (db_dependency) SQLAlchemy ORM session.
    :param id: (int) ID of the category to move from.
    :param move_request: (MoveRequest) Data containing the <id_to> category and the amount to
     move.
    """
    # Fetch the models
    from_category_model = db.query(Category).filter(Category.id == id).first()
    to_category_model = db.query(Category).filter(Category.id == move_request.id_to).first()
    if not from_category_model:
        raise HTTPException(status_code=404, detail="<from> category not found")
    if not to_category_model:
        raise HTTPException(status_code=404, detail="<to> category not found")
    # Halt if remaining is negative
    if from_category_model.assigned_amount - move_request.amount < 0:
        raise HTTPException(
            status_code=403, detail="Move request would result in negative amount"
        )
    # Adjust the amounts
    from_category_model.assigned_amount -= move_request.amount
    to_category_model.assigned_amount += move_request.amount
    # Save the changes
    db.add(from_category_model)
    db.add(to_category_model)
