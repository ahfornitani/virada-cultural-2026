#!/usr/bin/env python3
"""Compara horários do events.json com o que o site oficial expõe na página de detalhes."""

from __future__ import annotations

import json
import random
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

# Reaproveita os helpers do scraper
from scrape_virada_v3 import decode_rsc_payload, extract_parties

BASE_DIR = Path(__file__).resolve().parent
EVENTS_JSON = BASE_DIR / "data" / "events.json"
SOURCE = "https://viradasp.prefeitura.sp.gov.br"
UA = "Mozilla/5.0 (compatible; ViradaVerifier/1.1)"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8")


def to_instant(iso: str | None):
    if not iso:
        return None
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def official_times_for(html: str, slug: str) -> tuple[str | None, str | None]:
    try:
        payload = decode_rsc_payload(html)
        parties = extract_parties(payload)
    except Exception:
        return None, None

    for entry in parties:
        fields = entry.get("fields") if isinstance(entry, dict) else None
        if isinstance(fields, dict) and str(fields.get("slug", "")) == slug:
            return str(fields.get("startDate", "")) or None, str(fields.get("endDate", "")) or None
    return None, None


def main() -> None:
    sample_size = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    events = json.loads(EVENTS_JSON.read_text(encoding="utf-8"))
    sample = random.sample(events, min(sample_size, len(events)))

    mismatches = []
    not_found = []
    print(f"Verificando {len(sample)} eventos...\n")

    for i, ev in enumerate(sample, 1):
        slug = ev["slug"]
        url = f"{SOURCE}/evento/{slug}/detalhes"
        try:
            html = fetch(url)
        except Exception as e:
            print(f"[{i}] ERRO HTTP {slug}: {e}")
            continue

        official_start, official_end = official_times_for(html, slug)
        local_start = ev.get("inicio_iso_original")
        local_end = ev.get("fim_iso_original")

        if not official_start:
            print(f"[{i:>3}] N/A  {slug} (slug não encontrado no payload)")
            not_found.append(slug)
            time.sleep(0.3)
            continue

        same = (
            to_instant(official_start) == to_instant(local_start)
            and to_instant(official_end) == to_instant(local_end)
        )
        status = "OK" if same else "DIFERENTE"
        if not same:
            mismatches.append({
                "slug": slug,
                "nome": ev["nome"],
                "site_oficial": {"start": official_start, "end": official_end},
                "meu_json":     {"start": local_start, "end": local_end},
                "exibido_no_site_estatico": f'{ev["data_inicio"]} {ev["hora_inicio"]}–{ev["hora_fim"]}',
            })
        print(f"[{i:>3}] {status}  {slug}")
        time.sleep(0.3)

    print("\n=== RESUMO ===")
    print(f"Conferidos: {len(sample)}  |  Divergentes: {len(mismatches)}  |  Não encontrados: {len(not_found)}")
    if mismatches:
        out = BASE_DIR / "verify_mismatches.json"
        out.write_text(json.dumps(mismatches, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Detalhes em {out}")


if __name__ == "__main__":
    main()