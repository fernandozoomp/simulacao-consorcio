import numpy as np
import warnings
import pandas as pd
from load_functions import convert_currency, calcular_rentabilidade_mes, get_corrected_value


def expandir_cotas(df, colateral=0.4, apys_df=None, compounded=False, tx_adm_circulana=None):
    """Expand the DataFrame for each month."""
    expanded_rows_consorcio = []
    expanded_rows_circulana = []
    grouped = df.groupby('id')

    for cota_id, group in grouped:
        last_row = group.iloc[-1]
        vl_bem = last_row["vl_bem"]
        TX_adm_percent = last_row["TX_adm_%"]
        contracted_period = last_row["contracted_period"]
        embedded_bid_vl = last_row["embedded_bid_vl"]

        vl_devolver = last_row["vl_devolver"]
        data_info = last_row["data_info"]
        seguro_percent = last_row["Seguro_%"]
        year = pd.to_datetime(data_info).year

        FC_already_paid = 0.0
        TX_already_paid = 0.0
        FR_already_paid = 0.0
        TX_already_paid_circulana = 0.0
        rentabilidade_colateral = 0.0
        rentabilidade_colateral_real = 0.0
        rentabilidade_colateral_bem = 0.0
        rentabilidade_bem_contemplacao_real = 0.0
        bem_contemplacao = None
        profits_colateral = 0.0
        profits_bem = 0.0

        for _, row in group.iterrows():
            start_date = pd.to_datetime(row["dt_venda"])
            end_date = min(filter(pd.notna, [
                pd.Timestamp(row["dt_canc"]) if pd.notna(row["dt_canc"]) else None,
                start_date + pd.DateOffset(months=row["contracted_period"]),
                pd.Timestamp.today()
            ]))

            months = pd.date_range(start=start_date, end=end_date, freq='MS')
            max_vl_bem_corrigido = vl_bem

            for month in months:
                canceled = pd.notna(row["dt_canc"]) and month >= pd.Timestamp(row["dt_canc"])
                if canceled:
                    consorcio_dict = expanded_rows_consorcio[-1].copy() if expanded_rows_consorcio else {}
                    circulana_dict = expanded_rows_circulana[-1].copy() if expanded_rows_circulana else {}
                    expanded_rows_consorcio.append(consorcio_dict)
                    expanded_rows_circulana.append(circulana_dict)
                    continue
                contemplated = pd.notna(row["dt_contemplacao"]) and month >= pd.Timestamp(row["dt_contemplacao"])


                vl_bem_corrigido = get_corrected_value(vl_bem, year, month.month, start_date)
                vl_bem_corrigido = max(vl_bem_corrigido, max_vl_bem_corrigido)
                max_vl_bem_corrigido = vl_bem_corrigido
                periodo_restante = contracted_period - ((month - start_date).days // 30)

                fc_monthly = max_vl_bem_corrigido / contracted_period
                tx_monthly = (TX_adm_percent / 100) * max_vl_bem_corrigido / contracted_period
                FC_already_paid += fc_monthly
                TX_already_paid += tx_monthly
                if tx_adm_circulana is not  None:
                    try:
                        tx_adm_circulana_value = tx_adm_circulana * max_vl_bem_corrigido / contracted_period
                        if np.isinf(tx_adm_circulana_value) or np.isnan(tx_adm_circulana_value):
                            raise OverflowError(f"Overflow detected: tx_adm_circulana={tx_adm_circulana}, vl_bem_corrigido={max_vl_bem_corrigido}, contracted_period={contracted_period}")
                    except OverflowError as e:
                        warnings.warn(str(e))
                        tx_adm_circulana_value = np.nan
                else:
                    tx_adm_circulana = TX_adm_percent/100
                    tx_adm_circulana_value = tx_adm_circulana * max_vl_bem_corrigido / periodo_restante
                seguro_monthly = (seguro_percent / 100) * max_vl_bem_corrigido / periodo_restante

                if contemplated:
                    if not bem_contemplacao:
                        bem_contemplacao = max_vl_bem_corrigido
                        # Corrigir bem_contemplacao para dólar na data de contemplação
                        bem_contemplacao_dolar = convert_currency(date=month, amount=bem_contemplacao)

                    valor_colateral = colateral * bem_contemplacao_dolar  # Trabalhar com valores em dólar
                    first_month = (month == months[0])

                    # Para rentabilidade do colateral, use a base inicial se for o primeiro mês ou não composto
                    base_valor_colateral = valor_colateral if (not compounded or first_month) else rentabilidade_colateral
                    rentabilidade_colateral = calcular_rentabilidade_mes(valor=base_valor_colateral, data=month, apys_df=apys_df)
                    profits_colateral += rentabilidade_colateral - valor_colateral

                    # Para rentabilidade do bem, use a base inicial se for o primeiro mês ou não composto
                    base_valor_bem = bem_contemplacao_dolar if (not compounded or first_month) else rentabilidade_colateral_bem
                    rentabilidade_colateral_bem = calcular_rentabilidade_mes(valor=base_valor_bem, data=month, apys_df=apys_df)
                    profits_bem += rentabilidade_colateral_bem - bem_contemplacao_dolar

                    # Converter rentabilidade de volta para real antes de salvar no dataframe
                    rentabilidade_colateral_real = convert_currency(date=month, amount=rentabilidade_colateral, to_currency='brl')
                    rentabilidade_bem_contemplacao_real = convert_currency(date=month, amount=rentabilidade_colateral_bem, to_currency='brl')
                    profits_bem = convert_currency(date=month, amount=profits_bem, to_currency='brl')
                    profits_colateral = convert_currency(date=month, amount=profits_colateral, to_currency='brl')

                common_values = {
                    "id": cota_id,
                    "month": month,
                    "canceled": canceled,
                    "contemplated": contemplated,
                    "vl_bem": max_vl_bem_corrigido if not bem_contemplacao else bem_contemplacao,
                    "vl_devolver": vl_devolver if canceled else 0.0,
                    "contracted_period": contracted_period,
                    "embedded_bid_vl": embedded_bid_vl,
                    "FC_paid": fc_monthly if not canceled else 0.0,
                }

                # Create consorcio dictionary by merging common values with specific ones.
                consorcio_specific = {
                    "TX_adm_paid": tx_monthly if not canceled else 0.0,
                    "FC_paid_%": min(FC_already_paid / vl_bem, 1.0),
                    "TX_paid_%": min(TX_already_paid / ((TX_adm_percent / 100) * vl_bem), 1.0),
                    "FR_paid": FR_already_paid,
                    "seguro_paid": seguro_monthly if not canceled else 0.0,
                    "Seguro_%": seguro_percent,
                    "TX_adm_%": TX_adm_percent/100
                }
                consorcio_dict = {**common_values, **consorcio_specific}
                expanded_rows_consorcio.append(consorcio_dict)

                # Create circulana dictionary by merging common values with specific ones.
                circulana_specific = {
                    "FC_paid_%": min(FC_already_paid / vl_bem, 1.0),
                    "TX_paid_%": min(TX_already_paid_circulana / (tx_adm_circulana * vl_bem), 1.0),
                    "TX_adm_%": tx_adm_circulana,
                    "colateral_w_profits": rentabilidade_colateral_real,
                    "bem_contemplacao_w_profits": rentabilidade_bem_contemplacao_real,
                    "colateral_initial": colateral * bem_contemplacao if contemplated else 0.0,
                    "TX_adm_paid": TX_already_paid_circulana if not canceled else 0.0,
                    "profits_colateral": profits_colateral,
                    "profits_bem": profits_bem
                }
                circulana_dict = {**common_values, **circulana_specific}
                expanded_rows_circulana.append(circulana_dict)

    df_expanded_consorcio = pd.DataFrame(expanded_rows_consorcio)
    df_expanded_circulana = pd.DataFrame(expanded_rows_circulana)
    return df_expanded_consorcio, df_expanded_circulana