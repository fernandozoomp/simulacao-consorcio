import streamlit as st
import pandas as pd
import numpy as np

# =====================================================
# 1. Configurações gerais do app
# =====================================================
st.set_page_config(
    page_title="Comparação: Consórcio x Circulana",
    layout="wide"
)

# =====================================================
# 2. Mock de dados de cotas (exemplo)
#    Substitua pela leitura de CSV, se preferir.
# =====================================================
cotas_data = {
    "Cota 1": {
        "Bem": "Carro A",
        "Taxa Adm": 2.0,
        "Fundo Reserva": 0.5,
        "Prazo": 60,
        "Valor": 20000
    },
    "Cota 2": {
        "Bem": "Carro B",
        "Taxa Adm": 2.5,
        "Fundo Reserva": 0.3,
        "Prazo": 72,
        "Valor": 30000
    },
    "Cota 3": {
        "Bem": "Carro C",
        "Taxa Adm": 3.0,
        "Fundo Reserva": 0.25,
        "Prazo": 48,
        "Valor": 15000
    }
}

# =====================================================
# 3. Barra lateral: parâmetros de Simulação
# =====================================================
st.sidebar.title("Parâmetros de Simulação")

# --- 3.1 Seção Consórcio ---
with st.sidebar.expander("Consórcio", expanded=True):
    cota_escolhida = st.selectbox("Selecione a Cota", options=list(cotas_data.keys()))
    # Ao selecionar a cota, extraímos as informações para exibir
    if cota_escolhida:
        dados_cota = cotas_data[cota_escolhida]
        st.write(f"**Bem**: {dados_cota['Bem']}")
        st.write(f"**Valor**: R$ {dados_cota['Valor']:,}")
        st.write(f"**Taxa Adm**: {dados_cota['Taxa Adm']}%")
        st.write(f"**Fundo Reserva**: {dados_cota['Fundo Reserva']}%")
        st.write(f"**Prazo**: {dados_cota['Prazo']} meses")

# --- 3.2 Seção Circulana ---
with st.sidebar.expander("Circulana", expanded=False):
    valor_inicial_circulana = st.number_input("Valor inicial", value=10000, step=1000)
    prazo_circulana = st.slider("Prazo (meses) - Circulana", min_value=1, max_value=120, value=48, step=1)
    taxa_circulana = st.number_input("Taxa Circulana (%)", value=1.5)

# =====================================================
# 4. Menu de navegação (Simulando páginas)
# =====================================================
pagina = st.radio("Navegue pelas páginas:", ["Comparação", "Vantagens"])

# =====================================================
# 5. Página: Comparação
# =====================================================
if pagina == "Comparação":
    st.title("Comparação Consórcio x Circulana")
    st.write("""
    Nesta página, comparamos diretamente as informações do Consórcio escolhido
    com o produto Circulana, para avaliar custos e prazos envolvidos.
    """)

    if cota_escolhida:
        # --- 5.1 Extrair dados da cota ---
        valor_consorcio = dados_cota["Valor"]
        taxa_adm = dados_cota["Taxa Adm"]
        fundo_reserva = dados_cota["Fundo Reserva"]
        prazo_consorcio = dados_cota["Prazo"]
        
        # --- 5.2 Calcular custo total aproximado do Consórcio ---
        custo_total_consorcio = (
            valor_consorcio
            + (valor_consorcio * (taxa_adm / 100))
            + (valor_consorcio * (fundo_reserva / 100))
        )

        # --- 5.3 Calcular custo total aproximado da Circulana ---
        custo_total_circulana = valor_inicial_circulana + (valor_inicial_circulana * (taxa_circulana / 100))

        # --- 5.4 Exibir resultados ---
        st.subheader("Resultados dos Produtos")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label=f"Consórcio (Cota {cota_escolhida})",
                value=f"R$ {custo_total_consorcio:,.2f}",
                help=f"Bem: {dados_cota['Bem']} | Prazo: {prazo_consorcio} meses"
            )
        with col2:
            st.metric(
                label="Circulana",
                value=f"R$ {custo_total_circulana:,.2f}",
                help=f"Prazo: {prazo_circulana} meses"
            )

        # --- 5.5 Indicar qual produto é "melhor" (mock de análise) ---
        if custo_total_circulana < custo_total_consorcio:
            st.success("O produto **Circulana** apresenta um custo total menor neste cenário.")
        else:
            st.warning("O **Consórcio** apresenta um custo total menor neste cenário.")

    else:
        st.info("Selecione uma cota de consórcio na barra lateral para ver a comparação.")

    # --- 5.6 Exemplo de gráfico ou tabela adicional, se desejado ---
    st.write("---")
    st.write("### Visualização de Exemplo (dados fictícios)")
    all_users = ["Matheus", "Gabriel", "Fernando"]
    users = st.multiselect("Selecione usuários", all_users, default=all_users)
    rolling_average = st.checkbox("Rolling average (média móvel)", value=False)

    # Gerando dados fictícios
    np.random.seed(42)
    data = pd.DataFrame(np.random.randn(20, len(users)), columns=users)

    if rolling_average:
        data = data.rolling(7).mean().dropna()

    tab1, tab2 = st.tabs(["Chart", "Dataframe"])
    with tab1:
        st.line_chart(data, height=250)
    with tab2:
        st.dataframe(data, height=250, use_container_width=True)

# =====================================================
# 6. Página: Vantagens
# =====================================================
elif pagina == "Vantagens":
    st.title("Vantagens por Cota (Consórcio x Circulana)")
    st.write("""
    Nesta página, você pode detalhar as vantagens e benefícios de cada produto,
    destacando especialmente o **Circulana** como melhor opção.
    """)

    st.write("### Por que o Circulana é melhor?")
    st.write("- **Custo**: Em diversos cenários, o custo total do Circulana é menor.")
    st.write("- **Flexibilidade**: Permite ajustes de prazo e taxas.")
    st.write("- **Praticidade**: Evita burocracias comuns em consórcios tradicionais.")
    
    # Exemplo: incluir uma tabela comparativa entre cada cota e Circulana
    st.write("### Comparativo para cada Cota")
    colunas = ["Cota", "Bem", "Consórcio (R$)", "Circulana (R$)", "Diferença (R$)"]
    tabela_resultados = []

    for cota, info in cotas_data.items():
        valor_cons = info["Valor"]
        tx_adm = info["Taxa Adm"] / 100
        fundo_res = info["Fundo Reserva"] / 100
        custo_cons = valor_cons + (valor_cons * tx_adm) + (valor_cons * fundo_res)

        # Poderíamos usar os mesmos parâmetros de Circulana fixos ou criar uma lógica
        # Aqui, apenas um mock fixo como exemplo
        custo_circ = 10000 + (10000 * 0.015)

        tabela_resultados.append([
            cota,
            info["Bem"],
            f"{custo_cons:,.2f}",
            f"{custo_circ:,.2f}",
            f"{(custo_cons - custo_circ):,.2f}"
        ])

    df_comparativo = pd.DataFrame(tabela_resultados, columns=colunas)
    st.dataframe(df_comparativo, use_container_width=True)

    st.write("""
    Como podemos observar, em vários casos, o valor final do Circulana se mantém menor,
    evidenciando que **Circulana** tende a ser uma escolha mais vantajosa.
    """)

