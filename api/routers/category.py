"""
filename: category.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definitions of routes related to the Category model.
"""
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from starlette import status

from api.database import db_dependency, sql_session
from api.models.category import Category

router = APIRouter(prefix="/category", tags=["category"])


class CategoryRequest(BaseModel):
    title: str = Field(min_length=2, max_length=40)
    description: str = Field(max_length=100)


class CategoryResponse(CategoryRequest):
    pass


class CategoryPartialRequest(BaseModel):
    title: str = None
    description: str = None


def create_staging_category() -> None:
    """Create the main category from which to assign to all others."""
    with sql_session() as db:
        categories = db.query(Category).all()
        if categories:
            return
        stage_model = Category(
            title="stage",
            description="stage category to assign to all other categories",
        )
        db.add(stage_model)


def update_category_amount(db: db_dependency, category_id: int, amount: float):
    """Update the assigned amount of a category entry with the transaction amount."""
    # Fetch the category entry
    category_model = db.query(Category).filter(Category.id == category_id).first()
    # Update the assigned amount
    category_model.assigned_amount += amount
    # Apply the changes to the database
    db.add(category_model)


@router.get("/all", status_code=status.HTTP_200_OK)
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
    :param category_request: (CategoryRequest) data to be used to update the transaction
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
    # Manual validation as pydantic partial model had none
    for attribute, value in update_data.items():
        match attribute:
            case "title":
                if len(value) > 40:
                    raise ValueError("Attr <title> must be less than 30 character in length.")
                if len(value) < 2:
                    raise ValueError("Attr <title> must be at least 2 character in length.")
            case "description":
                if len(value) > 100:
                    raise ValueError("Attr <description> cannot be over 100 characters.")
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
