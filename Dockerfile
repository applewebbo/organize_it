# pull official base image
FROM python:3.11.8-slim-bookworm

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV VIRTUAL_ENV=/usr/local
ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONPATH /srv
ENV PYTHONUNBUFFERED 1

#install uv
RUN apt-get update
RUN pip install --upgrade pip uv
RUN python -m uv venv /venv

# install dependencies
COPY ./requirements.txt .
COPY ./requirements-dev.txt .
RUN uv pip install -r requirements.txt -r requirements-dev.txt

# copy entrypoint.sh
COPY ./entrypoint.sh .
RUN sed -i 's/\r$//g' /usr/src/app/entrypoint.sh
RUN chmod +x /usr/src/app/entrypoint.sh

# copy project
COPY . .

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
