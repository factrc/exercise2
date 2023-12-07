FROM ubuntu
WORKDIR /app
RUN apt-get update
RUN apt-get install -y python2 python-pip
COPY ./requirements.txt requirements.txt
RUN python2 -m pip install -r requirements.txt
