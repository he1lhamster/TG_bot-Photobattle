FROM python:3.10.6

WORKDIR /

COPY sender.py .
COPY poller.py .
COPY dataclassess.py .
COPY manager.py .

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

