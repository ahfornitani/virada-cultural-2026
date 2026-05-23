#!/usr/bin/env python3
"""Compara horários do events.json com o que o site oficial expõe na página de detalhes."""

from __future__ import annotations

import json
import random
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from scrape_virada_v3 import decode_rsc_payload, extract_parties

BASE_DIR = Path(__file__).resolve().parent
EVENTS_JSON = BASE_DIR / "data" / "events.json"
SOURCE = "https://viradasp.prefeitura.sp.gov.br"
UA = "Mozilla/5.0 (compatible; ViradaVerifier/1.2)"
MAX_WORKERS = 32


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


from datetime import timezone, timedelta
SP_TZ = timezone(timedelta(hours=-3))

def expected_display(iso: str) -> tuple[str, str]:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(SP_TZ)
    if dt.year == 2025:
        dt = dt.replace(year=2026)
    return dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M")


def check_one(ev: dict) -> dict:
    slug = ev["slug"]
    url = f"{SOURCE}/evento/{slug}/detalhes"
    result = {"slug": slug, "nome": ev["nome"], "status": "OK"}
    try:
        html = fetch(url)
    except Exception as e:
        result["status"] = "ERRO"
        result["error"] = str(e)
        return result

    official_start, official_end = official_times_for(html, slug)
    if not official_start:
        result["status"] = "NAO_ENCONTRADO"
        return result

    # compara instante absoluto
    same_instant = (
        to_instant(official_start) == to_instant(ev.get("inicio_iso_original"))
        and to_instant(official_end) == to_instant(ev.get("fim_iso_original"))
    )
    # compara o que está EXIBIDO no nosso site com o que deveria ser exibido (derivado do oficial)
    exp_date, exp_time = expected_display(official_start)
    exp_date_end, exp_time_end = expected_display(official_end)
    same_display = (
        ev["data_inicio"] == exp_date
        and ev["hora_inicio"] == exp_time
        and ev["data_fim"] == exp_date_end
        and ev["hora_fim"] == exp_time_end
    )

    if not (same_instant and same_display):
        result["status"] = "DIFERENTE"
        result["site_oficial_iso"] = {"start": official_start, "end": official_end}
        result["meu_json_iso"] = {"start": ev.get("inicio_iso_original"), "end": ev.get("fim_iso_original")}
        result["exibido_no_meu_site"] = f'{ev["data_inicio"]} {ev["hora_inicio"]}–{ev["hora_fim"]}'
        result["deveria_exibir"] = f'{exp_date} {exp_time}–{exp_time_end}'
    return result


def main() -> None:
    events = json.loads(EVENTS_JSON.read_text(encoding="utf-8"))
    if len(sys.argv) > 1:
        n = int(sys.argv[1])
        sample = events if n >= len(events) else random.sample(events, n)
    else:
        sample = events

    print(f"Verificando {len(sample)} eventos com {MAX_WORKERS} workers...\n")

    mismatches, errors, not_found = [], [], []
    done = 0
    total = len(sample)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(check_one, ev): ev for ev in sample}
        for fut in as_completed(futures):
            res = fut.result()
            done += 1
            status = res["status"]
            if status == "DIFERENTE":
                mismatches.append(res)
            elif status == "ERRO":
                errors.append(res)
            elif status == "NAO_ENCONTRADO":
                not_found.append(res)
            if done % 50 == 0 or done == total:
                print(f"  {done}/{total}  (div={len(mismatches)} err={len(errors)} n/a={len(not_found)})")

    print("\n=== RESUMO ===")
    print(f"Conferidos: {total}  |  Divergentes: {len(mismatches)}  |  Erros: {len(errors)}  |  Não encontrados: {len(not_found)}")
    if mismatches:
        out = BASE_DIR / "verify_mismatches.json"
        out.write_text(json.dumps(mismatches, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Divergências em {out}")
    if errors:
        out = BASE_DIR / "verify_errors.json"
        out.write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Erros em {out}")


if __name__ == "__main__":
    main()