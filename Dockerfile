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

# ---- System deps + hivemind + PGDG keyring prereqs ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    ca-certificates \
    gettext \
    unzip \
    lsb-release \
    gnupg \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libfontconfig1 \
    libffi8 \
  # Install hivemind (static binary)
  && HIVEMIND_VERSION="1.1.0" \
  && ARCH="$(dpkg --print-architecture)" \
  && case "$ARCH" in \
       amd64)  HIVEMIND_ARCH="amd64" ;; \
       arm64)  HIVEMIND_ARCH="arm64" ;; \
       *) echo "Unsupported arch: $ARCH" >&2; exit 1 ;; \
     esac \
  && curl -fsSL "https://github.com/DarthSim/hivemind/releases/download/v${HIVEMIND_VERSION}/hivemind-v${HIVEMIND_VERSION}-linux-${HIVEMIND_ARCH}.gz" \
     | gunzip > /usr/local/bin/hivemind \
  && chmod +x /usr/local/bin/hivemind \
  && hivemind --version \
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

WORKDIR /app

# activate virtual env
ARG VIRTUAL_ENV=/app/.venv
ENV PATH=/app/.venv/bin:$PATH

# install dependencies (layer cached as long as pyproject.toml/uv.lock unchanged)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# pre-download Tailwind CSS CLI to avoid runtime download (~120MB) on startup
# IMPORTANT: keep TAILWIND_VERSION aligned with django-tailwind-cli expected version
# (the release skill verifies this on every release)
ARG TAILWIND_VERSION=2.8.3
RUN mkdir -p /app/.django_tailwind_cli \
  && ARCH="$(dpkg --print-architecture)" \
  && case "$ARCH" in \
       amd64)  TW_ARCH="x64" ;; \
       arm64)  TW_ARCH="arm64" ;; \
       *) echo "Unsupported arch: $ARCH" >&2; exit 1 ;; \
     esac \
  && curl -fsSL "https://github.com/dobicinaitis/tailwind-cli-extra/releases/download/v${TAILWIND_VERSION}/tailwindcss-extra-linux-${TW_ARCH}" \
     -o "/app/.django_tailwind_cli/tailwindcss-extra-linux-${TW_ARCH}-${TAILWIND_VERSION}" \
  && chmod +x "/app/.django_tailwind_cli/tailwindcss-extra-linux-${TW_ARCH}-${TAILWIND_VERSION}"

# copy project
COPY . /app

# create logs directory
RUN mkdir -p /app/logs

# expose port for granian
EXPOSE 80

# run entrypoint (che poi fa exec hivemind)
CMD ["sh", "./entrypoint.sh"]
