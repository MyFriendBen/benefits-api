FROM python:3.10

# use root to install pip libs. Default user is root,
# but we make it explicit here for clarity.
USER root

RUN groupadd benefitsapi && \
  useradd -g benefitsapi benefitsapi

RUN apt-get update -y && \
  apt-get install -y --no-install-recommends postgresql-client make

WORKDIR /code

COPY --chown=benefitsapi:benefitsapi . /code/

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install -r requirements.txt

USER benefitsapi