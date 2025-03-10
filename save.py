import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px

def load_and_preprocess_apys(filepath):
    """Load and preprocess the APYs DataFrame."""
    apys_df = pd.read_csv(filepath)
    apys_df.drop(labels=['APY_REWARD', 'APY_BASE'], axis=1, inplace=True)
    apys_df["DATE"] = pd.to_datetime(apys_df["DATE"]).dt.date
    return apys_df

def get_apy_by_month(target_date, df):
    """
    Returns the average APY for the month of the given date if it exists in the dataset.

    Parameters:
    df (pd.DataFrame): DataFrame containing 'DATE' and 'APY' columns.
    target_date (np.datetime64): The date to search for (used to determine the month and year).

    Returns:
    float or None: The average APY value for the month if data exists, otherwise None.
    """
    df["DATE"] = pd.to_datetime(df["DATE"])
    target_year = pd.to_datetime(target_date).year
    target_month = pd.to_datetime(target_date).month

    monthly_data = df[(df["DATE"].dt.year == target_year) & (df["DATE"].dt.month == target_month)]
    return monthly_data["APY"].mean() if not monthly_data.empty else None

def calcular_rentabilidade(valor, data, type='circulana', apys_df=None, fc=False):
    """
    Calculates the return based on the average APY for the month of the given date.

    Parameters:
    valor (float): The initial investment value.
    data (np.datetime64): The date to determine the month and year for APY calculation.
    type (str): The type of calculation (default is 'circulana').
    apys_df (pd.DataFrame): DataFrame containing APY data.

    Returns:
    float: The calculated return based on the average APY for the month.
    """
    if type == 'circulana':
        apy = get_apy_by_month(data, apys_df)
        if apy is not None:
            apym = (1 + apy / 100) ** (1/12) - 1
            return valor * (1 + apym) if not fc else valor * (1+apym*0.7)
        else:
            
            return valor * (1 + 0.007)
    else:
        return valor

def expandir_cotas(df, df_correction, fr_integral_na_contemplacao=False, investir_fundo_comum=False, rentability_type='circulana', apys_df=None):
    """Expand the DataFrame for each month."""
    rename_map = {
        "pc_fc_pago": "FC_paid_%",
        "pc_fundo_reserva": "FR_%",
        "pc_fr_pago": "FR_paid_%",
        "pc_tx_adm": "TX_adm_%",
        "pc_tx_pago": "TX_paid_%",
        "pc_seguro": "Seguro_%",
        "nr_contrato": "id",
        "vl_bem_atual": "vl_bem",
        "pz_restante_grupo": "remaining_period",
        "qt_parcela_a_pagar": "parc_to_pay",
        "pz_contratado": "contracted_period",
        "qt_parcela_paga": "parc_paid",
        "pz_decorrido_grupo": "T_decorrido",
        "dt_entrega_bem": "dt_entrega",
        "vl_lance_embutido": "embedded_bid_vl",
        "vl_bem_corrigido": "bem_corrig_vl",
        "vl_total_contrato": "total_contract_vl",
        "vl_lance_proprio": "own_bid_vl",
        "qt_pc_atraso": "qt_parc_atraso",
        "qt_pc_lance": "qt_parc_lance"
    }
    df = df.rename(columns=rename_map)
    
    df['id'] = df['id'].astype(int)
    date_columns = ['dt_canc', 'dt_contemplacao', 'data_info', 'dt_entrega']
    for col in date_columns:
        df[col] = pd.to_datetime(df[col]).dt.date

    df_correction = df_correction.replace({',': '.'}, regex=True)
    for year in range(2020, 2026):
        df_correction[f'valor_{year}'] = df_correction[f'valor_{year}'].astype(str).apply(lambda x: float(x.replace('.', '').replace(',', '.')))

    df_correction['inicio_grupo'] = pd.to_datetime(df_correction['inicio_grupo'])
    df_correction['termino_grupo'] = pd.to_datetime(df_correction['termino_grupo'])

    def get_corrected_value(vl_bem_atual, year, month, data_entrada):
        item = df_correction[df_correction[f'valor_{year}'] == vl_bem_atual]
        if item.empty:
            closest_value = df_correction[f'valor_{year}'].sub(vl_bem_atual).abs().idxmin()
            item = df_correction.loc[closest_value]
        data_entrada = pd.to_datetime(data_entrada)
        data_corrigida = data_entrada + pd.DateOffset(months=month)
        year_corrigido = data_corrigida.year
        valor_corrigido = item[f'valor_{year_corrigido}']
        return valor_corrigido.values[0] if isinstance(valor_corrigido, pd.Series) else valor_corrigido

    expanded_rows = []
    grouped = df.groupby('id')

    for cota_id, group in grouped:
        vl_bem = group["vl_bem"].iloc[-1]
        TX_adm_percent = group["TX_adm_%"].iloc[-1]
        contracted_period = group["contracted_period"].iloc[-1]
        parc_to_pay = group["parc_to_pay"].iloc[-1]
        embedded_bid_vl = group["embedded_bid_vl"].iloc[-1]
        bem_corrig_vl = group["bem_corrig_vl"].iloc[-1]
        vl_devolver = group["vl_devolver"].iloc[-1]
        data_info = group["data_info"].iloc[-1]

        FC_already_paid = 0.0
        TX_already_paid = 0.0
        FR_already_paid = 0.0
        investimento_fundo_comum = 0.0
        rentabilidade_fundo_comum = 0.0
        rentabilidade_parcelas = 0.0
        rentabilidade_fr = 0.0

        for _, row in group.iterrows():
            start_date = pd.to_datetime(row["dt_venda"])
            end_date = min(filter(pd.notna, [
                pd.Timestamp(row["dt_canc"]) if pd.notna(row["dt_canc"]) else None,
                start_date + pd.DateOffset(months=row["contracted_period"]),
                pd.Timestamp.today()
            ]))

            months = pd.date_range(start=start_date, end=end_date, freq='MS')

            for month in months:
                canceled = pd.notna(row["dt_canc"]) and month >= pd.Timestamp(row["dt_canc"])
                contemplated = pd.notna(row["dt_contemplacao"]) and month >= pd.Timestamp(row["dt_contemplacao"])

                vl_bem_corrigido = get_corrected_value(vl_bem, month.year, month.month, start_date)

                fc_monthly = vl_bem_corrigido * (1 - FC_already_paid / vl_bem) / contracted_period
                tx_monthly = (TX_adm_percent / 100) * vl_bem_corrigido / contracted_period

                if not canceled:
                    FC_already_paid += fc_monthly
                    TX_already_paid += tx_monthly

                    if investir_fundo_comum:
                        investimento_fundo_comum += fc_monthly
                        rentabilidade_fundo_comum += calcular_rentabilidade(investimento_fundo_comum, month, rentability_type, apys_df, True) - investimento_fundo_comum

                    if fr_integral_na_contemplacao and contemplated:
                        FR_already_paid = vl_bem_corrigido * (row["FR_%"] / 100)
                        if FC_already_paid >= vl_bem:
                            rentabilidade_fr += calcular_rentabilidade(FR_already_paid, month, rentability_type, apys_df) - FR_already_paid

                expanded_rows.append({
                    "id": cota_id,
                    "month": month,
                    "canceled": canceled,
                    "contemplated": contemplated,
                    "vl_bem": vl_bem_corrigido,
                    "vl_devolver": vl_devolver if canceled else 0.0,
                    "TX_adm_%": TX_adm_percent,
                    "contracted_period": contracted_period,
                    "parc_to_pay": parc_to_pay,
                    "embedded_bid_vl": embedded_bid_vl,
                    "bem_corrig_vl": bem_corrig_vl,
                    "FC_paid": fc_monthly if not canceled else 0.0,
                    "TX_adm_paid": tx_monthly if not canceled else 0.0,
                    "FC_paid_%": min(FC_already_paid / vl_bem, 1.0),
                    "TX_paid_%": min(TX_already_paid / (TX_adm_percent / 100 * vl_bem), 1.0),
                    "FR_paid": FR_already_paid,
                    "investimento_fundo_comum": investimento_fundo_comum,
                    "rentabilidade_fundo_comum": rentabilidade_fundo_comum,
                    "rentabilidade_parcelas": rentabilidade_parcelas,
                    "rentabilidade_fr": rentabilidade_fr
                })

    df_expanded = pd.DataFrame(expanded_rows)
    return df_expanded

# Streamlit App
st.title("Cotas Analysis Dashboard")



apys_df = load_and_preprocess_apys("apys.csv")
df = pd.read_csv('santander_cotas_pre_grupo_md_cota655_202502211443.csv')
df_correction = pd.read_csv('FIPE-GRUPO-655-FIPE.csv')

# Input Parameters
fr_integral_na_contemplacao = st.sidebar.checkbox("FR Integral na Contemplação", value=True)
investir_fundo_comum = st.sidebar.checkbox("Investir no Fundo Comum", value=True)
rentability_type = st.sidebar.selectbox("Rentability Type", ["circulana", "Consorcio"])

# Process Data
df_expanded = expandir_cotas(
    df, 
    df_correction, 
    fr_integral_na_contemplacao=fr_integral_na_contemplacao, 
    investir_fundo_comum=investir_fundo_comum, 
    rentability_type=rentability_type, 
    apys_df=apys_df
)

# Visualizations
st.header("Group Analysis")

# Total FC, FR, and Adm Taxes
total_fc = df_expanded["FC_paid"].sum()
total_fr = df_expanded["FR_paid"].sum()
total_tx_adm = df_expanded["TX_adm_paid"].sum()

st.subheader("Total Accumulated")
col1, col2, col3 = st.columns(3)
col1.metric("Total FC", f"R$ {total_fc:,.2f}")
col2.metric("Total FR", f"R$ {total_fr:,.2f}")
col3.metric("Total Adm Taxes", f"R$ {total_tx_adm:,.2f}")

# Rentability Over Time
st.subheader("Rentability Over Time")
rentability_df = df_expanded.groupby("month").agg({
    "rentabilidade_fundo_comum": "sum",
    "rentabilidade_parcelas": "sum",
    "rentabilidade_fr": "sum"
}).reset_index()

fig = px.line(rentability_df, x="month", y=["rentabilidade_fundo_comum", "rentabilidade_parcelas", "rentabilidade_fr"],
                labels={"value": "Rentability", "variable": "Type"},
                title="Rentability Over Time")
st.plotly_chart(fig)

# Per Quota Analysis
st.subheader("Per Quota Analysis")
selected_id = st.selectbox("Select Quota ID", df_expanded["id"].unique())
quota_df = df_expanded[df_expanded["id"] == selected_id]

st.write(f"### Quota {selected_id} Details")
st.dataframe(quota_df)

# Plot Rentability for Selected Quota
fig2 = px.line(quota_df, x="month", y=["rentabilidade_fundo_comum", "rentabilidade_parcelas", "rentabilidade_fr"],
                labels={"value": "Rentability", "variable": "Type"},
                title=f"Rentability for Quota {selected_id}")
st.plotly_chart(fig2)