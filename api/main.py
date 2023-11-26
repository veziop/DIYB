"""
filename: main.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Project's root module.
"""
from fastapi import FastAPI

import models
from database import engine
from routers.balance_router import router as balance_router
from routers.transaction_router import router as transaction_router

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

models.Base.metadata.create_all(bind=engine)
