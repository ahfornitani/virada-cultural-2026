#!/usr/bin/env python3
"""Parse programacao_1778888340.txt into a CSV.

Output: data/programacao_1778888340.csv

Columns: categoria, regiao, local, endereco, data, hora, atracao
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SRC = BASE_DIR / "programacao_1778888340.txt"
OUT_DIR = BASE_DIR / "data"
OUT_CSV = OUT_DIR / "programacao_1778888340.csv"

YEAR = 2026
MONTHS = {"janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
          "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
          "outubro": 10, "novembro": 11, "dezembro": 12}

DATE_RE = re.compile(r"^(\d{1,2})\s+de\s+([a-zç]+)$", re.IGNORECASE)
TIME_RE = re.compile(r"^(\d{1,2})h(\d{2})\s*-\s*(.+)$")
ADDR_RE = re.compile(r"^Endereço:\s*(.+)$", re.IGNORECASE)
DJ_RE = re.compile(r"^DJs?\s+de\s+Intervalo:\s*(.+)$", re.IGNORECASE)

# Top-level section headers (categorias)
CATEGORIAS = {"Palcos e Pistas", "Equipamentos Culturais"}


def parse(text: str) -> list[dict]:
    lines = [ln.strip() for ln in text.splitlines()]
    rows: list[dict] = []

    categoria = ""
    regiao = ""
    local = ""
    endereco = ""
    current_date = ""
    djs_intervalo = ""

    for raw in lines:
        if not raw:
            continue
        if raw.startswith("*") and raw.endswith("*"):
            continue

        # Top-level category
        if raw in CATEGORIAS:
            categoria = raw
            regiao = ""
            local = ""
            endereco = ""
            current_date = ""
            djs_intervalo = ""
            continue

        # Endereço
        m = ADDR_RE.match(raw)
        if m:
            endereco = m.group(1).strip()
            continue

        # DJs de intervalo (apply to subsequent times in this venue)
        m = DJ_RE.match(raw)
        if m:
            djs_intervalo = m.group(1).strip()
            continue

        # Date header
        m = DATE_RE.match(raw)
        if m:
            day = int(m.group(1))
            month = MONTHS.get(m.group(2).lower(), 0)
            current_date = f"{day:02d}/{month:02d}/{YEAR}" if month else raw
            continue

        # Time line
        m = TIME_RE.match(raw)
        if m:
            hh, mm, atracao = m.group(1), m.group(2), m.group(3).strip()
            rows.append({
                "categoria": categoria,
                "regiao": regiao,
                "local": local,
                "endereco": endereco,
                "data": current_date,
                "hora": f"{int(hh):02d}:{mm}",
                "atracao": atracao,
                "djs_intervalo": djs_intervalo,
            })
            continue

        # Otherwise it's a venue header like "Centro – Palco Anhangabaú"
        # Reset venue-scoped state
        if "–" in raw or "-" in raw:
            parts = re.split(r"\s+[–-]\s+", raw, maxsplit=1)
            if len(parts) == 2:
                regiao, local = parts[0].strip(), parts[1].strip()
            else:
                regiao, local = "", raw
        else:
            regiao, local = "", raw
        endereco = ""
        current_date = ""
        djs_intervalo = ""

    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    text = SRC.read_text(encoding="utf-8")
    rows = parse(text)
    fields = ["categoria", "regiao", "local", "endereco", "data", "hora", "atracao", "djs_intervalo"]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT_CSV}")


if __name__ == "__main__":
    main()