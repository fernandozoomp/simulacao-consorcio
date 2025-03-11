import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd

def compare_consorcio_circulana(df_expanded_consorcio, df_expanded_circulana, selected_id=None, tx_adm_filter=None, month_contemplated=None, month_canceled=None):
    # Filter data based on the selected criteria
    if selected_id:
        df_expanded_consorcio = df_expanded_consorcio[df_expanded_consorcio['id'] == selected_id]
        df_expanded_circulana = df_expanded_circulana[df_expanded_circulana['id'] == selected_id]
    
    if tx_adm_filter:
        df_expanded_consorcio = df_expanded_consorcio[df_expanded_consorcio['TX_adm_%'] == tx_adm_filter]
        df_expanded_circulana = df_expanded_circulana[df_expanded_circulana['id'].isin(df_expanded_consorcio['id'])]
    
    if month_contemplated:
        df_expanded_consorcio = df_expanded_consorcio[df_expanded_consorcio['month'] == month_contemplated]
        df_expanded_circulana = df_expanded_circulana[df_expanded_circulana['id'].isin(df_expanded_consorcio['id'])]
    
    if month_canceled:
        df_expanded_consorcio = df_expanded_consorcio[df_expanded_consorcio['month'] == month_canceled]
        df_expanded_circulana = df_expanded_circulana[df_expanded_circulana['id'].isin(df_expanded_consorcio['id'])]
    
    # Calculate total costs and returns
    total_cost_consorcio = df_expanded_consorcio['FC_paid'].sum() + df_expanded_consorcio['TX_adm_monthly'].sum() + df_expanded_consorcio['FR_paid'].sum() + df_expanded_consorcio['seguro_paid'].sum()
    total_cost_circulana = df_expanded_circulana['FC_paid'].sum() + df_expanded_circulana['TX_adm_monthly'].sum()
    
    # Display total costs using Streamlit
    st.metric("Total Cost Consórcio", f"R$ {total_cost_consorcio:,.2f}")
    st.metric("Total Cost Circulana", f"R$ {total_cost_circulana:,.2f}")
    
    # Plot comparison
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.bar(['Consórcio', 'Circulana'], [total_cost_consorcio, total_cost_circulana], label='Total Cost')
    ax.set_xlabel('Option')
    ax.set_ylabel('Amount (R$)')
    ax.set_title('Custo total Consórcio vs Circulana')
    ax.legend()
    
    # Display the plot in Streamlit
    st.pyplot(fig)

def display_visualizations(df_expanded_consorcio, df_grupo):
    """
    Displays visualizations and calculations for the consorcio data in a Streamlit app.
    
    Parameters:
    df_expanded_consorcio (pd.DataFrame): DataFrame containing expanded consorcio data.
    df_grupo (pd.DataFrame): DataFrame containing grupo data.
    """
    # Total FC, FR, and Adm Taxes
    total_fc = df_expanded_consorcio["FC_paid"].sum()
    total_fr = df_expanded_consorcio["FR_paid"].sum()
    total_tx_adm = df_expanded_consorcio["TX_adm_paid"].sum()

    st.write(f"Total FC: R$ {total_fc:,.2f}")
    st.write(f"Total FR: R$ {total_fr:,.2f}")
    st.write(f"Total Adm Taxes: R$ {total_tx_adm:,.2f}")

    # Per Quota Analysis
    selected_id = df_expanded_consorcio["id"].unique()[0]  # Select the first quota ID for demonstration
    quota_df = df_expanded_consorcio[df_expanded_consorcio["id"] == selected_id]

    st.write(f"### Quota {selected_id} Details")
    st.write(quota_df)

    # Plot tx_adm_paid for all quotas
    st.write("### TX Adm Paid Over Time")
    plt.figure(figsize=(14, 8))
    df_expanded_consorcio.groupby("month")["TX_adm_paid"].sum().plot()
    plt.xlabel("Month")
    plt.ylabel("TX Adm Paid")
    plt.title("TX Adm Paid Over Time")
    st.pyplot(plt)

    st.write(f"O total da taxa de adm arrecadado no grupo todo foi: R$ {df_expanded_consorcio['TX_adm_paid'].sum():,.2f}")

    # Canceled Quotas Analysis
    df_canceled = df_grupo[df_grupo['dt_canc'].notna()]
    unique_ids_with_dt_canc = df_canceled['id'].unique()
    num_unique_ids_with_dt_canc = len(unique_ids_with_dt_canc)

    st.write(f"Tem {num_unique_ids_with_dt_canc} quotas canceladas no grupo")
    st.write(f"Tem {len(df_grupo['id'].unique())} quotas no grupo")

    st.write("### Quantity of Canceled Quotas per Month")
    plt.figure(figsize=(14, 8))
    df_canceled['dt_canc'] = pd.to_datetime(df_canceled['dt_canc'])
    df_canceled['month'] = df_canceled['dt_canc'].dt.to_period('M')
    df_canceled['month'].value_counts().sort_index().plot(kind='bar')
    plt.xlabel("Month")
    plt.ylabel("Quantity of Canceled Quotas")
    plt.title("Quantity of Canceled Quotas per Month")
    st.pyplot(plt)

    # Total Paid Analysis
    df_expanded_consorcio['total_paid'] = (
        df_expanded_consorcio['FC_paid'] + df_expanded_consorcio['TX_adm_paid'] +
        df_expanded_consorcio['FR_paid'] + df_expanded_consorcio['seguro_paid']
    )

    st.write("### Total Paid Over Time")
    plt.figure(figsize=(14, 8))
    df_expanded_consorcio.groupby('month')['total_paid'].sum().plot()
    plt.xlabel("Month")
    plt.ylabel("Total Paid")
    plt.title("Total Paid Over Time")
    st.pyplot(plt)

    st.write(f"O total pago no grupo todo foi: R$ {df_expanded_consorcio['total_paid'].sum():,.2f}")

    # Quotas Sold Analysis
    st.write("### Number of Quotas Sold per Month")
    df_grupo['dt_venda'] = pd.to_datetime(df_grupo['dt_venda'])
    df_grupo['month_sold'] = df_grupo['dt_venda'].dt.to_period('M')
    quotas_sold_by_month = df_grupo['month_sold'].value_counts().sort_index()

    plt.figure(figsize=(14, 8))
    quotas_sold_by_month.plot(kind='bar')
    plt.xlabel("Month")
    plt.ylabel("Number of Quotas Sold")
    plt.title("Number of Quotas Sold per Month")
    st.pyplot(plt)

def plot_quota_comparison(df_consorcio, df_circulana, quota_id):
    """
    Plots the costs and amounts received for the selected quota over time using matplotlib in Streamlit.

    Parameters:
    df_consorcio (pd.DataFrame): DataFrame containing Consórcio data.
    df_circulana (pd.DataFrame): DataFrame containing Circulana data.
    quota_id (int or str): The quota ID to filter the data.
    """
    # Filter and make copies of the data
    consorcio_q = df_consorcio[df_consorcio["id"] == quota_id].copy()
    circulana_q = df_circulana[df_circulana["id"] == quota_id].copy()

    if consorcio_q.empty or circulana_q.empty:
        raise ValueError("Quota ID not found in one of the datasets.")

    # Calculate monthly costs
    consorcio_q.loc[:, "monthly_cost"] = (
        consorcio_q["FC_paid"] + consorcio_q["TX_adm_monthly"] + 
        consorcio_q["FR_paid_monthly"] + consorcio_q["seguro_paid"]
    )
    circulana_q.loc[:, "monthly_cost"] = circulana_q["FC_paid"] + circulana_q["TX_adm_monthly"]
    
    # Calculate amount received
    consorcio_q.loc[:, "amount_received"] = consorcio_q.apply(
        lambda row: row["vl_bem"] if not row["contemplated"] else row["consorcio_w_profits"], axis=1
    )
    circulana_q.loc[:, "amount_received_colateral"] = circulana_q.apply(
        lambda row: (row["bem_contemplacao_dolar_colateral"] + row["profits_colateral"]) if row["contemplated"] 
                    else (row["vl_bem"] + row["profits_colateral"]),
        axis=1
    )
    circulana_q.loc[:, "amount_received_bem"] = circulana_q.apply(
        lambda row: (row["bem_contemplacao_dolar"] + row["profits_bem"]) if row["contemplated"] 
                    else (row["vl_bem"] + row["profits_bem"]),
        axis=1
    )

    # Calculate total amount paid (with and without collateral)
    circulana_q.loc[:, "total_paid"] = circulana_q["FC_paid"].cumsum() + circulana_q["TX_adm_monthly"].cumsum()
    circulana_q.loc[:, "total_paid_with_colateral"] = circulana_q["total_paid"] + circulana_q["colateral_initial"]
    consorcio_q.loc[:, "total_paid"] = consorcio_q['monthly_cost'].cumsum()

    # Plot monthly costs
    plt.figure(figsize=(12, 5))
    plt.plot(consorcio_q["month"], consorcio_q["monthly_cost"], label="Custo Mensal Consórcio", marker="o")
    plt.plot(circulana_q["month"], circulana_q["monthly_cost"], label="Custo Mensal Circulana", marker="s")
    plt.xlabel("Mês")
    plt.ylabel("Custo Mensal")
    plt.title(f"Custos Mensais para a Quota {quota_id}")
    plt.legend()
    plt.grid()
    st.pyplot(plt.gcf())
    plt.clf()

    # Plot TX Adm Paid
    plt.figure(figsize=(12, 5))
    plt.plot(consorcio_q["month"], consorcio_q["TX_adm_paid"], label="Consórcio TX Adm Pago", marker="o")
    plt.plot(circulana_q["month"], circulana_q["TX_adm_paid"], label="Circulana TX Adm Pago", marker="s")
    plt.xlabel("Mês")
    plt.ylabel("TX Adm Pago")
    plt.title(f"TX Adm Pago pela Quota {quota_id}")
    plt.legend()
    plt.grid()
    st.pyplot(plt.gcf())
    plt.clf()

    # Plot amount received
    plt.figure(figsize=(12, 5))
    plt.plot(consorcio_q["month"], consorcio_q["amount_received"], label="Consórcio valor a receber", marker="o")
    plt.plot(circulana_q["month"], circulana_q["amount_received_bem"], label="Circulana valor a receber (Bem)", marker="^")
    # Add a red vertical line at the month the quota changes contemplation status
    contemplation_change_month = circulana_q.loc[circulana_q['contemplated'].diff() == 1, 'month']
    if not contemplation_change_month.empty:
        plt.axvline(x=contemplation_change_month.iloc[0] - pd.DateOffset(months=1), color='red', linestyle='--', label='Contemplation Change (Previous Month)')
    plt.xlabel("Mês")
    plt.ylabel("Valor em R$")
    plt.title(f"Crédito a resgatar quota {quota_id}")
    plt.legend()
    plt.grid()
    st.pyplot(plt.gcf())
    plt.clf()

    # Plot amount received with collateral considerations
    plt.figure(figsize=(12, 5))
    consorcio_q_temp = consorcio_q.copy()
    consorcio_q_temp.loc[consorcio_q_temp["contemplated"], "amount_received"] = 0
    plt.plot(consorcio_q_temp["month"], consorcio_q_temp["amount_received"], label="Consórcio valor a receber", marker="o")
    plt.plot(circulana_q["month"], circulana_q["amount_received_colateral"], label="Circulana valor a receber (Colateral)", marker="s")
    # Add a red vertical line at the month the quota changes contemplation status
    contemplation_change_month = circulana_q.loc[circulana_q['contemplated'].diff() == 1, 'month']
    if not contemplation_change_month.empty:
        plt.axvline(x=contemplation_change_month.iloc[0] - pd.DateOffset(months=1), color='red', linestyle='--', label='Contemplation Change (Previous Month)')
    plt.xlabel("Mês")
    plt.ylabel("Valor em R$")
    plt.title(f"Crédito já resgatado quota {quota_id}")
    plt.legend()
    plt.grid()
    st.pyplot(plt.gcf())
    plt.clf()

    # Plot total amount paid
    plt.figure(figsize=(12, 5))
    plt.plot(circulana_q["month"], circulana_q["total_paid"], label="Circulana Total Pago (Excluindo Colateral)", marker="o")
    plt.plot(consorcio_q["month"], consorcio_q["total_paid"], label="Consórcio Total Pago", marker="^")
    plt.xlabel("Mês")
    plt.ylabel("Total Pago")
    plt.title(f"Total Pago para a Quota {quota_id}")
    plt.legend()
    plt.grid()
    st.pyplot(plt.gcf())
    plt.clf()

    # Calculate accumulated monthly cost and earned money
    consorcio_q.loc[:, "accumulated_monthly_cost"] = consorcio_q["monthly_cost"].cumsum()
    circulana_q.loc[:, "accumulated_monthly_cost"] = circulana_q["monthly_cost"].cumsum()
    
    consorcio_q["earned_money"] = consorcio_q.apply(
        lambda row: row["amount_received"] - row["accumulated_monthly_cost"] if row["contemplated"] else -row["accumulated_monthly_cost"], axis=1
    )
    circulana_q["earned_money"] = circulana_q.apply(
        lambda row: row["amount_received_bem"] - row["accumulated_monthly_cost"] if row["contemplated"] else -row["accumulated_monthly_cost"], axis=1
    )

    # Plot total earned money
    plt.figure(figsize=(12, 5))
    plt.plot(consorcio_q["month"], consorcio_q["earned_money"], label="Consórcio Dinheiro Ganhado", marker="o")
    plt.plot(circulana_q["month"], circulana_q["earned_money"], label="Circulana Dinheiro Ganhado", marker="^")
    plt.xlabel("Mês")
    plt.ylabel("Saldo Consórcio/Circulana")
    plt.title(f"Saldo Consórcio/Circulana para a Quota {quota_id}")
    plt.legend()
    plt.grid()
    st.pyplot(plt.gcf())
    plt.clf()

    # Create a summary dictionary with categories as columns
    summary_data = {
        "Metric": ["Consórcio (R$)", "Circulana (R$)"],
        "TX_adm": [
            consorcio_q["TX_adm_monthly"].sum(),
            circulana_q["TX_adm_monthly"].sum()
        ],
        "FC": [
            consorcio_q["FC_paid"].sum(),
            circulana_q["FC_paid"].sum()
        ],
        "FR": [
            consorcio_q["FR_paid_monthly"].sum(),
            None
        ],
        "Seguro": [
            consorcio_q["seguro_monthly"].sum(),
            None
        ],
        "Valor do crédito corrigido": [
            consorcio_q["vl_bem"].iloc[-1],
            circulana_q["vl_bem"].iloc[-1]
        ],
        "Valor inicial do bem": [
            consorcio_q["vl_bem"].iloc[0],
            circulana_q["vl_bem"].iloc[0]
        ],
        "Rentabilidade de não resgate": [
            consorcio_q["consorcio_w_profits"].iloc[-1] - consorcio_q["vl_bem"].iloc[-1],
            circulana_q["amount_received_bem"].iloc[-2] - circulana_q["vl_bem"].iloc[-1]
        ],
        "Resgate com rentabilidade (circulana)": [
            None,
            circulana_q["amount_received_colateral"].iloc[-2] - circulana_q["vl_bem"].iloc[-1] * 0.4
        ],
        "Total Pago": [
            consorcio_q["total_paid"].iloc[-1],
            circulana_q["total_paid"].iloc[-1]
        ],
        "Total Recebido sem resgate": [
            consorcio_q["amount_received"].iloc[-1],
            circulana_q["amount_received_bem"].iloc[-2]
        ],
        "Total Recebido com resgate": [
            consorcio_q["vl_bem"].iloc[-1],
            circulana_q["amount_received_colateral"].iloc[-2] + circulana_q["vl_bem"].iloc[-1] * 0.6
        ]
    }

    # Convert to DataFrame and display the summary in Streamlit
    summary_df = pd.DataFrame(summary_data)
    st.write(summary_df)
