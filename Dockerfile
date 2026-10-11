FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY migrations ./migrations
COPY db ./db
RUN pip install --no-cache-dir . \
    && useradd --system --uid 10001 --no-create-home habits
USER habits
# Secrets (database URLs, public key, publisher token) arrive as environment variables at runtime only.
CMD ["habits-api"]
