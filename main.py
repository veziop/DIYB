"""
filename: main.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Project's root module.
"""

from fastapi import FastAPI

from api import models
from api.database import engine
from api.routers.account import create_checking_account
from api.routers.account import router as account_router
from api.routers.balance import router as balance_router
from api.routers.category import create_stage_category
from api.routers.category import router as category_router
from api.routers.transaction import router as transaction_router

app = FastAPI(
    title="DIYB",
    version="0.1.0",
    summary="Do It Yourself Budget - a personal finance organizer",
    contact={
        "author": "Valentin Piombo",
        "email": "valenp97@gmail.com",
        "url": "https://github.com/veziop/DIYB",
    },
)
app.include_router(transaction_router)
app.include_router(balance_router)
app.include_router(category_router)
app.include_router(account_router)

models.Base.metadata.create_all(bind=engine)

# Populate tables with defaults
create_checking_account()
create_stage_category()
