"""
filename: database.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Module for everything database/engine/sessions related.
"""
from contextlib import contextmanager
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, scoped_session, sessionmaker

DATABASE_URL = "sqlite:///./diyb.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=getattr(e, "status_code", 500),
            detail={"message": getattr(e, "detail", str(e))},
        )
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


@contextmanager
def sql_session():
    """
    Custom SQL session in a context manager that conviniently commits and closes.
    """
    db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    try:
        yield db_session
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        raise HTTPException(
            status_code=e.status_code,
            detail={"message": e.detail.message},
        )
    finally:
        db_session.close()
