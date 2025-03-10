import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from load_functions import path_dict_to_df, load_and_preprocess_grupo, fetch_file_from_google_drive
from cotas_processor import expandir_cotas
from graphics import compare_consorcio_circulana, plot_quota_comparison

@st.cache_data
def load_data(collateral_percentage, place_of_interest):
    apys_df = path_dict_to_df(place_of_interest)
    df_grupo = load_and_preprocess_grupo('santander_cotas_pre_grupo_md_cota655_202502211443.csv')
    df_expanded_consorcio, df_expanded_circulana = expandir_cotas(
        df_grupo,  # Limit to 100 rows for demonstration purposes
        colateral=collateral_percentage,  # Use the user-provided collateral percentage
        apys_df=apys_df,
        tx_adm_circulana=None
    )
    return df_expanded_consorcio, df_expanded_circulana, df_grupo

st.sidebar.header("Filters")
# Place of interest dropdown
place_of_interest = st.sidebar.selectbox(
    "Select Place of Interest",
    options=['aave', 'compound', 'uniswap', 'balancer'],  # Options from path_dict_to_df
    index=0  # Default to 'aave'
)
collateral_percentage = st.sidebar.slider(
    "Collateral Percentage",
    min_value=0.0,
    max_value=1.0,
    value=0.4  # Default to 40%
)

# Initialize previous values in session state if not already set
if "prev_place_of_interest" not in st.session_state:
    st.session_state.prev_place_of_interest = place_of_interest
if "prev_collateral_percentage" not in st.session_state:
    st.session_state.prev_collateral_percentage = collateral_percentage

# Check if either parameter has changed since last load
params_changed = (
    st.session_state.prev_place_of_interest != place_of_interest or
    st.session_state.prev_collateral_percentage != collateral_percentage
)

if params_changed:
    # Ask for confirmation only if one of the parameters changed
    if not st.sidebar.checkbox("Parameters changed: Confirm to recompute data (this may take 5 minutes)"):
        st.info("Please check the box to recompute the data when parameters are changed.")
        st.stop()

# Load data with the current parameters
df_expanded_consorcio, df_expanded_circulana, df_grupo = load_data(collateral_percentage, place_of_interest)

# Update the stored previous values after data is loaded
st.session_state.prev_place_of_interest = place_of_interest
st.session_state.prev_collateral_percentage = collateral_percentage

quota_id = st.sidebar.selectbox(
    "Select Quota ID",
    options=df_grupo['id'].unique()  # Dynamically populate based on the dataset
)

# TX Adm filter dropdown
tx_adm_options = ["All"] + sorted(df_grupo['TX_adm_%'].unique().tolist())
tx_adm_filter = st.sidebar.selectbox(
    "Select TX Adm %",
    options=tx_adm_options,
    index=None  # Default to "All"
)
# Create month filter options for each event (including an "All" option)
creation_months = ["All"] + sorted(
    pd.to_datetime(df_grupo['dt_venda'], errors='coerce')
    .dropna()
    .dt.to_period('M')
    .astype(str)
    .unique()
    .tolist()
)
cancellation_months = ["All"] + sorted(
    pd.to_datetime(df_grupo['dt_canc'], errors='coerce')
    .dropna()
    .dt.to_period('M')
    .astype(str)
    .unique()
    .tolist()
)
contemplation_months = ["All"] + sorted(
    pd.to_datetime(df_grupo['dt_contemplacao'], errors='coerce')
    .dropna()
    .dt.to_period('M')
    .astype(str)
    .unique()
    .tolist()
)

# Let the user select a month for each event
selected_creation_month = st.sidebar.selectbox(
    "Filter by Creation Month (dt_venda)", creation_months
)
selected_cancellation_month = st.sidebar.selectbox(
    "Filter by Cancellation Month (dt_canc)", cancellation_months
)
selected_contemplation_month = st.sidebar.selectbox(
    "Filter by Contemplacao Month (dt_contemplacao)", contemplation_months
)
# Filter data based on selected months
def filter_data(df, creation_month, cancellation_month, contemplation_month):
    # Convert columns to datetime if they are not already
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

# Apply filters to df_grupo
filtered_grupo = filter_data(df_grupo, selected_creation_month, selected_cancellation_month, selected_contemplation_month)
# Filter df_expanded_consorcio and df_expanded_circulana based on the filtered_grupo IDs
filtered_consorcio = df_expanded_consorcio[df_expanded_consorcio['id'].isin(filtered_grupo['id'])]
filtered_circulana = df_expanded_circulana[df_expanded_circulana['id'].isin(filtered_grupo['id'])]
st.write("### Quota Details")
st.write(filtered_consorcio)

st.write("### Custo total do grupo para os clientes")
compare_consorcio_circulana(
    df_expanded_consorcio,
    df_expanded_circulana,
    tx_adm_filter=None,  # Optional: Add a filter for TX Adm if needed
    month_contemplated=selected_contemplation_month if selected_contemplation_month != "All" else None,
    month_canceled=selected_cancellation_month if selected_cancellation_month != "All" else None
)
# Quota ID dropdown for detailed visualization
quota_id = st.sidebar.selectbox(
    "Select Quota ID for Detailed Visualization",
    options=filtered_grupo['id'].unique()
)
if quota_id:
    st.write(f"### Detalhes da cota {quota_id}")
    plot_quota_comparison(
        df_expanded_consorcio,
        df_expanded_circulana,
        quota_id
    )
