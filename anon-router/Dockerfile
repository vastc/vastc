FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt requirements.txt
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN pip install -r requirements.txt
COPY *.py .
CMD [ "python3", "anon-router.py" ]
