#!/usr/bin/env python3
"""Scrape the official Virada Cultural programming page and emit CSV + JSON.

Source: https://prefeitura.sp.gov.br/web/cultura/w/programa%C3%A7%C3%A3o-completa-da-virada-cultural

Improvements over v1:
- Pulls live HTML (no manual paste).
- Derives ISO datetimes (handles overnight roll to next day when hour < previous hour).
- Computes hora_fim per venue (next attraction's start time, or +60min for last).
- Splits 'Centro / ZN / ZL / ZO / ZS' into a normalized regiao_codigo.
- Emits stable slug per event.

Outputs:
  data/programacao_v2.csv
  data/programacao_v2.json
  site_v4/data/programacao_v2.csv
  site_v4/data/programacao_v2.json
  site_v4/data/metadata.json
"""

from __future__ import annotations

import csv
import html
import json
import re
import shutil
import unicodedata
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

URL = "https://prefeitura.sp.gov.br/web/cultura/w/programa%C3%A7%C3%A3o-completa-da-virada-cultural"
BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
SITE_DATA_DIR = BASE / "site_v4" / "data"

YEAR = 2026
MONTHS = {"janeiro":1,"fevereiro":2,"março":3,"marco":3,"abril":4,"maio":5,
          "junho":6,"julho":7,"agosto":8,"setembro":9,"outubro":10,
          "novembro":11,"dezembro":12}

DATE_RE = re.compile(r"^(\d{1,2})\s+de\s+([a-zç]+)$", re.IGNORECASE)
TIME_RE = re.compile(r"^(\d{1,2})h(\d{2})\s*[-–]\s*(.+)$")
ADDR_RE = re.compile(r"^Endereço:\s*(.+)$", re.IGNORECASE)
DJ_RE   = re.compile(r"^DJs?\s+de\s+Intervalo:\s*(.+)$", re.IGNORECASE)

CATEGORIAS = {"Palcos e Pistas", "Equipamentos Culturais"}

REGIAO_MAP = {
    "Centro": "Centro",
    "Palcos ZL": "Zona Leste",
    "Palcos ZN": "Zona Norte",
    "Palcos ZO": "Zona Oeste",
    "Palcos ZS": "Zona Sul",
    "Bibliotecas": "Bibliotecas",
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; ViradaCSV/2.0)",
        "Accept": "text/html",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", errors="replace")


def html_to_text(raw: str) -> str:
    # Drop scripts/styles
    raw = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", raw, flags=re.S | re.I)
    # Convert breaks and block tags to newlines
    raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
    raw = re.sub(r"</(p|div|li|h[1-6]|tr|section|article)>", "\n", raw, flags=re.I)
    # Strip remaining tags
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = html.unescape(raw)
    # Normalize whitespace
    raw = raw.replace("\xa0", " ")
    return raw


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s


def parse(text: str) -> list[dict]:
    lines = [ln.strip() for ln in text.splitlines()]
    rows: list[dict] = []

    categoria = ""
    regiao_raw = ""
    regiao = ""
    local = ""
    endereco = ""
    current_date = ""
    djs_intervalo = ""
    seen_tracker: dict[tuple, list[dict]] = {}

    for raw in lines:
        if not raw or raw.startswith("*"):
            continue

        if raw in CATEGORIAS:
            categoria = raw
            regiao_raw = regiao = local = endereco = current_date = djs_intervalo = ""
            continue

        if (m := ADDR_RE.match(raw)):
            endereco = m.group(1).strip()
            continue

        if (m := DJ_RE.match(raw)):
            djs_intervalo = m.group(1).strip()
            continue

        if (m := DATE_RE.match(raw)):
            d = int(m.group(1)); mo = MONTHS.get(m.group(2).lower(), 0)
            current_date = f"{YEAR:04d}-{mo:02d}-{d:02d}" if mo else ""
            continue

        if (m := TIME_RE.match(raw)):
            hh, mm, atracao = int(m.group(1)), m.group(2), m.group(3).strip()
            row = {
                "categoria": categoria,
                "regiao_codigo": regiao_raw,
                "regiao": regiao,
                "local": local,
                "endereco": endereco,
                "data": current_date,
                "hora_inicio": f"{hh:02d}:{mm}",
                "atracao": atracao,
                "djs_intervalo": djs_intervalo,
            }
            rows.append(row)
            seen_tracker.setdefault((local, current_date), []).append(row)
            continue

        # Venue header line, e.g. "Centro – Palco Anhangabaú"
        parts = re.split(r"\s+[–-]\s+", raw, maxsplit=1)
        if len(parts) == 2:
            regiao_raw, local = parts[0].strip(), parts[1].strip()
        else:
            regiao_raw, local = "", raw
        regiao = REGIAO_MAP.get(regiao_raw, regiao_raw)
        endereco = ""
        current_date = ""
        djs_intervalo = ""

    # Compute ISO datetimes with overnight rollover, plus hora_fim
    enrich(rows)
    return rows


def enrich(rows: list[dict]) -> None:
    # Group by venue, ordered by appearance, to handle overnight rollover
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r["local"], []).append(r)

    for venue, items in groups.items():
        prev_dt: datetime | None = None
        for r in items:
            try:
                y, mo, d = map(int, r["data"].split("-"))
                hh, mm = map(int, r["hora_inicio"].split(":"))
            except Exception:
                r["inicio_iso"] = ""
                continue
            dt = datetime(y, mo, d, hh, mm)
            # If earlier than prev start within same venue, assume next-day rollover
            if prev_dt and dt < prev_dt:
                dt += timedelta(days=1)
            r["inicio_iso"] = dt.isoformat()
            r["_dt"] = dt
            prev_dt = dt

        # hora_fim = next start, last gets +60min
        for i, r in enumerate(items):
            if "_dt" not in r:
                r["fim_iso"] = ""; r["hora_fim"] = ""; continue
            end = items[i+1]["_dt"] if i+1 < len(items) and "_dt" in items[i+1] else r["_dt"] + timedelta(minutes=60)
            r["fim_iso"] = end.isoformat()
            r["hora_fim"] = end.strftime("%H:%M")

    for r in rows:
        r.pop("_dt", None)
        r["slug"] = slugify(f"{r['local']}-{r['data']}-{r['hora_inicio']}-{r['atracao']}")


FIELDS = ["slug","categoria","regiao_codigo","regiao","local","endereco",
          "data","hora_inicio","hora_fim","atracao","djs_intervalo",
          "inicio_iso","fim_iso"]


def write_outputs(rows: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = DATA_DIR / "programacao_v2.csv"
    json_path = DATA_DIR / "programacao_v2.json"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    metadata = {
        "source_url": URL,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "event_count": len(rows),
        "venues": sorted({r["local"] for r in rows if r["local"]}),
        "regions": sorted({r["regiao"] for r in rows if r["regiao"]}),
        "dates": sorted({r["data"] for r in rows if r["data"]}),
    }
    (DATA_DIR / "metadata_v2.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    shutil.copy2(csv_path, SITE_DATA_DIR / csv_path.name)
    shutil.copy2(json_path, SITE_DATA_DIR / json_path.name)
    shutil.copy2(DATA_DIR / "metadata_v2.json", SITE_DATA_DIR / "metadata.json")


def main() -> None:
    print(f"Fetching {URL}")
    raw = fetch(URL)
    print(f"HTML: {len(raw):,} chars")
    text = html_to_text(raw)
    rows = parse(text)
    print(f"Parsed {len(rows)} events across {len({r['local'] for r in rows})} venues")
    write_outputs(rows)
    print("Done.")


if __name__ == "__main__":
    main()