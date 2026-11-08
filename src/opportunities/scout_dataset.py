"""Read the complete public open dataset; never access LinkedIn or canonical state."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from http.cookiejar import CookieJar, DefaultCookiePolicy
from pathlib import Path
from typing import Literal, cast

import httpx
from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, field_serializer, field_validator, model_validator

from opportunities.manual_jobs import unique_json_object
from opportunities.utils.time import utc_now
from opportunities.utils.url import validate_linkedin_job_url

PUBLIC_ORIGIN = "https://techopportunities.eu"
MAX_PUBLIC_BYTES = 64 * 1024 * 1024
MAX_API_PAGES = 100  # Research budget, deliberately below the API's maximum.


class PublicDatasetError(ValueError):
    """Public retrieval failures with bounded recovery categories for local tooling."""

    def __init__(
        self,
        code: Literal["dataset_changed", "export_required", "http_429"],
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code


def validate_contract(payload: object, definition: str) -> None:
    """Validate against the checked-in public contract, without duplicating its fields."""
    package = Path(__file__).resolve().parent
    schema_path = package / "resources/schemas/opportunities-v1.schema.json"
    if not schema_path.is_file():
        schema_path = package.parents[1] / "schemas/opportunities-v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    contract = {"$ref": f"#/$defs/{definition}", "$defs": schema["$defs"]}
    if not Draft202012Validator(contract).is_valid(payload):
        raise ValueError("public dataset does not match the repository contract")


class PublicDataset(BaseModel):
    """Local record of a complete, consistency-checked public read, not historical state."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    status: dict[str, object]
    ids: frozenset[str]
    retrieved_at: datetime
    method: Literal["api", "export"]

    @field_serializer("ids")
    def serialize_ids(self, value: frozenset[str]) -> list[str]:
        return sorted(value)

    @field_validator("retrieved_at")
    @classmethod
    def aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("retrieval time must have a timezone")
        return value

    @model_validator(mode="after")
    def complete(self) -> PublicDataset:
        validate_contract(self.status, "statusSuccess")
        if len(self.ids) != self.status["opportunities"]:
            raise ValueError("public dataset count mismatch")
        for job_id in self.ids:
            validate_linkedin_job_url(f"https://www.linkedin.com/jobs/view/{job_id}", job_id)
        return self


def _read(client: httpx.Client, path: str, *, limit: int) -> bytes:
    with client.stream(
        "GET",
        PUBLIC_ORIGIN + path,
        follow_redirects=False,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Cache-Control": "no-cache",
        },
    ) as response:
        if response.status_code == 429:
            raise PublicDatasetError("http_429", "public dataset request failed (HTTP 429)")
        if response.status_code != 200:
            raise ValueError(f"public dataset request failed (HTTP {response.status_code})")
        if response.headers.get("content-encoding", "identity").lower() != "identity":
            raise ValueError("compressed public dataset response refused")
        if "application/json" not in response.headers.get("content-type", "").lower():
            raise ValueError("public dataset response is not JSON")
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > limit:
                raise ValueError("public dataset response exceeds research budget")
            chunks.append(chunk)
        return b"".join(chunks)


def _decode(content: bytes) -> object:
    try:
        return cast(
            object, json.loads(content.decode("utf-8"), object_pairs_hook=unique_json_object)
        )
    except (ValueError, RecursionError) as exc:
        raise ValueError("public dataset response is invalid JSON") from exc


def _document(client: httpx.Client, path: str, definition: str) -> dict[str, object]:
    payload = _decode(
        _read(client, path, limit=4096 if definition == "statusSuccess" else 1024 * 1024)
    )
    validate_contract(payload, definition)
    return cast(dict[str, object], payload)


def load_public_dataset(client: httpx.Client, *, use_export: bool = False) -> PublicDataset:
    """Bracket bounded serial reads with status; fail rather than return partial identity sets.

    Call with an unauthenticated client. No retries or fallback requests occur implicitly.
    Fixed-path mode requires the hash-checked export because API pages cannot be pinned.
    """
    if client.auth is not None or any(
        key in client.headers for key in ("authorization", "proxy-authorization", "cookie")
    ):
        raise ValueError("public dataset client must be unauthenticated")
    client.cookies = CookieJar(policy=DefaultCookiePolicy(allowed_domains=[]))
    before = _document(client, "/api/v1/status", "statusSuccess")
    ids: set[str] = set()
    if use_export:
        ids = _export_ids(client, before)
    else:
        if before["release"] is None:
            raise PublicDatasetError(
                "export_required", "fixed-path API cannot pin pages; use the hash-checked export"
            )
        # JSON Schema accepts integral JSON numbers such as 100.0 as integers.
        total = int(cast(int | float, before["opportunities"]))
        pages = (total + 99) // 100
        if pages > MAX_API_PAGES:
            raise PublicDatasetError(
                "export_required", "public dataset exceeds page budget; use the complete export"
            )
        for page in range(1, max(pages, 1) + 1):
            payload = _document(
                client,
                f"/api/v1/opportunities?page={page}&page-size=100&sort=first-seen-desc",
                "apiSuccess",
            )
            expected = {"page": page, "pageSize": 100, "total": total, "totalPages": pages}
            if payload["pagination"] != expected:
                raise ValueError("public pagination changed or is incomplete")
            rows = cast(list[dict[str, object]], payload["data"])
            if len(rows) != min(100, total - (page - 1) * 100):
                raise ValueError("public page is incomplete")
            for row in rows:
                _add_identity(ids, row["linkedinJobId"], row["link"])
        # Status brackets alone can miss a publication followed by rollback. Tie the
        # complete API identity set to exact release bytes rather than trusting counts.
        if ids != _export_ids(client, before):
            raise ValueError("public API and hash-checked export identity sets differ")
    after = _document(client, "/api/v1/status", "statusSuccess")
    if before != after:
        raise PublicDatasetError("dataset_changed", "public dataset changed during retrieval")
    return PublicDataset(
        status=after,
        ids=frozenset(ids),
        retrieved_at=utc_now(),
        method="export" if use_export else "api",
    )


def _export_ids(client: httpx.Client, status: dict[str, object]) -> set[str]:
    content = _read(client, "/open-opportunities.json", limit=MAX_PUBLIC_BYTES)
    if hashlib.sha256(content).hexdigest() != status["dataset_sha256"]:
        raise ValueError("public export hash mismatch")
    payload = _decode(content)
    validate_contract(payload, "jsonDataset")
    ids: set[str] = set()
    for row in cast(list[dict[str, object]], payload):
        _add_identity(ids, row["linkedin_job_id"], row["link"])
    return ids


def _add_identity(ids: set[str], job_id: object, link: object) -> None:
    if not isinstance(job_id, str) or not isinstance(link, str):
        raise ValueError("invalid public identity")
    validate_linkedin_job_url(link, job_id)
    if job_id in ids:
        raise ValueError("duplicate identity across public rows")
    ids.add(job_id)
