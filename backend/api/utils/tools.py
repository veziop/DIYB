"""
filename: tools.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for the definitions of reusable utility functions.
"""

from datetime import date, datetime

from fastapi import HTTPException
from pydantic import BaseModel
from pytz import timezone
from sqlalchemy.orm import Session

from api.config import settings


def validate_entries_in_db(db: Session, entries: list) -> dict:
    """
    Auxiliary function to validate the existence of data in the database. This is useful for
    validating the data before making operations. After successful validation, it can also
    return the data in the form of SQLAlchemy models.

    :param db: (Session) SQLAlchemy ORM session.
    :param entries: (List[Union[Entry, None]]) collection of data to check; optional flag
     <return_model> can be included if the entry data is requested to be returned.
    :return: (dict) A dictionary with model names as keys and corresponding result as values.
    """
    results = {}
    for entry in entries:
        if entry is None:
            continue  # Skip processing if entry is None
        query = db.query(entry["model"]).filter(entry["model"].id == entry["id_value"])
        if entry.get("return_model"):
            model_result = query.first()
            if not model_result:
                raise HTTPException(
                    status_code=404, detail=f"{entry['model'].__name__} not found"
                )
            results[entry["model"].__name__] = model_result
        else:
            count_result = query.count()
            if not count_result:
                raise HTTPException(
                    status_code=404, detail=f"{entry['model'].__name__} not found"
                )
    return results


def today_factory() -> date:
    """
    Function that computes today's date accurate to the timezone set in the config.py

    :returns: (date) Today's date
    """
    tz = timezone(settings.timezone)
    return datetime.now(tz).date()
