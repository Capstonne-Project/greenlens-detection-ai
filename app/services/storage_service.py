"""Image fetch (HTTP / S3) and optional stripped upload (BR-AI-007)."""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from urllib.parse import unquote, urlparse

import boto3
import httpx
from botocore.client import BaseClient

from app.config import Settings, get_settings


def _file_uri_to_path(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        msg = f"Not a file URI: {uri!r}"
        raise ValueError(msg)
    decoded = unquote(parsed.path)
    host = parsed.netloc
    if os.name != "nt":
        candidate = decoded or host
        return Path(candidate)
    # Windows typical: file:///D:/caps/a.jpg → path `/D:/caps/a.jpg`
    if decoded.startswith("/") and len(decoded) >= 3 and decoded[2] == ":":
        return Path(decoded[1:])
    if host and decoded:
        merged = "\\\\" + host + decoded.replace("/", "\\")
        return Path(merged)
    return Path(decoded)


def _s3_client(settings: Settings) -> BaseClient:
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
    )


def _s3_get_bytes_sync(url: str, settings: Settings) -> bytes:
    rest = url.removeprefix("s3://")
    bucket, _, key = rest.partition("/")
    if not bucket or not key:
        msg = f"Invalid s3 URL: {url}"
        raise ValueError(msg)
    client = _s3_client(settings)
    obj = client.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()


def _s3_put_bytes_sync(
    bucket: str,
    key: str,
    body: bytes,
    settings: Settings,
    content_type: str = "image/jpeg",
) -> str:
    client = _s3_client(settings)
    client.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)
    return f"s3://{bucket}/{key}"


async def fetch_image_bytes(url: str, settings: Settings | None = None) -> bytes:
    settings = settings or get_settings()
    if url.startswith(("http://", "https://")):
        timeout = httpx.Timeout(60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
    if url.startswith("s3://"):
        return await asyncio.to_thread(_s3_get_bytes_sync, url, settings)
    if url.startswith("file://"):
        path = _file_uri_to_path(url)
        return await asyncio.to_thread(path.read_bytes)
    msg = f"Unsupported image URL scheme: {url[:32]!r}..."
    raise ValueError(msg)


async def upload_stripped_jpeg(data: bytes, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    key = f"stripped/{uuid.uuid4().hex}.jpg"
    if settings.storage_stub_mode:
        return f"s3://{settings.s3_bucket}/{key}"

    return await asyncio.to_thread(
        _s3_put_bytes_sync,
        settings.s3_bucket,
        key,
        data,
        settings,
    )
