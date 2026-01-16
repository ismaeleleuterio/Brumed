import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import locale
import plotly.graph_objects as go
import os

df = pd.read_excel("Base Brumed.xlsx")

df_long = df.melt(
    id_vars=["ESPECIFICA","GRUPO CONTA"],
    var_name="MES",
    value_name="VALOR"
    )

df_long = df_long[["GRUPO CONTA","ESPECIFICA","MES", "VALOR"]]

colunas_data = ["MES"]
for col in colunas_data:
    df_long[col] = pd.to_datetime(df_long[col], format="%d/%m/%y", errors="coerce").dt.to_period("M").dt.to_timestamp()


####DRE

mapa_dre = {
    ### RECEITA BRUTA ###
    **dict.fromkeys(
        [
            "CLIENTES "
        ],
        "Receita Bruta"
    ),

    ### CUSTOS OPERACIONAIS ###
    **dict.fromkeys(
        [
            "Fornecedor"
        ],
        "Custos dos Serviços"
    ),

    ### DESPESAS OPERACIONAIS ###
    **dict.fromkeys(
        [
            "FIXO"
        ],
        "Despesas Operacionais"
    ),

    ### DESPESAS TRIBUTÁRIAS E FINANCEIRAS ###
    **dict.fromkeys(
        [
            "Fiscal e Financeiro"
        ],
        "Despesas Tributárias e Financeiras"
    ),

    ### INVESTIMENTOS ###
    **dict.fromkeys(
        [
            "INVESTIMENTO "
        ],
        "Investimentos"
    ),

    ### ANTECIPAÇÃO SÓCIOS ###
    **dict.fromkeys(
        [
            "Variavél Sócio"
        ],
        "Retirada - Sócio"
    ),

    ###META DE FATURAMENTO###
    **dict.fromkeys(
        [
            "META FATURAMENTO "
        ],
        "Faturamento - Meta 2025"
    ),

    ### ESTIMATIVA SIMPLES ###
    **dict.fromkeys(
        [
            "IMPOSTO SIMPLES ESTIMADO"
        ],
        "Imposto Simples - Estimado"
    ),

    ### ESTIMATIVA ROYALTIES BRUMED"
    **dict.fromkeys(
        [
            "ROYALTIES BRUMED ESTIMADOS"
        ],
        "Royalties Brumed - Estimado"
    )

}

df_long["Grupo_DRE"] = df_long["GRUPO CONTA"].map(mapa_dre).fillna("Outros")

# ===============================
# FUNÇÃO DE SOMA
# ===============================
def soma_total(grupo):
    return df_long.loc[df_long["Grupo_DRE"] == grupo, "VALOR"].sum()

# ===============================
# MONTAGEM DA DRE (ORDEM CLÁSSICA)
# ===============================
dre_layout = []

receita_bruta = soma_total("Receita Bruta")
deducoes = soma_total("Imposto Simples - Estimado")
receita_liquida = receita_bruta - deducoes

dre_layout += [
    ("Receita Bruta", receita_bruta),
    ("(-) Simples Nacional - Estimado 17%", -deducoes),
    ("Receita Líquida", receita_liquida),
]

custos = soma_total("Custos dos Serviços")
lucro_bruto = receita_liquida - custos

dre_layout += [
    ("(-) Custos dos Serviços", -custos),
    ("Lucro Bruto", lucro_bruto),
]

despesas_operacionais = soma_total("Despesas Operacionais")
ebitda = lucro_bruto - despesas_operacionais

dre_layout += [
    ("(-) Despesas Operacionais", -despesas_operacionais),
    ("EBITDA", ebitda),
]

resultado_financeiro = soma_total("Despesas Tributárias e Financeiras")
resultado_antes_ir = ebitda - resultado_financeiro

dre_layout += [
    ("(-) Despesas Tributárias e Financeiras", -resultado_financeiro),
    ("Resultado Antes dos Royalties", resultado_antes_ir),
]

royalties = soma_total("Royalties Brumed - Estimado")
resultado_liquido = resultado_antes_ir - royalties

dre_layout += [
    ("(-) Royalties Brumed - Estimado 11%", -royalties),
    ("Resultado Líquido", resultado_liquido),
]

dre_df = pd.DataFrame(dre_layout, columns=["Descrição", "Valor"])

### av geral###

receita_base = dre_df.loc[
    dre_df["Descrição"] == "Receita Bruta", "Valor"
].values[0]

dre_df["AV (%)"] = dre_df["Valor"] / receita_base * 100

### estilos ###

def estilo_financeiro(valor):
    if not isinstance(valor, (int, float)):
        return ""
    if pd.isna(valor):
        return ""
    if valor < 0:
        return "color: red;"
    return ""


def formato_contabil(valor):
    if pd.isna(valor):
        return ""
    valor_abs = abs(valor)
    texto = (
        f"R$ {valor_abs:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )
    return f"({texto})" if valor < 0 else texto

def formato_percentual(valor):
    if pd.isna(valor):
        return ""
    valor_abs = abs(valor)
    texto = f"{valor_abs:.1f}%"
    return f"({texto})" if valor < 0 else texto

### formato final ###
styler_dre_anual = (
    dre_df
    .style
    .applymap(estilo_financeiro, subset=["Valor", "AV (%)"])
    .format({
        "Valor": formato_contabil,
        "AV (%)": formato_percentual
    })
)

### DRE MENSAL ####

def soma_mensal(grupo, mes=None):
    df = df_long[df_long["Grupo_DRE"] == grupo]

    if mes is not None:
        mes = pd.to_datetime(mes)
        df = df[df["MES"] == mes]

    return df["VALOR"].sum()

def monta_dre_por_periodo(mes=None):
    receita_bruta = soma_mensal("Receita Bruta", mes)
    deducoes = soma_mensal("Imposto Simples - Estimado", mes)
    receita_liquida = receita_bruta - deducoes

    custos = soma_mensal("Custos dos Serviços", mes)
    lucro_bruto = receita_liquida - custos

    despesas_operacionais = soma_mensal("Despesas Operacionais", mes)
    ebitda = lucro_bruto - despesas_operacionais

    resultado_financeiro = soma_mensal("Despesas Tributárias e Financeiras", mes)
    resultado_antes_ir = ebitda - resultado_financeiro

    royalties = soma_mensal("Royalties Brumed - Estimado", mes)
    resultado_liquido = resultado_antes_ir - royalties

    return pd.DataFrame([
        ("Receita Bruta", receita_bruta),
        ("(-) Simples Nacional - Estimado 17%", -deducoes),
        ("Receita Líquida", receita_liquida),
        ("(-) Custos dos Serviços", -custos),
        ("Lucro Bruto", lucro_bruto),
        ("(-) Despesas Operacionais", -despesas_operacionais),
        ("EBITDA", ebitda),
        ("(-) Despesas Tributárias e Financeiras", -resultado_financeiro),
        ("Resultado Antes dos Royalties", resultado_antes_ir),
        ("(-) Royalties Brumed - Estimado 11%", -royalties),
        ("Resultado Líquido", resultado_liquido),
    ], columns=["Descrição", "Valor"])

meses = sorted(df_long["MES"].dropna().unique())

dre_mensal_lista = []

for mes in meses:
    dre_mes = monta_dre_por_periodo(mes)
    dre_mes["MES"] = mes
    dre_mensal_lista.append(dre_mes)

dre_mensal_df = pd.concat(dre_mensal_lista)

# Pivot
dre_mensal_tabela = (
    dre_mensal_df
    .pivot(index="Descrição", columns="MES", values="Valor")
    .reset_index()
)

dre_mensal_tabela.columns = [
    col.strftime("%b/%Y").title() if isinstance(col, pd.Timestamp) else col
    for col in dre_mensal_tabela.columns
]


# Ordem correta da DRE
ordem_dre = [
    "Receita Bruta",
    "(-) Simples Nacional - Estimado 17%",
    "Receita Líquida",
    "(-) Custos dos Serviços",
    "Lucro Bruto",
    "(-) Despesas Operacionais",
    "EBITDA",
    "(-) Despesas Tributárias e Financeiras",
    "Resultado Antes dos Royalties",
    "(-) Royalties Brumed - Estimado 11%",
    "Resultado Líquido",
]

dre_mensal_tabela["Descrição"] = pd.Categorical(
    dre_mensal_tabela["Descrição"],
    categories=ordem_dre,
    ordered=True
)

dre_mensal_tabela = dre_mensal_tabela.sort_values("Descrição")

def destacar_negativos(valor):
    if pd.isna(valor):
        return ""
    if valor < 0:
        return "color: red;"
    return ""

colunas_valor = dre_mensal_tabela.columns.drop("Descrição")
### Layout Mensal com AV e AH ###

# ===============================
# 1. BASE
# ===============================
dre_base = dre_mensal_tabela.copy()
colunas_meses = dre_base.columns.drop("Descrição")

# ===============================
# 2. ANÁLISE VERTICAL (AV)
# ===============================
dre_av = dre_base.copy()

for mes in colunas_meses:
    receita_mes = dre_base.loc[
        dre_base["Descrição"] == "Receita Bruta", mes
    ].values[0]

    dre_av[f"{mes} AV (%)"] = dre_base[mes] / receita_mes * 100

# ===============================
# 3. ANÁLISE HORIZONTAL (AH)
# ===============================
dre_ah = dre_base.copy()

for i in range(1, len(colunas_meses)):
    mes_atual = colunas_meses[i]
    mes_anterior = colunas_meses[i - 1]

    dre_ah[f"{mes_atual} AH (%)"] = (
        (dre_base[mes_atual] - dre_base[mes_anterior])
        / dre_base[mes_anterior]
        * 100
    )

# ===============================
# 4. UNIR BASE + AV + AH
# ===============================
dre_analise = dre_base.copy()

for col in dre_av.columns:
    if "AV (%)" in col:
        dre_analise[col] = dre_av[col]

for col in dre_ah.columns:
    if "AH (%)" in col:
        dre_analise[col] = dre_ah[col]

# ===============================
# 5. REORDENAR COLUNAS (MÊS / AV / AH)
# ===============================
colunas_existentes = dre_analise.columns.tolist()

nova_ordem = ["Descrição"]

for i, mes in enumerate(colunas_meses):
    if mes in colunas_existentes:
        nova_ordem.append(mes)

    av_col = f"{mes} AV (%)"
    if av_col in colunas_existentes:
        nova_ordem.append(av_col)

    ah_col = f"{mes} AH (%)"
    if ah_col in colunas_existentes:
        nova_ordem.append(ah_col)

dre_analise = dre_analise[nova_ordem]

# ===============================
# 6. ESTILO
# ===============================
def estilo_financeiro(valor):
    if not isinstance(valor, (int, float)):
        return ""
    if pd.isna(valor):
        return ""
    if valor < 0:
        return "color: red;"
    return ""


def formato_contabil(valor):
    if pd.isna(valor):
        return ""
    valor_abs = abs(valor)

    texto = (
        f"R$ {valor_abs:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return f"({texto})" if valor < 0 else texto

def formato_percentual(valor):
    if pd.isna(valor):
        return ""
    valor_abs = abs(valor)
    texto = f"{valor_abs:.1f}%"
    return f"({texto})" if valor < 0 else texto


styler = (
    dre_analise
    .style
    .applymap(
        estilo_financeiro,
        subset=[col for col in dre_analise.columns if col != "Descrição"]
    )
    .format(
        {
            **{col: formato_contabil for col in colunas_meses},
            **{
                col: formato_percentual
                for col in dre_analise.columns
                if "AV (%)" in col or "AH (%)" in col
            },
        }
    )
)

# ===============================
# FLUXO DE CAIXA (BASE CORRETA)
# ===============================

# Meses ordenados (datetime)
meses = sorted(df_long["MES"].dropna().unique())

fluxo_lista = []

for mes in meses:
    dre_mes = monta_dre_por_periodo(mes)

    resultado_liquido = dre_mes.loc[
        dre_mes["Descrição"] == "Resultado Líquido", "Valor"
    ].values[0]

    investimentos = soma_mensal("Investimentos", mes)
    retirada = soma_mensal("Retirada - Sócio", mes)

    saldo = resultado_liquido - investimentos - retirada

    fluxo_lista.extend([
        {"Linha": "Resultado Líquido", "MES": mes, "VALOR": resultado_liquido},
        {"Linha": "Investimentos", "MES": mes, "VALOR": -investimentos},
        {"Linha": "Retirada - Sócio", "MES": mes, "VALOR": -retirada},
        {"Linha": "Saldo", "MES": mes, "VALOR": saldo},
    ])

fluxo_df = pd.DataFrame(fluxo_lista)

# ===============================
# TABELA FLUXO DE CAIXA (PIVOT)
# ===============================

fluxo_pivot = (
    fluxo_df
    .pivot(index="Linha", columns="MES", values="VALOR")
    .reset_index()
)

# ===============================
# STYLER (MESMO PADRÃO DA DRE)
# ===============================

styler_fluxo = (
    fluxo_pivot
    .style
    .applymap(
        estilo_financeiro,
        subset=[col for col in fluxo_pivot.columns if col != "Linha"]
    )
    .format(
        {col: formato_contabil for col in fluxo_pivot.columns if col != "Linha"}
    )
)

# ===============================
# BASE PARA GRÁFICO DE LINHAS
# ===============================

dre_plot = (
    dre_mensal_df
    .pivot(index="MES", columns="Descrição", values="Valor")
    .reset_index()
)

# Saldo do fluxo (base limpa, sem parsing)
saldo_fluxo = (
    fluxo_df[fluxo_df["Linha"] == "Saldo"]
    [["MES", "VALOR"]]
    .rename(columns={"VALOR": "Saldo"})
)

df_grafico = (
    dre_plot[[
        "MES",
        "Receita Bruta",
        "Lucro Bruto",
        "EBITDA",
        "Resultado Líquido"
    ]]
    .merge(saldo_fluxo, on="MES", how="left")
)

# ===============================
# GRÁFICO DE LINHAS
# ===============================

fig_evolucao = go.Figure()

fig_evolucao = go.Figure()

# ===============================
# Receita Bruta (BARRA)
# ===============================
fig_evolucao.add_bar(
    x=df_grafico["MES"],
    y=df_grafico["Receita Bruta"],
    name="Receita Bruta"
)

# ===============================
# EBITDA (LINHA)
# ===============================
fig_evolucao.add_trace(
    go.Scatter(
        x=df_grafico["MES"],
        y=df_grafico["EBITDA"],
        mode="lines+markers",
        name="EBITDA"
    )
)

# ===============================
# Saldo (LINHA)
# ===============================
fig_evolucao.add_trace(
    go.Scatter(
        x=df_grafico["MES"],
        y=df_grafico["Saldo"],
        mode="lines+markers",
        name="Saldo"
    )
)

# ===============================
# Layout
# ===============================
fig_evolucao.update_layout(
    title="📊 Receita Bruta, EBITDA e Saldo de Caixa",
    xaxis_title="Mês",
    yaxis_title="R$",
    hovermode="x unified",
    legend_title="Indicadores",
    barmode="overlay"  # barra + linha no mesmo gráfico
)

# ===============================
# Eixos
# ===============================
fig_evolucao.update_xaxes(
    tickformat="%b/%Y",
    tickangle=-45
)

fig_evolucao.update_yaxes(
    rangemode="tozero",
    tickformat=",."
)

# ===============================
# Hover monetário completo
# ===============================
fig_evolucao.update_traces(
    hovertemplate="R$ %{y:,.2f}"
)

st.markdown(
    """
    <style>
        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #002d70;
        }

        /* Texto geral da sidebar */
        section[data-testid="stSidebar"] * {
            color: white;
        }

        /* Título do radio ("Navegação") */
        section[data-testid="stSidebar"] label {
            color: white;
            font-weight: 600;
        }

        /* Opções do radio */
        section[data-testid="stSidebar"] div[role="radiogroup"] label {
            color: white;
        }

        /* Remove fundo branco padrão */
        section[data-testid="stSidebar"] .stRadio > div {
            background: transparent;
        }
    </style>
    """,
    unsafe_allow_html=True
)

### gráficos

st.title("Brumed FP&A")


st.set_page_config(
    page_title="Brumed FP&A",
    layout="wide"
)

st.sidebar.image("Assinatura visual 11B.png", use_container_width=True)

#### CONTÁBIL 1 ####

df_encargos = pd.read_excel(
    "PLANILHA COMPARATIVA TRIBUTACAO.xlsx",
    sheet_name="ENCARGOS TRABALHISTAS"
)

df_encargos = df_encargos.where(pd.notna(df_encargos), "")

# ===============================
# FUNÇÕES DE FORMATAÇÃO
# ===============================
def formato_automatico(v):
    # Trata None, NaN e vazios
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""

    # Texto → retorna como está
    if not isinstance(v, (int, float)):
        return v

    # Percentual (ex: 0.28 = 28%)
    if -1 <= v <= 1:
        texto = f"{abs(v) * 100:.1f}%"
        return f"({texto})" if v < 0 else texto

    # Monetário
    texto = (
        f"R$ {abs(v):,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return f"({texto})" if v < 0 else texto
def zebra_linhas(row):
    cor = "#f2f2f2" if row.name % 2 else "white"
    return [f"background-color: {cor}"] * len(row)

def estilo_negativo_parenteses(v):
    if isinstance(v, str):
        v_strip = v.strip()
        if v_strip.startswith("(") and v_strip.endswith(")"):
            return "color: red;"
    return ""


# ===============================
# STYLER FINAL
# ===============================

styler_encargos = (
    df_encargos
    .style
    .format(formato_automatico)
    .apply(zebra_linhas, axis=1)
)
df_encargos_2 = pd.read_excel(
    "PLANILHA COMPARATIVA TRIBUTACAO.xlsx",
    sheet_name="ENCARGOS TRABALHISTAS (2)"
).where(pd.notna, "")

styler_encargos_2 = (
    df_encargos_2
    .style
    .format(formato_automatico)
    .apply(zebra_linhas, axis=1)
)


### CONTÁBIL 2 ###
df_simples = pd.read_excel(
    "PLANILHA COMPARATIVA TRIBUTACAO.xlsx",
    sheet_name="SIMPLES"
)

df_simples = df_simples.where(pd.notna(df_simples), "")

styler_simples = (
    df_simples
    .style
    .format(formato_automatico)
    .apply(zebra_linhas, axis=1)
)


### CONTABIL 3 ###
df_lp_normais = pd.read_excel(
    "PLANILHA COMPARATIVA TRIBUTACAO.xlsx",
    sheet_name="L. PRESUMIDO SERV. NORMAIS"
).where(pd.notna, "")

styler_lp_normais = (
    df_lp_normais
    .style
    .format(formato_automatico)
    .apply(zebra_linhas, axis=1)
)

df_lp_normais_2 = pd.read_excel(
    "PLANILHA COMPARATIVA TRIBUTACAO.xlsx",
    sheet_name="L. PRESUMIDO SERV. NORMAIS (2)"
).where(pd.notna, "")

styler_lp_normais_2 = (
    df_lp_normais_2
    .style
    .format(formato_automatico)
    .apply(zebra_linhas, axis=1)
)

df_lp_normais_3 = pd.read_excel(
    "PLANILHA COMPARATIVA TRIBUTACAO.xlsx",
    sheet_name="L. PRESUMIDO SERV. NORMAIS (3)"
).where(pd.notna, "")

styler_lp_normais_3 = (
    df_lp_normais_3
    .style
    .format(formato_automatico)
    .apply(zebra_linhas, axis=1)
)


### CONTÁBIL 4 ###
df_lp_medicos = pd.read_excel(
    "PLANILHA COMPARATIVA TRIBUTACAO.xlsx",
    sheet_name="L. PRESUMIDO SERV. MÉDICOS"
).where(pd.notna, "")

styler_lp_medicos = (
    df_lp_medicos
    .style
    .format(formato_automatico)
    .apply(zebra_linhas, axis=1)
)

df_lp_medicos_2 = pd.read_excel(
    "PLANILHA COMPARATIVA TRIBUTACAO.xlsx",
    sheet_name="L. PRESUMIDO SERV. MÉDICOS (2)"
).where(pd.notna, "")

styler_lp_medicos_2 = (
    df_lp_medicos_2
    .style
    .format(formato_automatico)
    .apply(zebra_linhas, axis=1)
)

df_lp_medicos_3 = pd.read_excel(
    "PLANILHA COMPARATIVA TRIBUTACAO.xlsx",
    sheet_name="L. PRESUMIDO SERV. MÉDICOS (3)"
).where(pd.notna, "")

styler_lp_medicos_3 = (
    df_lp_medicos_3
    .style
    .format(formato_automatico)
    .apply(zebra_linhas, axis=1)
)

### CONTÁBIL 5 ###
df_lr = pd.read_excel(
    "PLANILHA COMPARATIVA TRIBUTACAO.xlsx",
    sheet_name="L. REAL"
).where(pd.notna, "")

styler_lr = (
    df_lr
    .style
    .format(formato_automatico)
    .apply(zebra_linhas, axis=1)
)

df_lr_2 = pd.read_excel(
    "PLANILHA COMPARATIVA TRIBUTACAO.xlsx",
    sheet_name="L. REAL (2)"
).where(pd.notna, "")

styler_lr_2 = (
    df_lr_2
    .style
    .format(formato_automatico)
    .apply(zebra_linhas, axis=1)
)

df_lr_3 = pd.read_excel(
    "PLANILHA COMPARATIVA TRIBUTACAO.xlsx",
    sheet_name="L. REAL (3)"
).where(pd.notna, "")

styler_lr_3 = (
    df_lr_3
    .style
    .format(formato_automatico)
    .apply(zebra_linhas, axis=1)
)

### CONTÁBIL 6 ###
df_simples_real = pd.read_excel(
    "PLANILHA COMPARATIVA TRIBUTACAO.xlsx",
    sheet_name="SIMPLES FOLHA + REAL APURAÇÃO"
).where(pd.notna, "")

styler_simples_real = (
    df_simples_real
    .style
    .format(formato_automatico)
    .apply(zebra_linhas, axis=1)

)

menu = st.sidebar.radio(
    "Navegação",
    ["Dashboard", "Demonstrações", "Tabelas", "Comparativo das apurações"]
)

if menu == "Dashboard":
    
    df_grafico = (
        df_long[df_long["Grupo_DRE"].isin([
            "Receita Bruta",
            "Faturamento - Meta 2025"
        ])]
        .groupby(["MES", "Grupo_DRE"], as_index=False)["VALOR"]
        .sum()
    )

    st.subheader("📈 Receita Bruta x Meta de Faturamento 2025")

    fig_receita_meta = px.line(
        df_grafico,
        x="MES",
        y="VALOR",
        color="Grupo_DRE",
        markers=True,
        labels={
            "MES": "Mês",
            "VALOR": "Valor (R$)",
            "Grupo_DRE": ""
        }
    )

    fig_receita_meta.update_layout(
        xaxis_tickformat="%m/%Y",
        hovermode="x unified",
        legend_title_text=""
    )

    fig_receita_meta.update_yaxes(
        tickprefix="R$ ",
        separatethousands=True
    )
    fig_receita_meta.update_yaxes(
    tickformat=",.0f",
    tickprefix="R$ ",
    separatethousands=True
    )

    fig_receita_meta.update_yaxes(
    rangemode="tozero"
    )

    st.plotly_chart(fig_receita_meta, use_container_width=True)

    st.subheader("Composição Lucro Bruto")
    col1, col2 = st.columns(2)
    with col1:
        dre_chart = (
            dre_mensal_df[
                dre_mensal_df["Descrição"].isin([
                    "Receita Bruta",
                    "(-) Simples Nacional - Estimado 17%",
                    "(-) Custos dos Serviços",
                    "Lucro Bruto"
                ])
            ]
            .pivot(index="MES", columns="Descrição", values="Valor")
            .reset_index()
        )

        dre_chart["MES"] = pd.to_datetime(dre_chart["MES"])
        fig = go.Figure()

        # Receita Bruta
        fig.add_bar(
            x=dre_chart["MES"],
            y=dre_chart["Receita Bruta"],
            name="Receita Bruta"
        )

        # Simples (negativo)
        fig.add_bar(
            x=dre_chart["MES"],
            y=dre_chart["(-) Simples Nacional - Estimado 17%"],
            name="(-) Simples Nacional"
        )

        # Custos
        fig.add_bar(
            x=dre_chart["MES"],
            y=dre_chart["(-) Custos dos Serviços"],
            name="(-) Custos dos Serviços"
        )

        # Lucro Bruto (linha)
        fig.add_trace(
            go.Scatter(
                x=dre_chart["MES"],
                y=dre_chart["Lucro Bruto"],
                mode="lines+markers",
                name="Lucro Bruto",
                yaxis="y"
            )
        )

        fig.update_layout(
            barmode="relative",
            title="📊 Receita, Custos e Lucro Bruto",
            xaxis_title="Mês",
            yaxis_title="R$",
            legend_title="Contas",
        )

        # Eixo Y iniciando em zero
        fig.update_yaxes(rangemode="tozero")

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        df_custos = df_long[df_long["Grupo_DRE"] == "Custos dos Serviços"]

        df_custos_agg = df_custos.groupby("ESPECIFICA", as_index=False)["VALOR"].sum()

        # Cria o Pie Chart
        fig_pie_custos = px.pie(
            df_custos_agg,
            names="ESPECIFICA",
            values="VALOR",
            title="Distribuição dos Custos dos Serviços por Conta Financeira",
            hole=0.3  # donut
        )

        # Remove labels e mantém hover com valor e percentual
        fig_pie_custos.update_traces(
            textinfo="none",
            hovertemplate="%{label}: R$ %{value:,.2f} (<b>%{percent}</b>)"
        )


        # Mostra no Streamlit
        st.plotly_chart(fig_pie_custos, use_container_width=True)
# =============================== 
# EBITDA e Despesas Operacionais
# ===============================

    st.subheader("Composição EBITDA")
    col1, col2 = st.columns(2)

    with col1:
        ebidta_chart = (
            dre_mensal_df[
                dre_mensal_df["Descrição"].isin([
                    "Receita Líquida",
                    "(-) Custos dos Serviços",
                    "(-) Despesas Operacionais",
                    "EBITDA"
                ])
            ]
            .pivot(index="MES", columns="Descrição", values="Valor")
            .reset_index()
        )

        ebidta_chart["MES"] = pd.to_datetime(ebidta_chart["MES"])
        fig = go.Figure()

        # Receita Líquida
        fig.add_bar(
            x=ebidta_chart["MES"],
            y=ebidta_chart["Receita Líquida"],
            name="Receita Líquida"
        )

        # Custos
        fig.add_bar(
            x=ebidta_chart["MES"],
            y=ebidta_chart["(-) Custos dos Serviços"],
            name="(-) Custos dos Serviços"
        )

        # Despesas Operacionais
        fig.add_bar(
            x=ebidta_chart["MES"],
            y=ebidta_chart["(-) Despesas Operacionais"],
            name="(-) Despesas Operacionais"
        )

        # EBITDA (linha)
        fig.add_trace(
            go.Scatter(
                x=ebidta_chart["MES"],
                y=ebidta_chart["EBITDA"],
                mode="lines+markers",
                name="EBITDA",
                yaxis="y"
            )
        )

        fig.update_layout(
            barmode="relative",
            title="📊 Receita, Custos, Despesas Operacionais e EBITDA",
            xaxis_title="Mês",
            yaxis_title="R$",
            legend_title="Contas"
        )
        fig.update_yaxes(rangemode="tozero")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        df_desp_op = df_long[df_long["Grupo_DRE"] == "Despesas Operacionais"]
        df_desp_op_agg = df_desp_op.groupby("ESPECIFICA", as_index=False)["VALOR"].sum()

        fig_pie_desp_op = px.pie(
            df_desp_op_agg,
            names="ESPECIFICA",
            values="VALOR",
            title="Distribuição das Despesas Operacionais",
            hole=0.3
        )

        fig_pie_desp_op.update_traces(
            textinfo="none",
            hovertemplate="%{label}: R$ %{value:,.2f} (<b>%{percent}</b>)"
        )

        st.plotly_chart(fig_pie_desp_op, use_container_width=True)


    # =============================== 
    # Resultado Antes dos Impostos e Despesas Tributárias/Financeiras
    # ===============================

    st.subheader("Composição Resultado Antes dos Royalties")
    col1, col2 = st.columns(2)

    with col1:
        res_ant_imp_chart = (
            dre_mensal_df[
                dre_mensal_df["Descrição"].isin([
                    "EBITDA",
                    "(-) Despesas Tributárias e Financeiras",
                    "Resultado Antes dos Royalties"
                ])
            ]
            .pivot(index="MES", columns="Descrição", values="Valor")
            .reset_index()
        )

        res_ant_imp_chart["MES"] = pd.to_datetime(res_ant_imp_chart["MES"])
        fig = go.Figure()

        # EBITDA
        fig.add_bar(
            x=res_ant_imp_chart["MES"],
            y=res_ant_imp_chart["EBITDA"],
            name="EBITDA"
        )

        # Despesas Tributárias e Financeiras
        fig.add_bar(
            x=res_ant_imp_chart["MES"],
            y=res_ant_imp_chart["(-) Despesas Tributárias e Financeiras"],
            name="(-) Despesas Tributárias e Financeiras"
        )

        # Resultado Antes dos Impostos (linha)
        fig.add_trace(
            go.Scatter(
                x=res_ant_imp_chart["MES"],
                y=res_ant_imp_chart["Resultado Antes dos Royalties"],
                mode="lines+markers",
                name="Resultado Antes dos Royalties",
                yaxis="y"
            )
        )

        fig.update_layout(
            barmode="relative",
            title="📊 EBITDA, Despesas Tributárias e Resultado Antes dos Royalties",
            xaxis_title="Mês",
            yaxis_title="R$",
            legend_title="Contas"
        )
        fig.update_yaxes(rangemode="tozero")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        df_res_fin = df_long[df_long["Grupo_DRE"] == "Despesas Tributárias e Financeiras"]
        df_res_fin_agg = df_res_fin.groupby("ESPECIFICA", as_index=False)["VALOR"].sum()

        fig_pie_res_fin = px.pie(
            df_res_fin_agg,
            names="ESPECIFICA",
            values="VALOR",
            title="Distribuição das Despesas Tributárias e Financeiras",
            hole=0.3
        )

        fig_pie_res_fin.update_traces(
            textinfo="none",
            hovertemplate="%{label}: R$ %{value:,.2f} (<b>%{percent}</b>)"
        )

        st.plotly_chart(fig_pie_res_fin, use_container_width=True)

    st.subheader("📈 Evolução Financeira Mensal")
    st.plotly_chart(
    fig_evolucao,
    use_container_width=True,
    key="grafico_evolucao_financeira"
)


if menu == "Demonstrações Financeiras":
    st.subheader("📊 Demonstração do Resultado do Exercício (DRE)")
    st.dataframe(
            styler_dre_anual,
            use_container_width=True,
            hide_index=True
        )

    st.subheader("📊 DRE Mensal")

    st.dataframe(
        styler,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("📊 Fluxo de Caixa Mensal")
    st.dataframe(styler_fluxo, use_container_width=True, hide_index=True)

if menu == "Comparativo das apurações":
    st.subheader("Encargos Trabalhistas")
    st.dataframe(
    styler_encargos,
    use_container_width=True,
    hide_index=True
)
    st.dataframe(styler_encargos_2, use_container_width=True, hide_index=True
)
    st.subheader("Quadro Comparativo dos Encargos Trabalhistas")
    st.dataframe(
    styler_simples,
    use_container_width=True,
    hide_index=True
)
    st.subheader("Apuração L. Presumido - Serviços em Geral")
    st.dataframe(styler_lp_normais, use_container_width=True, hide_index=True
)
    st.dataframe(styler_lp_normais_2, use_container_width=True, hide_index=True
)
    st.dataframe(styler_lp_normais_3, use_container_width=True, hide_index=True
)
    st.subheader("Apuração L. Presumido - Serviços Médicos")
    st.dataframe(styler_lp_medicos, use_container_width=True, hide_index=True)
    st.dataframe(styler_lp_medicos_2, use_container_width=True, hide_index=True
)
    st.dataframe(styler_lp_medicos_3, use_container_width=True, hide_index=True
)
    st.subheader("Apuração L. Real")
    st.dataframe(styler_lr, use_container_width=True, hide_index=True
)
    st.dataframe(styler_lr_2, use_container_width=True, hide_index=True
)
    st.dataframe(styler_lr_3, use_container_width=True, hide_index=True
)

    st.subheader("Apuração conjugada Simples (Folha) + L. Real")
    st.dataframe(styler_simples_real, use_container_width=True, hide_index=True
)




