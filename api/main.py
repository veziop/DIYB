"""
filename: main.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Project's root module.
"""
from fastapi import FastAPI

from database import engine
import models
from routers.transaction_router import router as transaction_router
from routers.balance_router import router as balance_router

app = FastAPI()
app.include_router(transaction_router)
app.include_router(balance_router)

models.Base.metadata.create_all(bind=engine)
