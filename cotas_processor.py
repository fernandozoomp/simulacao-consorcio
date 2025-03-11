import numpy as np
import warnings
import pandas as pd
from load_functions import convert_currency, calcular_rentabilidade_mes, find_corrected_values, aplication_cdi

def expandir_cotas(df, colateral=0.4, apys_df=None, compounded=False, tx_adm_circulana=None):
    """Expand the DataFrame for each month."""
    expanded_rows_consorcio = []
    expanded_rows_circulana = []
    grouped = df.groupby('id')

    for cota_id, group in grouped:
        last_row = group.iloc[-1]
        vl_bem = last_row["vl_bem"]
        TX_adm_percent = last_row["TX_adm_%"]
        start_date = pd.to_datetime(last_row["dt_venda"])
        contracted_period = min(last_row["contracted_period"], (pd.Timestamp.today() - start_date).days // 30)
        embedded_bid_vl = last_row["embedded_bid_vl"]
        vl_devolver = last_row["vl_devolver"]
        seguro_percent = last_row["Seguro_%"]
        if seguro_percent is None or np.isnan(seguro_percent):
            seguro_percent = 0.0
        dt_cancel = pd.to_datetime(last_row["dt_canc"])
        year = pd.to_datetime(start_date).year
        dt_contemplacao = pd.to_datetime(last_row["dt_contemplacao"])

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
        profits_colateral_dolar = 0.0
        profits_bem_dolar = 0.0
        consorcio_cdi = 0.0
        profits_consorcio_cdi = 0.0
        first_month = True
        bem_contemplacao_dolar_show = 0.0
        total_seguro = 0.0

        end_date = min(filter(pd.notna, [
            pd.Timestamp(dt_cancel) if pd.notna(dt_cancel) else None,
            start_date + pd.DateOffset(months=contracted_period),
            pd.Timestamp.today()
        ]))

        months = pd.date_range(start=start_date, end=end_date, freq='MS')
        max_vl_bem_corrigido = vl_bem

        for month in months:
            canceled = pd.notna(dt_cancel) and month >= pd.Timestamp(dt_cancel)
            if canceled:
                continue
            contemplated = pd.notna(dt_contemplacao) and month >= pd.Timestamp(dt_contemplacao)

            vl_bem_corrigido = find_corrected_values(vl_bem, year, month.year)
            vl_bem_corrigido = max(vl_bem_corrigido, max_vl_bem_corrigido)
            max_vl_bem_corrigido = vl_bem_corrigido
            if not canceled:
                fc_monthly = max_vl_bem_corrigido / contracted_period
                tx_monthly = (TX_adm_percent / 100) * max_vl_bem_corrigido / contracted_period
                fr_monthly = max_vl_bem_corrigido * (last_row["FR_%"] / 100) / contracted_period
            else:
                fc_monthly = 0.0
                tx_monthly = 0.0
                fr_monthly = 0.0
                tx_adm_circulana = 0.0
                seguro_percent = 0.0
            FC_already_paid += fc_monthly
            TX_already_paid += tx_monthly
            FR_already_paid += fr_monthly
            if tx_adm_circulana is not None:
                try:
                    tx_adm_circulana_value = tx_adm_circulana * max_vl_bem_corrigido / contracted_period
                    if np.isinf(tx_adm_circulana_value) or np.isnan(tx_adm_circulana_value):
                        raise OverflowError(f"Overflow detected: tx_adm_circulana={tx_adm_circulana}, vl_bem_corrigido={max_vl_bem_corrigido}, contracted_period={contracted_period}")
                except OverflowError as e:
                    warnings.warn(str(e))
                    tx_adm_circulana_value = np.nan
            else:
                tx_adm_circulana = TX_adm_percent / 100
                tx_adm_circulana_value = tx_adm_circulana * max_vl_bem_corrigido / contracted_period
            TX_already_paid_circulana += tx_adm_circulana_value
            seguro_monthly = (float(seguro_percent) / 100) * max_vl_bem_corrigido / contracted_period
            total_seguro += seguro_monthly

            if contemplated:
                if not bem_contemplacao:
                    bem_contemplacao = max_vl_bem_corrigido
                    bem_contemplacao_dolar = convert_currency(date=month, amount=bem_contemplacao)

                valor_colateral = colateral * bem_contemplacao_dolar
                if consorcio_cdi == 0.0:
                    consorcio_cdi = bem_contemplacao
                else:
                    consorcio_cdi = aplication_cdi(consorcio_cdi, month)
                profits_consorcio_cdi += consorcio_cdi - bem_contemplacao

                base_valor_colateral = valor_colateral if (not compounded or first_month) else rentabilidade_colateral
                rentabilidade_colateral = calcular_rentabilidade_mes(valor=base_valor_colateral, data=month, apys_df=apys_df)
                profits_colateral_dolar += rentabilidade_colateral - valor_colateral

                base_valor_bem = bem_contemplacao_dolar if (not compounded or first_month) else rentabilidade_colateral_bem
                rentabilidade_colateral_bem = calcular_rentabilidade_mes(valor=base_valor_bem, data=month, apys_df=apys_df)
                profits_bem_dolar += rentabilidade_colateral_bem - bem_contemplacao_dolar

                rentabilidade_colateral_real = convert_currency(date=month, amount=rentabilidade_colateral, to_currency='brl')
                rentabilidade_bem_contemplacao_real = convert_currency(date=month, amount=rentabilidade_colateral_bem, to_currency='brl')
                profits_bem = convert_currency(date=month, amount=profits_bem_dolar, to_currency='brl')
                profits_colateral = convert_currency(date=month, amount=profits_colateral_dolar, to_currency='brl')
                bem_contemplacao_dolar_show = convert_currency(date=month, amount=bem_contemplacao_dolar+profits_bem_dolar, to_currency='brl')
                if not first_month:
                    first_month = False

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

            consorcio_specific = {
                "TX_adm_paid": TX_already_paid,
                "FC_paid_%": min(FC_already_paid / vl_bem, 1.0),
                "FC_paid_monthly": fc_monthly,
                "TX_paid_%": min(TX_already_paid / ((TX_adm_percent / 100) * vl_bem), 1.0),
                "FR_paid": FR_already_paid,
                "FR_paid_%": min(FR_already_paid / (last_row["FR_%"] / 100 * vl_bem), 1.0),
                "FR_paid_monthly": fr_monthly,
                "seguro_paid": seguro_monthly,
                "Seguro_%": seguro_percent,
                "TX_adm_%": TX_adm_percent / 100,
                "consorcio_w_profits": consorcio_cdi,
                "profits_consorcio": profits_consorcio_cdi,
                "TX_adm_monthly": tx_monthly,
                "seguro_monthly": seguro_monthly,
            }
            consorcio_dict = {**common_values, **consorcio_specific}
            expanded_rows_consorcio.append(consorcio_dict)

            circulana_specific = {
                "FC_paid_%": min(FC_already_paid / vl_bem, 1.0),
                "TX_paid_%": min(TX_already_paid_circulana / (tx_adm_circulana * vl_bem), 1.0),
                "TX_adm_%": tx_adm_circulana,
                "colateral_w_profits": rentabilidade_colateral_real,
                "bem_contemplacao_w_profits": rentabilidade_bem_contemplacao_real,
                "colateral_initial": colateral * bem_contemplacao if contemplated else 0.0,
                "TX_adm_paid": TX_already_paid_circulana if not canceled else 0.0,
                "TX_adm_monthly": tx_adm_circulana_value,
                "profits_colateral": profits_colateral,
                "profits_bem": profits_bem,
                "bem_contemplacao_dolar": bem_contemplacao_dolar_show,
                "bem_contemplacao_dolar_colateral": bem_contemplacao_dolar_show * colateral,
            }
            circulana_dict = {**common_values, **circulana_specific}
            expanded_rows_circulana.append(circulana_dict)

    df_expanded_consorcio = pd.DataFrame(expanded_rows_consorcio)
    df_expanded_circulana = pd.DataFrame(expanded_rows_circulana)
    return df_expanded_consorcio, df_expanded_circulana