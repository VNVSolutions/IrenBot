FROM python:3.8

ENV PYTHONUNBUFFERED 1

RUN mkdir /IrenBot

WORKDIR /IrenBot

COPY web/requirements.txt /IrenBot/

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /IrenBot/

CMD ["gunicorn", "--workers=3", "--bind=0.0.0.0:8000", "IrenBot.wsgi:application"]
