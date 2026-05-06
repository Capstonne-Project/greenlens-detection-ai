# AI Service

AI microservice cho hệ thống báo cáo ô nhiễm môi trường (SU26SE049).

## Quick Start

```cmd
uv sync
uv run uvicorn app.main:app --reload
```

Mở: http://localhost:8000/docs

## Run with Docker

```cmd
cd docker
docker compose up --build
```

## Run tests

```cmd
uv run pytest -v
```
