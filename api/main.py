from fastapi import FastAPI

from database import engine
import models
from routers.transaction_router import router as transaction_router

app = FastAPI()
app.include_router(transaction_router)

models.Base.metadata.create_all(bind=engine)
