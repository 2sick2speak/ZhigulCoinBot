FROM ubuntu:16.04

RUN apt-get update -y
RUN apt-get install -y python3-pip git python-dev htop
RUN apt-get install -y python3-psycopg2 libpq-dev
RUN apt-get install -y locales python3-tk
RUN locale-gen "en_US.UTF-8"
ENV LC_ALL en_US.UTF-8   
RUN mkdir /app
COPY . /app
WORKDIR /app

RUN pip3 install -U pip
RUN pip3 install -U -r requirements.txt

WORKDIR /app

CMD ["python3",  "run.py"]