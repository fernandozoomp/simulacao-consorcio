import streamlit as st
import os
import pandas as pd
import matplotlib.pyplot as plt
from load_functions import path_dict_to_df, load_and_preprocess_grupo,fetch_file_from_google_drive, get_folder_id, drive_service
from cotas_processor import expandir_cotas
from graphics import compare_consorcio_circulana, plot_quota_comparison

# =====================================================
# 1. Configurações gerais do app
# =====================================================
st.set_page_config(
    page_title="Comparação: Consórcio x Circulana",
    layout="wide"
)
st.sidebar.title("Parâmetros")
st.sidebar.header("Circulana")

with st.sidebar.expander("Filtros", expanded=True):
    place_of_interest = st.selectbox("Select Place of Interest", ['aave', 'compound', 'uniswap', 'balancer'], index=0)
    collateral_percentage = st.slider("Collateral Percentage", 0.0, 1.0, 0.4)

@st.cache_data
def load_data(place_of_interest):
    if collateral_percentage == 0.4 and place_of_interest == "aave":
        file_path_consorcio = 'df_expanded_consorcio.pkl'
        file_path_circulana = 'df_expanded_circulana.pkl'
        if not os.path.exists(file_path_consorcio):
            folder_id = get_folder_id(drive_service, "Base_simulacao")
            fetch_file_from_google_drive(drive_service, file_path_consorcio, file_path_consorcio, folder_id=folder_id)
        df_expanded_consorcio = pd.read_pickle('df_expanded_consorcio.pkl')
        if not os.path.exists(file_path_circulana):
            folder_id = get_folder_id(drive_service, "Base_simulacao")
            fetch_file_from_google_drive(drive_service, file_path_circulana, file_path_circulana, folder_id=folder_id)
        df_expanded_circulana = pd.read_pickle('df_expanded_circulana.pkl')
        df_grupo = load_and_preprocess_grupo('santander_cotas_pre_grupo_md_cota655_202502211443.csv')
    else:
        apys_df = path_dict_to_df(place_of_interest)
        df_grupo = load_and_preprocess_grupo('santander_cotas_pre_grupo_md_cota655_202502211443.csv')
        df_expanded_consorcio, df_expanded_circulana = expandir_cotas(
            df_grupo, apys_df=apys_df, tx_adm_circulana=None
        )
    return df_expanded_consorcio, df_expanded_circulana, df_grupo

# Load data
df_expanded_consorcio, df_expanded_circulana, df_grupo = load_data(place_of_interest)

# Default quotas to display
selected_quotas = [30506940, 30438293]
filtered_grupo = df_grupo[df_grupo['id'].isin(selected_quotas)]
filtered_consorcio = df_expanded_consorcio[df_expanded_consorcio['id'].isin(selected_quotas)]
filtered_circulana = df_expanded_circulana[df_expanded_circulana['id'].isin(selected_quotas)]

# Toggle for advanced filters
show_advanced_filters = st.sidebar.checkbox("Show Advanced Filters")

if show_advanced_filters:
    # Show all filtering options
    tx_adm_options = ["All"] + sorted(df_grupo['TX_adm_%'].unique().tolist())
    tx_adm_filter = st.sidebar.selectbox("Select TX Adm %", tx_adm_options, index=None)

    creation_months = ["All"] + sorted(pd.to_datetime(df_grupo['dt_venda'], errors='coerce').dropna().dt.to_period('M').astype(str).unique().tolist())
    cancellation_months = ["All"] + sorted(pd.to_datetime(df_grupo['dt_canc'], errors='coerce').dropna().dt.to_period('M').astype(str).unique().tolist())
    contemplation_months = ["All"] + sorted(pd.to_datetime(df_grupo['dt_contemplacao'], errors='coerce').dropna().dt.to_period('M').astype(str).unique().tolist())

    selected_creation_month = st.sidebar.selectbox("Filter by Creation Month (dt_venda)", creation_months)
    selected_cancellation_month = st.sidebar.selectbox("Filter by Cancellation Month (dt_canc)", cancellation_months)
    selected_contemplation_month = st.sidebar.selectbox("Filter by Contemplation Month (dt_contemplacao)", contemplation_months)

    def filter_data(df, creation_month, cancellation_month, contemplation_month):
        df['dt_venda'] = pd.to_datetime(df['dt_venda'], errors='coerce')
        df['dt_canc'] = pd.to_datetime(df['dt_canc'], errors='coerce')
        df['dt_contemplacao'] = pd.to_datetime(df['dt_contemplacao'], errors='coerce')

        if creation_month != "All":
            df = df[df['dt_venda'].dt.to_period('M').astype(str) == creation_month]
        if cancellation_month != "All":
            df = df[df['dt_canc'].dt.to_period('M').astype(str) == cancellation_month]
        if contemplation_month != "All":
            df = df[df['dt_contemplacao'].dt.to_period('M').astype(str) == contemplation_month]
        
        return df

    # Apply filters
    filtered_grupo = filter_data(df_grupo, selected_creation_month, selected_cancellation_month, selected_contemplation_month)
    filtered_consorcio = df_expanded_consorcio[df_expanded_consorcio['id'].isin(filtered_grupo['id'])]
    filtered_circulana = df_expanded_circulana[df_expanded_circulana['id'].isin(filtered_grupo['id'])]

    # Allow user to select one quota for more detailed analysis
    quota_id = st.sidebar.selectbox("Select Quota ID for Detailed Visualization", options=filtered_grupo['id'].unique())

    if quota_id:
        st.write(f"### Detailed View of Quota {quota_id}")
        plot_quota_comparison(df_expanded_consorcio, df_expanded_circulana, quota_id)

# Display Quota Details
st.title("Consórcio x Circulana")
st.write("""
    Comparamos as informações do Consórcio com o Circulana, para avaliar custos e valores envolvidos.
    """)

# Compare costs
st.header("Análise da Cota")

for quota_id in selected_quotas:
    with st.expander(f"Cenário: Cota {quota_id} (Taxa adm: {df_grupo[df_grupo['id']==quota_id]['TX_adm_%'].iloc[0]}%, Crédito inicial: R${df_grupo[df_grupo['id']==quota_id]['vl_bem'].iloc[0]})", expanded=False):
        plot_quota_comparison(filtered_consorcio, filtered_circulana, quota_id)

st.header("Análise do Grupo")
with st.expander("Visão geral", expanded=False):
    st.write("### Valor Total Pago")
    compare_consorcio_circulana(
    df_expanded_consorcio, df_expanded_circulana,
    tx_adm_filter=None if not show_advanced_filters else tx_adm_filter,
    month_contemplated=selected_contemplation_month if show_advanced_filters and selected_contemplation_month != "All" else None,
    month_canceled=selected_cancellation_month if show_advanced_filters and selected_cancellation_month != "All" else None
)
    st.write(filtered_consorcio)