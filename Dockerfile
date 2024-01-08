FROM python:3.10-alpine

WORKDIR /app

COPY ./requrements.txt /app/requrements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./main.py /app/main.py

COPY ./api /app/api

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
