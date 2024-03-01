# pull official base image
FROM python:3.11.8-slim-bookworm

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

#install uv
ENV VIRTUAL_ENV=/usr/local
RUN apt update && apt install -y curl
ADD --chmod=755 https://astral.sh/uv/install.sh /install.sh
RUN /install.sh && rm /install.sh

# install dependencies
COPY ./requirements.txt .
COPY ./requirements-dev.txt .
RUN /root/.cargo/bin/uv pip install --no-cache -r requirements.txt -r requirements-dev.txt

# copy project
COPY . .
