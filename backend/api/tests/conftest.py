"""
filename: conftest.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Configuration of the PyTest suite.
"""

from datetime import date
from decimal import Decimal
from random import randint

from fastapi.testclient import TestClient
from pytest import fixture
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base, get_db
from api.main import app
from api.models import Account, Balance, Category, Transaction

client = TestClient(app)

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Fixture to create the database schema before any tests run
@fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# Fixture to override the `get_db` dependency
@fixture()
def db_session():
    # Create a new database session for a test
    db = TestingSessionLocal()
    try:
        yield db
        db.commit()
    finally:
        db.close()


# Override FastAPI's dependency to use the test database session
@fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
            db_session.commit()
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client


@fixture(autouse=True)
def setup_database(db_session):
    # Empty all tables
    db_session.query(Transaction).delete()
    db_session.query(Category).delete()
    db_session.query(Account).delete()
    db_session.commit()

    # Create default accounts
    default_accounts = [
        Account(name="test checking", description="Default checking account", is_checking=True),
        Account(name="test savings", description="Default savings account", is_checking=False),
    ]
    db_session.add_all(default_accounts)
    db_session.commit()

    # Create default categories
    default_categories = [
        Category(title="stage", description="test stage", is_stage=True, assigned_amount=0),
        Category(title="restaurant", description="test food", assigned_amount=100),
        Category(title="transportation", description="test transportation", assigned_amount=50),
    ]
    db_session.add_all(default_categories)
    db_session.commit()


@fixture()
def create_transaction(db_session):
    def _create_transaction(**kwargs):
        transaction = Transaction(
            payee=kwargs.get("payee", "test payee"),
            creation_datetime=kwargs.get("creation_datetime", date.today()),
            last_update_datetime=kwargs.get("last_update_datetime", date.today()),
            transaction_date=kwargs.get("transaction_date", date.today()),
            description=kwargs.get("description", "test description"),
            amount=kwargs.get("amount", 100),
            category_id=kwargs.get("category_id", 1),
            account_id=kwargs.get("account_id", 1),
        )
        db_session.add(transaction)
        db_session.commit()
        return transaction

    return _create_transaction


@fixture(params=[1, 3, 10])
def create_multiple_transactions(request, db_session, create_transaction):
    transactions = []
    for i in range(request.param):
        transaction = create_transaction(
            payee=f"test payee {i}",
            creation_datetime=date.today(),
            last_update_datetime=date.today(),
            transaction_date=date.today(),
            description="test description {i}",
            amount=Decimal(f"-{randint(1, 5)}.{randint(1, 100)}"),
            category_id=randint(1, 3),
            account_id=1,
        )
        transactions.append(transaction)
    return transactions
