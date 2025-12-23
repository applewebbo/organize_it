# pull official base image
FROM python:3.14-slim-bookworm

# set work directory
WORKDIR /usr/src/app

# set environment variables (key=value format)
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/srv
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=prod

# ---- System deps + mprocs + PGDG keyring prereqs ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    ca-certificates \
    gettext \
    unzip \
    lsb-release \
    gnupg \
  # Install mprocs (static musl)
  && MPROCS_VERSION="0.7.3" \
  && ARCH="$(dpkg --print-architecture)" \
  && case "$ARCH" in \
       amd64)  MPROCS_ARCH="x86_64" ;; \
       arm64)  MPROCS_ARCH="aarch64" ;; \
       *) echo "Unsupported arch: $ARCH" >&2; exit 1 ;; \
     esac \
  && curl -fsSL "https://github.com/pvolok/mprocs/releases/download/v${MPROCS_VERSION}/mprocs-${MPROCS_VERSION}-linux-${MPROCS_ARCH}-musl.tar.gz" \
     | tar -xz -C /usr/local/bin mprocs \
  && chmod +x /usr/local/bin/mprocs \
  && mprocs --version \
  # PGDG repo (PostgreSQL Apt Repository)
  && install -d /usr/share/keyrings \
  && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
     | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg \
  && echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
     > /etc/apt/sources.list.d/pgdg.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends postgresql-16 \
  && rm -rf /var/lib/apt/lists/*

# Install uv using the official script
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
  && mv /root/.local/bin/uv /usr/local/bin/uv

# copy project
WORKDIR /app
COPY . /app

# activate virtual env
ARG VIRTUAL_ENV=/app/.venv
ENV PATH=/app/.venv/bin:$PATH

# install dependencies
COPY pyproject.toml ./
COPY uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# copy project (se vuoi evitare doppia COPY, puoi rimuovere questa se non ti serve)
WORKDIR /app
COPY . /app

# mprocs config (sostituisce supervisord.conf)
COPY mprocs.yaml /app/mprocs.yaml

# create logs directory
RUN mkdir -p /app/logs

# expose port for granian
EXPOSE 80

# run entrypoint (che poi fa exec mprocs)
CMD ["sh", "./entrypoint.sh"]
