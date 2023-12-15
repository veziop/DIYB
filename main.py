"""
filename: main.py
author: Valentin Piombo
email: valenp97@gmail.com
description: Project's root module.
"""
import uvicorn
from fastapi import FastAPI

from api import models
from api.database import engine
from api.routers.balance import router as balance_router
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

models.Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port="8080")
