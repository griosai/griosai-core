FROM python:3.12-slim

LABEL org.opencontainers.image.title="GriosAI"
LABEL org.opencontainers.image.description="Local-first AI brain and dashboard runner"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOME=/tmp
ENV GRIOSAI_VAULT_DIR=/data/vault
ENV GRIOSAI_HOST=0.0.0.0
ENV GRIOSAI_PORT=8765

WORKDIR /app

RUN groupadd --system --gid 10001 griosai \
    && useradd --system --uid 10001 --gid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin griosai

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir . \
    && mkdir -p /data/vault \
    && chown -R 10001:10001 /data/vault

USER 10001:10001

EXPOSE 8765
VOLUME ["/data/vault"]

ENTRYPOINT ["griosai"]
CMD ["serve", "--vault", "/data/vault", "--host", "0.0.0.0", "--port", "8765"]
