"""Painel de Controladoria — Fazendinha Resort Privé.  Rodar: streamlit run app.py"""
import html
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import dados
import predicao

ASSETS = Path(__file__).parent / "assets"
NOIR, NOIR2, BORDO, VINHO = "#14090C", "#1E0B10", "#4A1420", "#7A2335"
OURO, CHAMPANHE, FUMACA, ALERTA, OK = "#C9A24B", "#EADBC0", "#A8968A", "#D9604C", "#8DB580"
OURO_FRACO, GRADE = "rgba(201,162,75,.28)", "rgba(234,219,192,.08)"
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
M = dados.METAS

st.set_page_config(page_title="Controladoria · Fazendinha Resort Privé", page_icon=str(ASSETS / "logo.png"), layout="wide")
st.markdown(f"<style>{(ASSETS / 'estilo.css').read_text()}</style>", unsafe_allow_html=True)

# Layout base aplicado explicitamente: o Streamlit ≥ 1.5x ignora templates customizados do Plotly.
LAYOUT_BASE = dict(
    font=dict(family="Jost, sans-serif", color=CHAMPANHE, size=12),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", separators=",.",
    colorway=[OURO, "#B0485C", CHAMPANHE, "#8C6A3F", "#6F8F78"],
    xaxis=dict(gridcolor=GRADE, linecolor=GRADE, zeroline=False, automargin=True, tickfont=dict(color=FUMACA)),
    yaxis=dict(gridcolor=GRADE, linecolor=GRADE, zeroline=False, automargin=True, tickfont=dict(color=FUMACA)),
    hoverlabel=dict(bgcolor=BORDO, bordercolor=OURO, font=dict(family="Jost, sans-serif", color=CHAMPANHE)),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=FUMACA)),
    margin=dict(l=8, r=8, t=28, b=8),
)


def figura(dados_=None):
    return go.Figure(dados_, layout=LAYOUT_BASE)


# ---------------------------------------------------------------- formatação

def num(v, casas=0):
    if v is None or pd.isna(v):
        return "—"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def brl(v, casas=0):
    return "—" if v is None or pd.isna(v) else f"R$ {num(v, casas)}"


def brl_curto(v):
    if v is None or pd.isna(v):
        return "—"
    if abs(v) >= 1e6:
        return f"R$ {num(v / 1e6, 2)} mi"
    if abs(v) >= 1e4:
        return f"R$ {num(v / 1e3, 1)} mil"
    return brl(v)


def pct(v, casas=1):
    return "—" if v is None or pd.isna(v) else f"{num(v, casas)}%"


def div(a, b):
    return a / b if b else float("nan")


def rotulo_mes(datas):
    return [f"{MESES[d.month - 1]}/{d.year % 100:02d}" for d in pd.DatetimeIndex(datas)]


def mes(s):
    return s.dt.to_period("M").dt.to_timestamp()


# ---------------------------------------------------------------- componentes

def placas(itens):
    """itens: (valor, rótulo) ou (valor, rótulo, nota, bom?) — bom=None deixa a nota neutra."""
    for col, item in zip(st.columns(len(itens)), itens):
        valor, rotulo, nota, bom = (*item, None, None)[:4]
        classe = "" if bom is None else ("bom" if bom else "ruim")
        extra = f'<div class="delta {classe}">{nota}</div>' if nota else ""
        col.markdown(f'<div class="placa"><div class="valor">{valor}</div><div class="rotulo">{rotulo}</div>{extra}</div>',
                     unsafe_allow_html=True)
    st.write("")


def nota_meta(valor, meta, fmt, maior_melhor=True):
    if pd.isna(valor):
        return None, None
    bom = valor >= meta if maior_melhor else valor <= meta
    return f"{'▲' if bom else '▼'} meta {fmt(meta)}", bom


@contextmanager
def moldura(titulo, sub=None):
    with st.container(border=True):
        st.markdown(f'<p class="titulo-grafico">{titulo}</p>' + (f'<p class="sub-grafico">{sub}</p>' if sub else ""),
                    unsafe_allow_html=True)
        yield


def grafico(fig, altura=320, **kw):
    fig.update_layout(height=altura)
    return st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo": False}, **kw)


def gauge(valor, meta, titulo, fmt, maximo, maior_melhor=True, prefixo="", sufixo="", casas=1):
    bom = (valor >= meta if maior_melhor else valor <= meta) if pd.notna(valor) else True
    fig = figura(go.Indicator(
        mode="gauge+number", value=None if pd.isna(valor) else valor,
        number=dict(prefix=prefixo, suffix=sufixo, valueformat=f",.{casas}f",
                    font=dict(family="Marcellus, serif", size=30, color=CHAMPANHE)),
        title=dict(text=titulo, font=dict(family="Marcellus, serif", size=15, color=CHAMPANHE)),
        domain=dict(x=[0, 1], y=[0, 0.92]),
        gauge=dict(axis=dict(range=[0, maximo], visible=False), bar=dict(color=OURO if bom else ALERTA, thickness=0.34),
                   bgcolor="rgba(234,219,192,.07)", borderwidth=0,
                   threshold=dict(line=dict(color=CHAMPANHE, width=2), thickness=0.95, value=meta)),
    ))
    fig.add_annotation(text=f"meta {fmt(meta)}", x=0.5, y=-0.1, showarrow=False, font=dict(color=FUMACA, size=11))
    fig.update_layout(margin=dict(l=16, r=16, t=34, b=22))
    with st.container(border=True):
        grafico(fig, altura=185)


def linha_mensal(datas, valores, nome, fmt_hover, meta=None, rotulos=True, cor=OURO):
    x = rotulo_mes(datas)
    fig = figura(go.Scatter(
        x=x, y=valores, name=nome, mode="lines+markers+text" if rotulos else "lines+markers",
        text=[num(v, 0) for v in valores] if rotulos else None, textposition="top center",
        textfont=dict(size=10, color=FUMACA), line=dict(color=cor, width=2, shape="spline", smoothing=0.6),
        marker=dict(size=5, color=cor), fill="tozeroy", fillcolor="rgba(201,162,75,.10)",
        hovertemplate="%{x}<br>" + nome + " " + fmt_hover + "<extra></extra>",
    ))
    if meta is not None:
        fig.add_hline(y=meta, line=dict(color=CHAMPANHE, width=1, dash="dot"), annotation_text="meta",
                      annotation_font=dict(color=FUMACA, size=10), annotation_position="top left")
    return fig


def cor_sinal(v, maior_melhor=True):
    if pd.isna(v) or v == 0:
        return f"color: {FUMACA}"
    return f"color: {OK if (v > 0) == maior_melhor else ALERTA}"


def seta(v):
    return "—" if pd.isna(v) else f"{'▲' if v >= 0 else '▼'} {num(abs(v), 2)}%"


# ---------------------------------------------------------------- dados e filtros

@st.cache_data(show_spinner="Carregando bases…")
def carregar():
    return dados.carregar()


bases, ausentes = carregar()
if aviso := st.session_state.pop("importado", None):
    st.toast(aviso, icon=":material/check_circle:")


def concluir_importacao(msg):
    carregar.clear()
    st.session_state["importado"] = msg
    st.rerun()


@st.dialog("Importar planilhas", width="large")
def importar_planilhas():
    nomes = {t: b for b, (t, _) in dados.MODELOS.items()} | {"Protocolos de inconsistência": "protocolos"}
    titulo = st.selectbox("Base", list(nomes))
    base = nomes[titulo]
    if base == "protocolos":
        st.caption("Baixe o modelo, duplique a aba MODELO uma vez por protocolo e preencha. "
                   "Um protocolo com número já existente substitui o anterior.")
        st.download_button("Baixar modelo", dados.modelo_protocolo(), "modelo_protocolos.xlsx",
                           icon=":material/download:")
        arquivo = st.file_uploader("Planilha preenchida", type="xlsx")
        if arquivo and st.button("Importar", type="primary"):
            try:
                n = len(dados.importar_protocolos(arquivo.getvalue(), arquivo.name))
            except ValueError as erro:
                st.error(str(erro))
            else:
                concluir_importacao(f"{n} protocolo(s) importado(s).")
        return

    st.caption("Baixe o modelo, preencha a primeira aba mantendo os nomes das colunas e envie em .xlsx ou .csv. "
               "A aba Instruções descreve cada coluna.")
    st.download_button("Baixar modelo", dados.modelo_planilha(base, bases[base]), f"modelo_{base}.xlsx",
                       icon=":material/download:")
    arquivo = st.file_uploader("Planilha preenchida", type=["xlsx", "csv"])
    if not arquivo:
        return
    try:
        df = dados.validar(base, dados.ler_planilha(arquivo))
    except ValueError as erro:
        st.error("A planilha não segue o modelo:\n\n" + "\n".join(f"- {p}" for p in str(erro).splitlines()))
        return
    st.success(f"{num(len(df))} linhas válidas, de {df.iloc[:, 0].min():%d/%m/%Y} a {df.iloc[:, 0].max():%d/%m/%Y}.")
    st.dataframe(df.head(), hide_index=True)
    substituir = base not in ausentes and st.radio(
        "Como importar", ["Acrescentar e atualizar", "Substituir a base inteira"],
        help="Acrescentar mantém o que já existe e atualiza as linhas repetidas "
             "(mesma data e hora, turno, centro ou POP).") == "Substituir a base inteira"
    if st.button("Importar", type="primary"):
        dados.importar(base, df, substituir)
        concluir_importacao(f"{titulo}: {num(len(df))} linhas importadas.")


def botao_importar():
    if st.button("Importar planilhas", icon=":material/upload_file:", width="stretch"):
        importar_planilhas()


def faltando(*bs):
    return ", ".join(dados.MODELOS[b][0] for b in bs if b in ausentes)


CABECALHO = ('<div class="cabecalho"><div><div class="sobre">Fazendinha Resort Privé</div>'
             '<h1>Painel de Controladoria</h1></div>{}</div>')

# o período e quase todos os indicadores saem das receitas: sem elas não há o que mostrar
if "receitas" in ausentes:
    with st.sidebar:
        st.image(str(ASSETS / "logo-branco.png"), width=210)
        botao_importar()
    st.markdown(CABECALHO.format(""), unsafe_allow_html=True)
    st.markdown('<div class="aviso">Nenhum dado inserido ainda. Use <b>Importar planilhas</b> na barra lateral, '
                'comece pela base de Receitas por hora e depois importe as demais.</div>', unsafe_allow_html=True)
    st.stop()

d_min, d_max = bases["receitas"]["data"].min().date(), bases["receitas"]["data"].max().date()
nomes_centro = list(dados.CENTROS.values())

with st.sidebar:
    st.image(str(ASSETS / "logo-branco.png"), width=210)
    st.markdown('<div class="sidebar-titulo">Período</div>', unsafe_allow_html=True)
    periodo = st.date_input("Período", (d_min, d_max), min_value=d_min, max_value=d_max,
                            format="DD/MM/YYYY", label_visibility="collapsed")
    st.markdown('<div class="sidebar-titulo">Operação</div>', unsafe_allow_html=True)
    turno = st.radio("Turno", ["Todos", "Dia", "Noite"], horizontal=True,
                     help="Dia: 06h às 17h59 (Caixa Dia). Noite: 18h às 05h59 (Caixa Noite).")
    centros = st.multiselect("Centro de receita", nomes_centro, default=nomes_centro)
    st.markdown('<div class="sidebar-titulo">Auditoria</div>', unsafe_allow_html=True)
    deptos = st.multiselect("Departamento", list(dados.DEPARTAMENTOS), placeholder="Todos")
    prioridades = st.multiselect("Prioridade", ["P1", "P2", "P3", "P4"], placeholder="Todas",
                                 help="P1 Crítica · P2 Alta · P3 Média · P4 Programável")
    st.markdown('<p class="sidebar-nota">Fonte dos POPs e responsáveis: Projeto Controladoria, etapas 1 e 2. '
                'Sistema de origem: Desbravador PMS.</p>', unsafe_allow_html=True)
    botao_importar()

ini = pd.Timestamp(periodo[0])
fim = pd.Timestamp(periodo[1] if len(periodo) > 1 else d_max)
ini_mes = ini.to_period("M").to_timestamp()


def no_periodo(df, col="data"):
    return df[(df[col] >= ini) & (df[col] <= fim)]


def no_periodo_mes(df, col="mes"):
    return df[(df[col] >= ini_mes) & (df[col] <= fim)]


cols_centro = [c for c, n in dados.CENTROS.items() if n in centros] or list(dados.CENTROS)
r_periodo = no_periodo(bases["receitas"])
r = r_periodo if turno == "Todos" else r_periodo[dados.turno_da_hora(r_periodo["hora"]) == turno]
r = r.assign(receita=r[cols_centro].sum(axis=1))

cx = no_periodo(bases["caixa"])
cx = cx if turno == "Todos" else cx[cx["turno"] == turno]
cx = cx.assign(divergencia=cx["valor_contado"] - cx["valor_sistema"])
cx = cx.assign(sem_divergencia=cx["divergencia"].abs() <= 5)

cu = no_periodo_mes(bases["custos"])
cu = cu[cu["centro"].isin(centros)]

turno_depto = {d: v[2] for d, v in dados.DEPARTAMENTOS.items()}
au = no_periodo(bases["auditorias"])
if deptos:
    au = au[au["departamento"].isin(deptos)]
if prioridades:
    au = au[au["prioridade"].isin(prioridades)]
if turno != "Todos":
    au = au[au["departamento"].map(turno_depto).isin([None, turno])]

pr = bases["protocolos"]
if deptos:
    pr = pr[pr["departamento"].isin(deptos)]

# orçado x realizado é mensal por centro; o turno não se aplica
realizado = (r_periodo.groupby(mes(r_periodo["data"]))[list(dados.CENTROS)].sum().rename(columns=dados.CENTROS)
             .reset_index(names="mes").melt(id_vars="mes", var_name="centro", value_name="realizado"))
plano = no_periodo_mes(bases["orcamento"]).merge(realizado, on=["mes", "centro"])
plano = plano[plano["centro"].isin(centros)]

if r.empty:
    st.warning("Nenhum dado no período e filtros escolhidos. Amplie o período na barra lateral.")
    st.stop()


def indicadores_mensais():
    g = r.groupby(mes(r["data"])).agg(receita=("receita", "sum"), hosp=("receita_hospedagem", "sum"),
                                      disp=("horas_disponiveis", "sum"), vend=("horas_vendidas", "sum"),
                                      comandas=("comandas", "sum"))
    out = pd.DataFrame({"Receita": g["receita"], "RevPAH": g["hosp"] / g["disp"],
                        "Ocupação": g["vend"] / g["disp"] * 100, "Ticket médio": g["receita"] / g["comandas"]})
    a = au.groupby(mes(au["data"]))[["conforme", "nao_conforme"]].sum()
    out["Conformidade"] = a["conforme"] / (a["conforme"] + a["nao_conforme"]) * 100
    c = cu.groupby("mes")[["cmv_real", "receita"]].sum()
    out["CMV"] = c["cmv_real"] / c["receita"] * 100
    out["Precisão de caixa"] = cx.groupby(mes(cx["data"]))["sem_divergencia"].mean() * 100
    return out


mm = indicadores_mensais()
receita_total = r["receita"].sum()
revpah = div(r["receita_hospedagem"].sum(), r["horas_disponiveis"].sum())
ocupacao = div(r["horas_vendidas"].sum(), r["horas_disponiveis"].sum()) * 100
ticket = div(receita_total, r["comandas"].sum())
conformidade = dados.indice_conformidade(au["conforme"], au["nao_conforme"])
precisao = cx["sem_divergencia"].mean() * 100 if len(cx) else float("nan")
cmv_pct = div(cu["cmv_real"].sum(), cu["receita"].sum()) * 100
abertos = int((pr["status"] != "Respondido").sum())

# ---------------------------------------------------------------- cabeçalho

st.markdown(CABECALHO.format(
    f'<div class="periodo">{ini:%d/%m/%Y} a {fim:%d/%m/%Y}<br>Turno: {turno.lower()} · '
    f'{len(centros)} de {len(nomes_centro)} centros de receita</div>'), unsafe_allow_html=True)
if ausentes:
    st.markdown(f'<div class="aviso">Ainda não importadas: {faltando(*ausentes)}. Os painéis dessas bases ficam '
                'ocultos até a importação.</div>', unsafe_allow_html=True)

# abas e indicadores cuja base ainda não foi importada não aparecem
tem_au, tem_cx = "auditorias" not in ausentes, "caixa" not in ausentes
nomes_abas = {"Visão geral": None, "Tesouraria e receitas": None, "Custos e CMV": "custos",
              "Auditorias POP": "auditorias", "Protocolos": None, "Orçado x realizado": "orcamento",
              "Indicadores": None, "Predição": None}
visiveis = [a for a, b in nomes_abas.items() if b not in ausentes]
abas = dict(zip(visiveis, st.tabs(visiveis)))

# ---------------------------------------------------------------- visão geral
with abas["Visão geral"]:
    placas([
        (brl_curto(receita_total), "Receita total"),
        (brl(revpah, 2), "RevPAH", *nota_meta(revpah, M["revpah"], brl)),
        (pct(ocupacao), "Ocupação", *nota_meta(ocupacao, M["ocupacao"], pct)),
        (brl(ticket, 2), "Ticket médio"),
        *[(pct(conformidade), "Conformidade POP", *nota_meta(conformidade, M["conformidade"], pct))] * tem_au,
        (str(abertos), "Protocolos abertos", "aguardando devolutiva" if abertos else "nenhum pendente", abertos == 0),
    ])
    medidores = [(revpah, M["revpah"], "RevPAH", brl, 100, dict(prefixo="R$ ", casas=2)),
                 (ocupacao, M["ocupacao"], "Ocupação", pct, 100, dict(sufixo="%")),
                 *[(conformidade, M["conformidade"], "Conformidade", pct, 100, dict(sufixo="%"))] * tem_au,
                 *[(precisao, M["precisao_caixa"], "Precisão de caixa", pct, 100, dict(sufixo="%"))] * tem_cx]
    for col, (*args, kw) in zip(st.columns(len(medidores)), medidores):
        with col:
            gauge(*args, **kw)

    with moldura("RevPAH por mês", "Receita de hospedagem ÷ horas-suíte disponíveis"):
        grafico(linha_mensal(mm.index, mm["RevPAH"], "RevPAH", "R$ %{y:,.2f}", meta=M["revpah"]), altura=290)

    if not faltando("orcamento"):
        with moldura("Receita orçada e realizada por mês", "Centros de receita selecionados, todos os turnos"):
            p = plano.groupby("mes")[["orcado", "realizado"]].sum()
            x = rotulo_mes(p.index)
            fig = figura([
                go.Bar(x=x, y=p["realizado"], name="Realizado", marker_color=OURO,
                       hovertemplate="%{x}<br>Realizado R$ %{y:,.0f}<extra></extra>"),
                go.Scatter(x=x, y=p["orcado"], name="Orçado", mode="lines+markers",
                           line=dict(color=CHAMPANHE, width=1.5), marker=dict(size=5),
                           hovertemplate="%{x}<br>Orçado R$ %{y:,.0f}<extra></extra>"),
            ])
            fig.update_layout(hovermode="x unified", bargap=0.35)
            grafico(fig, altura=290)

# ---------------------------------------------------------------- tesouraria
with abas["Tesouraria e receitas"]:
    por_centro = r[cols_centro].sum().rename(dados.CENTROS)
    divergentes = int((~cx["sem_divergencia"]).sum())
    placas([(brl_curto(v), k) for k, v in por_centro.items()] + [
        (pct(precisao), "Precisão de caixa", *nota_meta(precisao, M["precisao_caixa"], pct)),
        (str(divergentes), "Fechamentos divergentes", f"líquido {brl(cx['divergencia'].sum())}", divergentes == 0),
    ] * tem_cx)

    c1, c2 = st.columns([1, 1.35])
    h = r.groupby("hora")[["receita_hospedagem", "horas_disponiveis"]].sum()
    revpah_h = h["receita_hospedagem"] / h["horas_disponiveis"]
    pico = int(revpah_h.idxmax())
    with c1, moldura("Relógio de receita", f"RevPAH médio por hora do dia. Pico às {pico:02d}h ({brl(revpah_h.max(), 2)})"):
        fig = figura(go.Barpolar(
            r=revpah_h, theta=revpah_h.index * 15, width=[13.5] * len(revpah_h),
            marker=dict(color=revpah_h, colorscale=[[0, BORDO], [0.55, VINHO], [1, OURO]], line=dict(color=NOIR, width=1)),
            customdata=[f"{i:02d}h" for i in revpah_h.index],
            hovertemplate="%{customdata}<br>RevPAH R$ %{r:,.2f}<extra></extra>",
        ))
        fig.update_layout(showlegend=False, polar=dict(
            bgcolor="rgba(0,0,0,0)", hole=0.18,
            angularaxis=dict(direction="clockwise", rotation=90, tickmode="array", tickvals=list(range(0, 360, 45)),
                             ticktext=[f"{i:02d}h" for i in range(0, 24, 3)], gridcolor=GRADE, linecolor=OURO_FRACO,
                             tickfont=dict(color=FUMACA)),
            radialaxis=dict(showticklabels=False, ticks="", gridcolor=GRADE, linecolor="rgba(0,0,0,0)")))
        grafico(fig, altura=360)
    with c2, moldura("Ocupação por dia da semana e hora", "% das horas-suíte vendidas"):
        occ = r.assign(dia=r["data"].dt.dayofweek).pivot_table(index="dia", columns="hora",
                                                                values=["horas_vendidas", "horas_disponiveis"], aggfunc="sum")
        z = occ["horas_vendidas"] / occ["horas_disponiveis"] * 100
        fig = figura(go.Heatmap(
            z=z.values, x=[f"{i:02d}h" for i in z.columns], y=[DIAS_SEMANA[i] for i in z.index],
            colorscale=[[0, NOIR2], [0.5, VINHO], [1, OURO]], xgap=2, ygap=2,
            colorbar=dict(thickness=8, ticksuffix="%", outlinewidth=0, tickfont=dict(color=FUMACA)),
            hovertemplate="%{y}, %{x}<br>Ocupação %{z:.1f}%<extra></extra>"))
        fig.update_yaxes(autorange="reversed", showgrid=False)
        fig.update_xaxes(showgrid=False)
        grafico(fig, altura=360)

    c1, c2 = st.columns(2) if tem_cx else (st.container(), None)
    with c1, moldura("Receita por centro e mês"):
        rc = r.groupby(mes(r["data"]))[cols_centro].sum().rename(columns=dados.CENTROS)
        x = rotulo_mes(rc.index)
        fig = figura([go.Bar(x=x, y=rc[c], name=c, hovertemplate="%{x}<br>" + c + " R$ %{y:,.0f}<extra></extra>")
                         for c in rc.columns])
        fig.update_layout(barmode="stack", bargap=0.3)
        grafico(fig)
    if tem_cx:
        with c2, moldura("Fechamentos às cegas com divergência", "Diferença acima de R$ 5 entre o contado e o sistema"):
            dv = cx[~cx["sem_divergencia"]]
            dvm = dv.groupby([mes(dv["data"]), "turno"]).size().unstack(fill_value=0)
            x = rotulo_mes(dvm.index)
            fig = figura([go.Bar(x=x, y=dvm[t], name=f"Caixa {t}", marker_color=OURO if t == "Dia" else "#B0485C",
                                    hovertemplate="%{x}<br>" + f"Caixa {t}" + ": %{y} fechamentos<extra></extra>")
                             for t in dvm.columns])
            fig.update_layout(barmode="group", bargap=0.3)
            grafico(fig)
        with st.expander("Maiores divergências de caixa no período"):
            top = cx.reindex(cx["divergencia"].abs().sort_values(ascending=False).index).head(15)
            st.dataframe(pd.DataFrame({
                "Data": top["data"].dt.strftime("%d/%m/%Y"), "Turno": top["turno"],
                "Sistema": top["valor_sistema"].map(brl), "Contado": top["valor_contado"].map(brl),
                "Diferença": top["divergencia"].map(lambda v: brl(v, 2)),
            }), hide_index=True, width="stretch")

# ---------------------------------------------------------------- custos
if "Custos e CMV" in abas:
    with abas["Custos e CMV"]:
        if cu.empty:
            st.info("Selecione Gastronomia ou Bebidas & Clube do Whisky em “Centro de receita” para ver o CMV.")
        else:
            cmv_teorico = div(cu["cmv_teorico"].sum(), cu["receita"].sum()) * 100
            desvio = cu["cmv_real"].sum() - cu["cmv_teorico"].sum()
            placas([
                (brl_curto(cu["receita"].sum()), "Receita de A&B"),
                (brl_curto(cu["cmv_real"].sum()), "CMV real"),
                (pct(cmv_pct), "CMV real %", *nota_meta(cmv_pct, M["cmv"], pct, maior_melhor=False)),
                (pct(cmv_teorico), "CMV teórico %", "pela ficha técnica"),
                (brl_curto(desvio), "Real acima do teórico", pct(div(desvio, cu["cmv_teorico"].sum()) * 100), desvio <= 0),
                (brl_curto(cu["perdas"].sum()), "Perdas registradas"),
            ])
            c1, c2 = st.columns([1.5, 1])
            with c1, moldura("CMV real e teórico por mês", "% da receita de A&B"):
                cm = cu.groupby("mes")[["cmv_real", "cmv_teorico", "receita"]].sum()
                x = rotulo_mes(cm.index)
                fig = figura([
                    go.Scatter(x=x, y=cm["cmv_real"] / cm["receita"] * 100, name="Real", mode="lines+markers",
                               line=dict(color=OURO, width=2), hovertemplate="%{x}<br>Real %{y:.1f}%<extra></extra>"),
                    go.Scatter(x=x, y=cm["cmv_teorico"] / cm["receita"] * 100, name="Teórico", mode="lines",
                               line=dict(color=CHAMPANHE, width=1.5, dash="dash"),
                               hovertemplate="%{x}<br>Teórico %{y:.1f}%<extra></extra>"),
                ])
                fig.add_hline(y=M["cmv"], line=dict(color=ALERTA, width=1, dash="dot"), annotation_text="meta",
                              annotation_font=dict(color=FUMACA, size=10))
                fig.update_layout(hovermode="x unified", yaxis_ticksuffix="%")
                grafico(fig)
            with c2, moldura("Desvio por centro", "Real − teórico"):
                t = cu.groupby("centro")[["receita", "cmv_teorico", "cmv_real", "perdas"]].sum()
                t["Desvio %"] = (t["cmv_real"] / t["cmv_teorico"] - 1) * 100
                st.dataframe(
                    pd.DataFrame({"Centro": t.index, "CMV real %": t["cmv_real"] / t["receita"] * 100,
                                  "CMV teórico %": t["cmv_teorico"] / t["receita"] * 100, "Desvio %": t["Desvio %"]})
                    .style.format({"CMV real %": pct, "CMV teórico %": pct, "Desvio %": seta})
                    .map(lambda v: cor_sinal(v, maior_melhor=False), subset=["Desvio %"]),
                    hide_index=True, width="stretch")
                fig = figura(go.Bar(y=t.index, x=t["perdas"], orientation="h", marker_color="#B0485C",
                                       text=[brl_curto(v) for v in t["perdas"]], textposition="auto",
                                       hovertemplate="%{y}<br>Perdas R$ %{x:,.0f}<extra></extra>"))
                fig.update_layout(title=dict(text="Perdas no período", font=dict(size=13, color=FUMACA)), margin=dict(t=36))
                grafico(fig, altura=200)

# ---------------------------------------------------------------- auditorias
if "Auditorias POP" in abas:
    with abas["Auditorias POP"]:
        if au.empty:
            st.info("Nenhuma auditoria nos filtros atuais. Limpe “Departamento” ou “Prioridade” na barra lateral.")
        else:
            det = au["horas_ate_deteccao"].dropna()
            no_prazo = (det <= M["deteccao_horas"]).mean() * 100 if len(det) else float("nan")
            placas([
                (num(len(au)), "Auditorias realizadas"),
                (num(au["conforme"].sum()), "Itens conformes"),
                (num(au["nao_conforme"].sum()), "Não conformes"),
                (num(au["nao_aplicavel"].sum()), "Não aplicáveis"),
                (pct(conformidade), "Índice de conformidade", *nota_meta(conformidade, M["conformidade"], pct)),
                (pct(no_prazo), "Detectadas em até 12 h", *nota_meta(no_prazo, 90, pct)),
            ])
            st.caption("Índice de conformidade = itens C ÷ (C + NC) × 100. Itens NA não entram no cálculo.")

            c1, c2 = st.columns(2)
            dep = au.groupby("departamento")[["conforme", "nao_conforme"]].sum()
            dep["indice"] = dep["conforme"] / (dep["conforme"] + dep["nao_conforme"]) * 100
            dep = dep.sort_values("indice")
            with c1, moldura("Conformidade por departamento", "Clique numa barra para filtrar os POPs ao lado"):
                fig = figura(go.Bar(
                    y=dep.index, x=dep["indice"], orientation="h",
                    marker_color=[OURO if v >= M["conformidade"] else ALERTA for v in dep["indice"]],
                    text=[pct(v) for v in dep["indice"]], textposition="outside", cliponaxis=False,
                    hovertemplate="%{y}<br>Conformidade %{x:.1f}%<extra></extra>"))
                fig.add_vline(x=M["conformidade"], line=dict(color=CHAMPANHE, width=1, dash="dot"))
                fig.update_xaxes(range=[min(70, dep["indice"].min() - 2), 101], ticksuffix="%")
                evento = grafico(fig, altura=420, key="conf_depto", on_select="rerun", selection_mode="points")
            escolhidos = [p["y"] for p in evento.selection.points] if evento and evento.selection.points else []
            with c2, moldura("POPs com mais não conformidades",
                             ", ".join(escolhidos) if escolhidos else "Todos os departamentos filtrados"):
                base = au[au["departamento"].isin(escolhidos)] if escolhidos else au
                pops = base.groupby(["pop_num", "pop", "departamento"])["nao_conforme"].sum().nlargest(12).iloc[::-1]
                rot = [f"POP {n:02d} · {p[:38]}" for n, p, _ in pops.index]
                fig = figura(go.Bar(y=rot, x=pops.values, orientation="h", marker_color="#B0485C",
                                       customdata=[d for *_, d in pops.index], text=pops.values, textposition="outside",
                                       cliponaxis=False, hovertemplate="%{y}<br>%{customdata}<br>%{x} itens NC<extra></extra>"))
                fig.update_xaxes(range=[0, pops.max() * 1.18])
                grafico(fig, altura=420)

            c1, c2 = st.columns([1.6, 1])
            with c1, moldura("Índice de conformidade por mês"):
                grafico(linha_mensal(mm.index, mm["Conformidade"], "Conformidade", "%{y:.1f}%", meta=M["conformidade"],
                                     rotulos=False), altura=300)
            with c2, moldura("Não conformidades por prioridade", "P1 Crítica · P2 Alta · P3 Média · P4 Programável"):
                pz = au.groupby("prioridade")["nao_conforme"].sum()
                fig = figura(go.Pie(labels=pz.index, values=pz.values, hole=0.6, sort=False,
                                       marker=dict(colors=[ALERTA, OURO, "#B0485C", FUMACA][:len(pz)], line=dict(color=NOIR, width=2)),
                                       textinfo="label+percent", hovertemplate="%{label}<br>%{value} itens NC<extra></extra>"))
                fig.update_layout(showlegend=False)
                grafico(fig, altura=300)

# ---------------------------------------------------------------- protocolos
with abas["Protocolos"]:
    agora = pd.Timestamp.now()
    placas([
        (str(len(pr)), "Protocolos emitidos"),
        (str(abertos), "Aguardando devolutiva", "prazo de 24 h", abertos == 0),
        (str(pr["departamento"].nunique()), "Departamentos envolvidos"),
        (str(int(pr["pops"].map(len).sum())), "POPs citados"),
    ])
    st.caption("Fonte: docs/Protocolo Avulso de inconsistência.xlsx e protocolos importados. "
               "O filtro de período não se aplica a esta aba.")
    if pr.empty:
        st.info("Nenhum protocolo para os departamentos escolhidos.")
    for p in pr.sort_values("protocolo", ascending=False).to_dict("records"):
        prazo = p["data"] + pd.Timedelta(hours=24) if pd.notna(p["data"]) else None
        respondido = p["status"] == "Respondido"
        selo = "Respondido" if respondido else ("Prazo vencido" if prazo is not None and agora > prazo else "Aguardando devolutiva")
        e = html.escape
        st.markdown(
            f'<div class="protocolo"><span class="num">Nº {e(p["protocolo"])}</span>'
            f'<span class="selo{" ok" if respondido else ""}">{selo}</span>'
            f'<div class="meta">{e(p["departamento"])} · Setor {e(p["setor"])} · Responsável (R): {e(p["responsavel"])} · '
            f'Gestor: {e(p["gestor"])} · {p["data"]:%d/%m/%Y}</div>'
            f'<p>{e(p["descricao"])}</p>'
            f'<div class="meta" style="margin-top:.5rem">POPs: {e(" · ".join(p["pops"]))}</div></div>',
            unsafe_allow_html=True)
        with st.expander(f"Devolutiva e PDCA do protocolo {p['protocolo']}"):
            st.markdown(f"**Devolutiva da diretoria:** {p['devolutiva'] or 'ainda não registrada.'}")
            for k, nome in zip("PDCA", ["Planejamento", "Implantação", "Checagem/auditoria", "Ação"]):
                st.markdown(f"**{k}: {nome}.** {p[f'pdca_{k}'] or '—'}")

# ---------------------------------------------------------------- orçado x realizado
if "Orçado x realizado" in abas:
    with abas["Orçado x realizado"]:
        orc, rea = plano["orcado"].sum(), plano["realizado"].sum()
        desvio_pct = div(rea - orc, orc) * 100
        placas([
            (brl_curto(orc), "Receita orçada"),
            (brl_curto(rea), "Receita realizada"),
            (pct(div(rea, orc) * 100), "Aderência ao orçamento"),
            (brl_curto(rea - orc), "Desvio", seta(desvio_pct), rea >= orc),
        ])
        st.caption("O orçamento é mensal por centro de receita, então o filtro de turno não se aplica a esta aba.")

        def tabela_desvio(df, chave):
            t = df.groupby(chave)[["orcado", "realizado"]].sum()
            t["desvio"] = t["realizado"] - t["orcado"]
            t["pct"] = t["desvio"] / t["orcado"] * 100
            return t

        c1, c2 = st.columns(2)
        estilo = dict(hide_index=True, width="stretch")
        with c1, moldura("Desvio por centro de receita"):
            t = tabela_desvio(plano, "centro").sort_values("pct")
            st.dataframe(pd.DataFrame({"Centro": t.index, "Orçado": t["orcado"], "Realizado": t["realizado"],
                                       "Desvio": t["desvio"], "%": t["pct"]})
                         .style.format({"Orçado": brl, "Realizado": brl, "Desvio": brl, "%": seta})
                         .map(cor_sinal, subset=["Desvio", "%"]), **estilo)
        with c2, moldura("Desvio por mês"):
            t = tabela_desvio(plano, "mes").sort_index(ascending=False)
            st.dataframe(pd.DataFrame({"Mês": rotulo_mes(t.index), "Orçado": t["orcado"], "Realizado": t["realizado"],
                                       "Desvio": t["desvio"], "%": t["pct"]})
                         .style.format({"Orçado": brl, "Realizado": brl, "Desvio": brl, "%": seta})
                         .map(cor_sinal, subset=["Desvio", "%"]), height=250, **estilo)
        with moldura("Receita orçada e realizada por mês"):
            p = plano.groupby("mes")[["orcado", "realizado"]].sum()
            x = rotulo_mes(p.index)
            fig = figura([
                go.Bar(x=x, y=p["orcado"], name="Orçado", marker_color=VINHO,
                       hovertemplate="%{x}<br>Orçado R$ %{y:,.0f}<extra></extra>"),
                go.Bar(x=x, y=p["realizado"], name="Realizado", marker_color=OURO,
                       hovertemplate="%{x}<br>Realizado R$ %{y:,.0f}<extra></extra>"),
            ])
            fig.update_layout(barmode="group", bargap=0.25, hovermode="x unified")
            grafico(fig)

# ---------------------------------------------------------------- indicadores
with abas["Indicadores"]:
    colunas = [("RevPAH", lambda v: brl(v, 2), True), ("Ocupação", pct, True), ("Ticket médio", lambda v: brl(v, 2), True),
               ("Conformidade", pct, True), ("CMV", pct, False), ("Precisão de caixa", pct, True)]
    colunas = [c for c in colunas if mm[c[0]].notna().any()]
    tab = pd.DataFrame({"Mês": rotulo_mes(mm.index)}, index=mm.index)
    formatos, cores = {}, []
    for nome, fmt, maior_melhor in colunas:
        tab[nome] = mm[nome]
        tab[f"Δ {nome}"] = mm[nome].pct_change(fill_method=None) * 100
        formatos[nome], formatos[f"Δ {nome}"] = fmt, seta
        cores.append((f"Δ {nome}", maior_melhor))
    tab = tab.sort_index(ascending=False)
    estilizada = tab.style.format(formatos, na_rep="—")
    for coluna, maior_melhor in cores:
        estilizada = estilizada.map(lambda v, mm_=maior_melhor: cor_sinal(v, mm_), subset=[coluna])
    with moldura("Evolução dos indicadores", "Variação em relação ao mês anterior. No CMV, queda é favorável."):
        st.dataframe(estilizada, hide_index=True, width="stretch", height=480)
        st.download_button("Baixar indicadores (CSV)", mm.to_csv(sep=";", decimal=",").encode("utf-8-sig"),
                           file_name="indicadores_mensais.csv", mime="text/csv")

# ---------------------------------------------------------------- predição
with abas["Predição"]:
    formatos_ind = {"Receita": brl, "RevPAH": lambda v: brl(v, 2), "Ocupação": pct, "Ticket médio": lambda v: brl(v, 2),
                    "Conformidade": pct, "CMV": pct, "Precisão de caixa": pct}
    c1, c2, c3 = st.columns([1.2, 1.2, 1])
    indicador = c1.selectbox("Indicador", [k for k in formatos_ind if mm[k].notna().any()])
    modelo = c2.selectbox("Modelo", list(predicao.MODELOS),
                          help="A tendência é sempre linear. O modelo escolhido aprende a sazonalidade de cada mês.")
    horizonte = c3.slider("Meses à frente", 3, 12, 6)
    st.caption("O modelo usa o histórico mensal dos filtros atuais. Os 6 meses mais recentes ficam fora do treino "
               "para medir o erro, e a faixa sombreada é o intervalo de 95% baseado nesse erro.")
    fmt = formatos_ind[indicador]
    try:
        prev, met = predicao.prever(mm[indicador], horizonte, modelo)
    except ValueError as erro:
        st.warning(f"{erro} Amplie o período na barra lateral.")
    else:
        placas([
            (fmt(prev["previsto"].iloc[0]), f"Previsto para {rotulo_mes(prev['data'][:1])[0]}"),
            (fmt(prev["previsto"].sum() if indicador == "Receita" else prev["previsto"].mean()),
             f"{'Total' if indicador == 'Receita' else 'Média'} em {horizonte} meses"),
            (fmt(met["MAE"]), "Erro médio (MAE)", "na validação"),
            (pct(met["MAPE"]), "Erro percentual (MAPE)", "na validação", met["MAPE"] <= 10),
        ])
        hist = mm[indicador].dropna()
        xh, xf, xv = rotulo_mes(hist.index), rotulo_mes(prev["data"]), rotulo_mes(met["validacao"]["data"])
        fig = figura([
            go.Scatter(x=xf + xf[::-1], y=list(prev["maximo"]) + list(prev["minimo"][::-1]), fill="toself",
                       fillcolor="rgba(201,162,75,.15)", line=dict(width=0), mode="lines", hoverinfo="skip",
                       name="Intervalo 95%"),
            go.Scatter(x=xh, y=hist.values, name="Histórico", mode="lines+markers", line=dict(color=CHAMPANHE, width=1.5),
                       marker=dict(size=4), hovertemplate="%{x}<br>%{y:,.2f}<extra>Histórico</extra>"),
            go.Scatter(x=xv, y=met["validacao"]["previsto"], name="Previsto na validação", mode="lines",
                       line=dict(color="#B0485C", width=1.5, dash="dot"),
                       hovertemplate="%{x}<br>%{y:,.2f}<extra>Validação</extra>"),
            go.Scatter(x=[xh[-1]] + xf, y=[hist.iloc[-1]] + list(prev["previsto"]), name="Previsão",
                       mode="lines+markers", line=dict(color=OURO, width=2.5, dash="dash"), marker=dict(size=6),
                       hovertemplate="%{x}<br>%{y:,.2f}<extra>Previsão</extra>"),
        ])
        fig.update_layout(hovermode="x unified")
        fig.update_xaxes(categoryorder="array", categoryarray=xh + xf)
        with moldura(f"{indicador}: histórico e previsão", modelo):
            grafico(fig, altura=400)
        st.dataframe(pd.DataFrame({"Mês": xf, "Previsto": prev["previsto"].map(fmt),
                                   "Mínimo": prev["minimo"].map(fmt), "Máximo": prev["maximo"].map(fmt)}),
                     hide_index=True, width="stretch")

    with moldura("Como cada modelo faz a previsão",
                 "Os três seguem as mesmas duas etapas. A diferença está só na segunda."):
        st.markdown(
            "**Etapa 1, tendência (igual para todos).** Uma reta é ajustada ao histórico para captar se o indicador "
            "sobe ou desce ao longo do tempo. É ela que projeta o crescimento para os meses futuros.\n\n"
            "**Etapa 2, sazonalidade (muda conforme o modelo).** Depois de tirar a tendência, sobra o quanto cada mês "
            "fica acima ou abaixo da reta. O modelo escolhido aprende esse efeito de cada mês do ano "
            "(por exemplo, dezembro costuma ficar acima e março abaixo). A previsão é a reta mais o efeito do mês.\n\n"
            "- **Regressão linear (Ridge):** atribui um valor fixo a cada mês do ano, próximo da média do quanto "
            "aquele mês ficou acima ou abaixo da reta. Uma penalidade leve puxa esses valores para zero, evitando "
            "exagerar o efeito de um mês que teve um ano atípico.\n"
            "- **Random Forest:** monta 300 árvores de decisão, cada uma treinada com uma amostra sorteada do "
            "histórico, e tira a média delas. Cada árvore agrupa meses parecidos. A média de muitas árvores suaviza "
            "o resultado e reduz o peso de meses isolados fora do padrão.\n"
            "- **Gradient Boosting:** monta 200 árvores pequenas em sequência. Cada nova árvore corrige uma parte "
            "do erro que as anteriores deixaram. Aprende aos poucos e consegue acompanhar padrões sazonais mais "
            "marcados, mas com pouco histórico tende a se ajustar demais ao passado.")
        st.dataframe(pd.DataFrame({
            "": ["Como aprende o efeito do mês", "Ponto forte", "Cuidado"],
            "Regressão linear": ["Um valor fixo por mês, com penalidade", "Simples, estável e fácil de explicar",
                                 "Supõe que o efeito do mês é sempre o mesmo"],
            "Random Forest": ["Média de 300 árvores independentes", "Resistente a meses atípicos",
                              "Suaviza picos sazonais fortes"],
            "Gradient Boosting": ["200 árvores em sequência, cada uma corrigindo a anterior",
                                  "Capta sazonalidade marcada com precisão",
                                  "Pode se ajustar demais com pouco histórico"],
        }), hide_index=True, width="stretch")
        st.markdown("**Quando usar cada modelo**")
        for col, (nome, quando) in zip(st.columns(3), [
            ("Regressão linear", "- Histórico curto, de 18 a 24 meses.\n"
                                 "- Os meses se repetem de forma parecida todo ano.\n"
                                 "- Você precisa explicar a previsão para a diretoria.\n"
                                 "- Bom ponto de partida para qualquer indicador."),
            ("Random Forest", "- O histórico tem meses atípicos, como reforma, evento ou erro de lançamento.\n"
                              "- O indicador oscila muito de um mês para o outro, como Precisão de caixa e CMV.\n"
                              "- Você quer uma previsão mais conservadora, sem picos exagerados."),
            ("Gradient Boosting", "- Histórico longo, de 3 anos ou mais.\n"
                                  "- Sazonalidade forte e consistente, como Receita e Ocupação em feriados e "
                                  "datas comemorativas.\n"
                                  "- Confirme que o MAPE dele está menor que o dos outros antes de usar."),
        ]):
            col.markdown(f"*{nome}*\n\n{quando}")
        try:
            comparacao = {nome: predicao.prever(mm[indicador], horizonte, nome)[1] for nome in predicao.MODELOS}
        except ValueError:
            pass
        else:
            melhor = min(comparacao, key=lambda nome: comparacao[nome]["MAPE"])
            st.markdown(f"**Erro de cada modelo para {indicador} nos filtros atuais.** Quanto menor, melhor. "
                        f"Na prática, o erro decide: para estes dados, o recomendado é **{melhor}**.")
            st.dataframe(pd.DataFrame({"Modelo": list(comparacao),
                                       "Erro médio (MAE)": [fmt(m["MAE"]) for m in comparacao.values()],
                                       "Erro percentual (MAPE)": [pct(m["MAPE"]) for m in comparacao.values()]}),
                         hide_index=True, width="stretch")
