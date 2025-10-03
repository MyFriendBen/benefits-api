FROM python:3.10

# use root to install pip libs
USER root

WORKDIR /code

COPY . /code/

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install -r requirements.txt

# switch to app user
RUN groupadd benefitsapi && \
  useradd -g benefitsapi benefitsapi && \
  apt-get purge -y --auto-remove build-essential && \
  apt-get -y install make && \
  chown -R benefitsapi:benefitsapi /code

USER benefitsapi