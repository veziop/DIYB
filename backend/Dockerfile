FROM python:3.11-slim-bookworm

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN  pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./api /code/api

ENV DATABASE_URL="sqlite:////data/database.db"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "80"]
