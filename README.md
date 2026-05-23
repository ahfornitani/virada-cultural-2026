# Virada Cultural 2026

Site estático e pesquisável da programação da Virada Cultural de São Paulo 2026, com filtros, favoritos locais e exportação em CSV, JSON e ICS (calendário).

Acesse: <https://viradacultural2026.netlify.app>.

## Como funciona

- `scrape_virada_v3.py` baixa o site oficial (https://viradasp.prefeitura.sp.gov.br/), extrai o payload Next.js/RSC e gera `data/events.json`, `data/metadata.json` e `data/virada_cultural_2026_v3.csv`. Os mesmos arquivos são copiados para `site/data/` (consumidos pelo front-end).
- `verify_event_times.py` confere, em paralelo, cada evento contra a respectiva página de detalhes do site oficial.
- `site/` contém o front-end estático (HTML, CSS, JS puro, sem build).

## Uso

```bash
uv run scrape_virada_v3.py        # atualiza os dados
uv run verify_event_times.py      # valida os horários
python3 -m http.server -d site    # serve localmente em http://localhost:8000
```

## Créditos

- Ideação: Augusto Fornitani
- Feedback: Priscila Fornitani, Tharcísio Nogueira
- Código: 1% Augusto Fornitani, 99% Claude Opus 4.7

Dados pertencem à Prefeitura de São Paulo. Este é um projeto não-oficial, feito para uso pessoal e pesquisa. Sempre confira os horários no site oficial.
