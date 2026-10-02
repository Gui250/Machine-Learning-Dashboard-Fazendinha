# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # one-time setup
.venv/bin/streamlit run app.py                                       # run dashboard (http://localhost:8501)
.venv/bin/python dados.py                                            # self-check: data loading, conformity formula, protocol parser
.venv/bin/python dados.py modelos                                    # regenerate the import templates in modelos/
.venv/bin/python predicao.py                                         # self-check: forecasting models
```

There is no test framework. Each module has an `assert`-based `__main__` block. To test the UI headlessly, use `streamlit.testing.v1.AppTest.from_file("app.py").run()` and check `at.exception`.

## Architecture

A Streamlit controllership ("Controladoria") dashboard for **Fazendinha Resort Privé**, an hourly-stay resort. The spec is in `.llm/prd.MD`. The UI is in Brazilian Portuguese (pt-BR).

- **`dados.py`** owns the data, the domain constants and the business rules.
  - Domain constants: `METAS` (targets), `DEPARTAMENTOS` (the 66 POPs with gestor, priority P1–P4 and shift), `CENTROS` (revenue centers).
  - `carregar()` reads `data/*.csv`, which only exist after an import. A missing base comes back as an empty frame with the template columns and is listed in `ausentes`. Data enters only through the sidebar's **Importar planilhas** dialog. It offers a template download per base (`modelo_planilha`: columns from `MODELOS`, header-only data sheet, dropdowns from `PERMITIDOS`, example row from `EXEMPLOS` in the Instruções sheet), then `validar()` + `importar()`. Importing either appends and updates by `CHAVES`, or replaces the base.
  - `_gerar_demo()` is only a fixture for the self-check. The app never shows synthetic data.
  - Imported protocol workbooks are saved to `data/protocolos/`. `ler_todos_protocolos()` merges them with the docs/ workbook, and the newest version of a protocol number wins.
  - `ler_protocolos()` parses the **real** inconsistency protocols from `docs/Protocolo Avulso de inconsistência.xlsx`. It reads one sheet per protocol and skips the `MODELO` sheet.
- **`predicao.py`** does monthly forecasting. It fits a linear trend, then models seasonality (month one-hot) on the trend residuals with the chosen scikit-learn model.
  - The last 6 months are held out to compute MAE and MAPE.
  - The prediction interval is ±1.96 × the standard deviation of the holdout error.
  - At least 18 months of history are required; otherwise it raises `ValueError`, and the UI shows that message.
- **`app.py`** is a single-page app that runs top to bottom on every interaction.
  1. The sidebar filters build filtered DataFrames: `r` (revenue), `cx` (cash), `cu` (costs), `au` (audits), `pr` (protocols) and `plano` (budget).
     Without `receitas`, the app shows only an empty state and calls `st.stop()`. Tabs whose base is in `ausentes` (Custos, Auditorias, Orçado) are hidden, and so are KPIs and indicators from missing bases.
  2. `indicadores_mensais()` builds the monthly indicator table. The Indicadores and Predição tabs share it.
  3. Eight tabs mirror the Power BI model in `docs/POWER BI.pdf`: KPI "placas", gauges and monthly series.
- **Styling:**
  - `assets/estilo.css` is injected via `st.markdown`. It uses a wine, black and gold palette with the Marcellus and Jost fonts.
  - `.streamlit/config.toml` sets the base theme.

## Gotchas

- **Plotly template:** Streamlit ≥ 1.5x ignores custom Plotly templates even with `theme=None`. Always build figures with `figura(...)`, which applies `LAYOUT_BASE` explicitly, never with `go.Figure(...)`. Call figure-specific `update_layout` after `figura()`.
- **Tab selectors:** Streamlit 1.64 tabs use react-aria. Style them with `[data-testid="stTab"][aria-selected="true"]`, not the BaseWeb `[data-baseweb="tab"]` selectors.
- **Icon font:** the global font rule in the CSS must not override `[data-testid="stIconMaterial"]`. Otherwise the icon names render as text, e.g. "_arrow_right".
- **Category order:** monthly charts use categorical x labels such as `Jan/24` (from `rotulo_mes`) so months show in Portuguese. When traces add categories in a different order, set `categoryorder="array"`.
- **Cached data:** `carregar()` is wrapped in `st.cache_data`. After regenerating `data/`, restart the server.
- **Filters that don't apply everywhere:**
  - Orçado x realizado ignores the shift filter, because the budget is monthly per revenue center.
  - Protocolos ignores the period filter.

## Domain (from `docs/`)

- **Source system:** Desbravador PMS (not INCICLE).
- **Three pillars:**
  - Qualidade & Compliance: Michele.
  - Tesouraria e Receitas: Tatiane.
  - Custos e Estoques: Edgar.
- **Main KPI:** RevPAH = hospitality revenue ÷ available suite-hours.
- **POP audits:**
  - Each checklist item is classified as C, NC or NA.
  - `Índice de Conformidade = C / (C + NC) × 100`. NA items are excluded.
  - Priority: P1 (Caixas, Recepção) > P2 (DP/RH) > P3 > P4 (patrimônio).
  - Divergences should be detected within 12 h.
- **Protocolos Avulsos de Inconsistência:** each has a 24 h deadline for the Diretoria's response, plus a PDCA section.
- **Shifts:** Dia is 06h–17h59 (Caixa Dia, gestor Carlos). Noite is 18h–05h59 (Caixa Noite, gestor Ernesto).

## Reading the docs

- **All PDFs are image-only.** Render pages with `pdftoppm -r 50 -png -f N -l M <file> <out>` and view them with Read.
- **`Projeto Controladoria Etapa 2 .pdf`** (note the space before `.pdf`) has 206 pages. It contains the POP list per department and sample KPI panels with targets.
