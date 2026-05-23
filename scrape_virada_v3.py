#!/usr/bin/env python3
"""V3 scraper for Virada Cultural 2026.

Outputs:
- data/virada_cultural_2026_v3.csv
- data/events.json
- data/metadata.json
- site/data/virada_cultural_2026_v3.csv
- site/data/events.json
- site/data/metadata.json
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SOURCE_URL = "https://viradasp.prefeitura.sp.gov.br/"
EXPECTED_EVENT_COUNT = 1462
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SITE_DATA_DIR = BASE_DIR / "site" / "data"

CSV_FIELDS = [
    "nome",
    "data_inicio",
    "hora_inicio",
    "data_fim",
    "hora_fim",
    "bairro",
    "local",
    "tipo_local",
    "categoria",
    "endereco",
    "latitude",
    "longitude",
    "instagram",
    "playlist",
    "url_oficial",
    "foto",
    "descricao",
    "inicio_iso_utc",
    "fim_iso_utc",
    "inicio_iso_original",
    "fim_iso_original",
]


def fetch_text(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "Mozilla/5.0 (compatible; ViradaCulturalCSV/3.0)",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset)


def decode_rsc_payload(html: str) -> str:
    pushes = re.findall(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', html)
    if not pushes:
        raise RuntimeError("No Next.js RSC payload found in the page.")

    decoded = []
    for push in pushes:
        decoded.append(json.loads(f'"{push}"'))
    return "".join(decoded)


def extract_json_value(text: str, start: int) -> str:
    if text[start] not in "[{":
        raise ValueError(f"Expected JSON array/object at offset {start}, got {text[start]!r}")

    expected_closers: list[str] = []
    in_string = False
    escaped = False

    for i in range(start, len(text)):
        char = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "[":
            expected_closers.append("]")
        elif char == "{":
            expected_closers.append("}")
        elif char in "]}":
            if not expected_closers or char != expected_closers[-1]:
                raise ValueError(f"Unexpected JSON closer {char!r} at offset {i}")
            expected_closers.pop()
            if not expected_closers:
                return text[start : i + 1]

    raise ValueError("Could not find the end of the JSON value.")


def extract_parties(combined_payload: str) -> list[dict[str, Any]]:
    key = '"parties":'
    idx = combined_payload.find(key)
    if idx == -1:
        raise RuntimeError("Could not find the parties array in the RSC payload.")

    start = idx + len(key)
    while start < len(combined_payload) and combined_payload[start].isspace():
        start += 1

    parties = json.loads(extract_json_value(combined_payload, start))
    if not isinstance(parties, list):
        raise RuntimeError("The parties payload is not a JSON array.")
    return parties


def rich_text_to_plain(node: Any) -> str:
    if not isinstance(node, dict):
        return ""
    if node.get("nodeType") == "text":
        return str(node.get("value", ""))

    child_texts = [rich_text_to_plain(child).strip() for child in node.get("content", [])]
    child_texts = [text for text in child_texts if text]
    if node.get("nodeType") == "document":
        return "\n\n".join(child_texts)
    if node.get("nodeType") == "paragraph":
        return " ".join(child_texts)
    return " ".join(child_texts)


def normalize_event_year(dt: datetime) -> datetime:
    if dt.year == 2025:
        return dt.replace(year=2026)
    return dt


def display_datetime_from_source(iso_value: str) -> tuple[str, str, str]:
    if not iso_value:
        return "", "", ""

    source_dt = datetime.fromisoformat(iso_value)
    precise_utc = normalize_event_year(source_dt.astimezone(timezone.utc).replace(microsecond=0))
    displayed_dt = precise_utc.replace(minute=0, second=0, microsecond=0)
    iso_utc = precise_utc.isoformat().replace("+00:00", "Z")
    return displayed_dt.strftime("%d/%m/%Y"), displayed_dt.strftime("%H:%M"), iso_utc


def resolve_rsc_ref(value: Any, parties: list[dict[str, Any]]) -> Any:
    if not isinstance(value, str) or not value.startswith("$"):
        return value

    tokens = value.split(":")
    if "parties" not in tokens:
        return value

    current: Any = parties
    for token in tokens[tokens.index("parties") + 1 :]:
        if isinstance(current, list) and token.isdigit():
            index = int(token)
            if index >= len(current):
                return value
            current = current[index]
        elif isinstance(current, dict) and token in current:
            current = current[token]
        else:
            return value
    return current


def first_photo_url(fields: dict[str, Any], parties: list[dict[str, Any]]) -> str:
    photos = fields.get("photos") or []
    if not isinstance(photos, list) or not photos:
        return ""

    first_photo = resolve_rsc_ref(photos[0], parties)
    if not isinstance(first_photo, dict):
        return ""

    file_info = first_photo.get("fields", {}).get("file", {})
    if not isinstance(file_info, dict):
        return ""

    url = str(file_info.get("url", ""))
    return "https:" + url if url.startswith("//") else url


def local_to_string(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def event_to_row(entry: dict[str, Any], parties: list[dict[str, Any]]) -> dict[str, Any]:
    fields = entry.get("fields", {})
    if not isinstance(fields, dict):
        raise RuntimeError("Event entry without fields dict.")

    slug = str(fields.get("slug", "")).strip()
    if not slug:
        raise RuntimeError("Event entry without slug.")

    start_original = str(fields.get("startDate", ""))
    end_original = str(fields.get("endDate", ""))
    start_date, start_time, start_utc = display_datetime_from_source(start_original)
    end_date, end_time, end_utc = display_datetime_from_source(end_original)

    location = fields.get("initialLocation") or {}
    if not isinstance(location, dict):
        location = {}

    return {
        "nome": str(fields.get("name", "")),
        "data_inicio": start_date,
        "hora_inicio": start_time,
        "data_fim": end_date,
        "hora_fim": end_time,
        "bairro": str(fields.get("neighborhood", "")),
        "local": str(fields.get("placeName", "")),
        "tipo_local": local_to_string(fields.get("local")),
        "categoria": str(fields.get("category", "")),
        "endereco": str(fields.get("address", "")),
        "latitude": location.get("lat", ""),
        "longitude": location.get("lon", ""),
        "instagram": str(fields.get("instagramLink", "")),
        "playlist": str(fields.get("playlistLink", "")),
        "url": f"{SOURCE_URL.rstrip('/')}/evento/{slug}/detalhes",
        "url_oficial": f"{SOURCE_URL.rstrip('/')}/evento/{slug}/detalhes",
        "foto": first_photo_url(fields, parties),
        "descricao": rich_text_to_plain(fields.get("description", {})),
        "inicio_iso_utc": start_utc,
        "fim_iso_utc": end_utc,
        "inicio_iso_original": start_original,
        "fim_iso_original": end_original,
        "slug": slug,
    }


def validate_rows(rows: list[dict[str, Any]], raw_count: int) -> None:
    if raw_count != EXPECTED_EVENT_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_EVENT_COUNT} raw events, found {raw_count}.")
    if len(rows) != EXPECTED_EVENT_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_EVENT_COUNT} unique events, found {len(rows)}.")

    by_slug = {row["slug"]: row for row in rows}
    expected_samples = {
        "nos-tempos-da-soweto-871e": ("24/05/2026", "22:00"),
        "duo-entre-cordas": ("24/05/2026", "12:00"),
    }
    for slug, (expected_date, expected_time) in expected_samples.items():
        row = by_slug.get(slug)
        if row is None:
            raise RuntimeError(f"Validation sample missing: {slug}")
        actual = (row["data_inicio"], row["hora_inicio"])
        expected = (expected_date, expected_time)
        if actual != expected:
            raise RuntimeError(f"Unexpected time for {slug}: {actual}, expected {expected}.")
        if not row.get("url_oficial", "").startswith("https://viradasp.prefeitura.sp.gov.br/evento/"):
            raise RuntimeError(f"Official URL missing for {slug}.")


def build_metadata(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_category = Counter(str(row["categoria"]) for row in rows)
    by_date = Counter(str(row["data_inicio"]) for row in rows)
    by_neighborhood = Counter(str(row["bairro"]) for row in rows)
    return {
        "source_url": SOURCE_URL,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "event_count": len(rows),
        "expected_event_count": EXPECTED_EVENT_COUNT,
        "time_normalization": "Raw ISO timestamps are converted to UTC clock time and displayed as full hours to match the official detail pages (for example, 00h => 00:00). Three 2025 source dates are normalized to 2026 for the Virada Cultural 2026 agenda.",
        "counts": {
            "by_category": dict(sorted(by_category.items())),
            "by_date": dict(sorted(by_date.items())),
            "by_neighborhood": dict(sorted(by_neighborhood.items())),
        },
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Baixando página principal...")
    html = fetch_text(SOURCE_URL)
    print(f"HTML baixado: {len(html):,} chars")

    print("Decodificando payload RSC...")
    combined_payload = decode_rsc_payload(html)
    parties = extract_parties(combined_payload)
    print(f"Eventos brutos no payload: {len(parties)}")

    rows_by_slug: dict[str, dict[str, Any]] = {}
    for entry in parties:
        row = event_to_row(entry, parties)
        rows_by_slug[row["slug"]] = row

    rows = sorted(rows_by_slug.values(), key=lambda row: (row["inicio_iso_utc"], row["nome"], row["slug"]))
    validate_rows(rows, raw_count=len(parties))

    metadata = build_metadata(rows)
    csv_path = DATA_DIR / "virada_cultural_2026_v3.csv"
    json_path = DATA_DIR / "events.json"
    metadata_path = DATA_DIR / "metadata.json"

    write_csv(csv_path, rows)
    write_json(json_path, rows)
    write_json(metadata_path, metadata)

    for folder in (DATA_DIR, SITE_DATA_DIR):
        (folder / "virada_cultural_2026_v2.csv").unlink(missing_ok=True)

    shutil.copy2(csv_path, SITE_DATA_DIR / csv_path.name)
    shutil.copy2(json_path, SITE_DATA_DIR / json_path.name)
    shutil.copy2(metadata_path, SITE_DATA_DIR / metadata_path.name)

    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    print(f"Site data: {SITE_DATA_DIR}")
    print(f"Eventos únicos validados: {len(rows)}")


if __name__ == "__main__":
    main()
