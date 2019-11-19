FROM python:3.7
ENV PYTHONUNBUFFERED 1
RUN mkdir /app
RUN mkdir /app/static
RUN mkdir /app/logs
COPY ./src/ /app/
WORKDIR /app
RUN pip install -r requirements.txt
