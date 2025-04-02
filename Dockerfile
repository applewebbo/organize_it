# pull official base image
FROM python:3.12-slim-bookworm

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONPATH /srv
ENV PYTHONUNBUFFERED 1

#install uv and postgresql client
RUN apt update && \
    apt install --no-install-recommends -y libpq-dev curl unzip gnupg2 lsb-release apt-transport-https ca-certificates
# Add the PGDG apt repo
RUN echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list
# Trust the PGDG gpg key
RUN curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc| gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg
RUN apt update \
    && apt -y install postgresql-16 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip uv
RUN python -m uv venv

# copy project
WORKDIR /app
COPY . /app

# Install Bun
RUN curl -fsSL https://bun.sh/install | bash

# # Install DaisyUI using Bun
RUN ~/.bun/bin/bun install

# activate virtual env
ARG VIRTUAL_ENV=/app/.venv
ENV PATH=/app/.venv/bin:$PATH

# install dependencies
COPY pyproject.toml ./
COPY uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# copy project
WORKDIR /app
COPY . /app

# expose port for gunicorn
EXPOSE 80

# run migrate and gunicorn on port 80
CMD ["sh", "./entrypoint.sh"]
