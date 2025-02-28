import streamlit as st
import pandas as pd
import numpy as np

# 1. Configurações gerais do app
st.set_page_config(page_title="Exemplo de Simulações", layout="wide")

# 2. Barra lateral - Seções para as simulações
st.sidebar.header("Parâmetros de Simulação")

with st.sidebar.expander("Simulação de Consórcio", expanded=True):
    valor_inicial_consorcio = st.number_input("Valor inicial do consórcio", value=20000, step=1000)
    prazo_consorcio = st.slider("Prazo (meses)", min_value=1, max_value=120, value=60, step=1)
    taxa_admin = st.number_input("Taxa de administração (%)", value=2.0)

with st.sidebar.expander("Simulação Circulana", expanded=False):
    valor_inicial_circulana = st.number_input("Valor inicial do Circulana", value=10000, step=1000)
    prazo_circulana = st.slider("Prazo (meses) - Circulana", min_value=1, max_value=120, value=48, step=1)
    taxa_circulana = st.number_input("Taxa Circulana (%)", value=1.5)

# 3. Exemplo de texto descritivo no corpo principal
st.write("""
### Exemplo de Análises e Visualizações

Abaixo, mostramos como você pode continuar usando suas funcionalidades de 
visualização (como dados aleatórios) **ao mesmo tempo** que adiciona configurações 
de simulação na barra lateral.
""")

# 4. Exemplo de inputs "tradicionais" no corpo principal
all_users = ["Alice", "Bob", "Charly"]
with st.container():
    users = st.multiselect("Selecione usuários", all_users, default=all_users)
    rolling_average = st.checkbox("Rolling average (média móvel)", value=False)

# 5. Geração de dados fictícios
np.random.seed(42)
data = pd.DataFrame(np.random.randn(20, len(users)), columns=users)

if rolling_average:
    data = data.rolling(7).mean().dropna()

# 6. Tabs para exibição de gráfico e tabela
tab1, tab2 = st.tabs(["Chart", "Dataframe"])

with tab1:
    st.line_chart(data, height=250)

with tab2:
    st.dataframe(data, height=250, use_container_width=True)

# 7. Exemplo de uso dos valores da barra lateral (simulações)
st.write("### Resultados das Simulações")

# Aqui você poderia inserir algum cálculo real de consórcio
resultado_consorcio = valor_inicial_consorcio + (valor_inicial_consorcio * (taxa_admin / 100))
texto_consorcio = f"Simulação de Consórcio: Valor final estimado = R$ {resultado_consorcio:,.2f}"

# E algum cálculo para o 'Circulana'
resultado_circulana = valor_inicial_circulana + (valor_inicial_circulana * (taxa_circulana / 100))
texto_circulana = f"Simulação Circulana: Valor final estimado = R$ {resultado_circulana:,.2f}"

st.write(texto_consorcio)
st.write(texto_circulana)
