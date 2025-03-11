import pandas as pd
import matplotlib.pyplot as plt
def load_and_preprocess_apys(filepath):
    """Load and preprocess the APYs DataFrame."""
    apys_df = pd.read_csv(filepath)
    apys_df.drop(labels=['APY_REWARD', 'APY_BASE', 'TVL'], axis=1, inplace=True)
    apys_df["DATE"] = pd.to_datetime(apys_df["DATE"]).dt.date
    return apys_df

def path_dict_to_df(type):
    """Reads all files in the given dictionary and concatenates them into a single DataFrame."""
    dict_path = {
        'aave': 'apys_aave_v2_USDC.csv',
        'compound': 'apys_compound_USDC.csv',
        'uniswap': 'apys_uniswap_v3-USDC-USDT.csv',
        'balancer': 'apys_balancer_v3_USDC.csv',
    }
    df = load_and_preprocess_apys(dict_path[type])
    return df



def aplication_cdi(amount, date_month):
    """
    Calculates the return based on the CDI for the month of the given date.
    If the exact month is not available, uses the most recent month before the given date.

    Parameters:
    amount (float): The initial investment value.
    date_month (np.datetime64): The date to determine the month and year for CDI calculation.

    Returns:
    float: The calculated return based on the CDI for the month.
    """
    df_cdi = DataFrameLoader.load_and_preprocess_cdi()
    if not isinstance(date_month, pd.Timestamp):
        date_month = pd.to_datetime(date_month)
        
    # Check for an exact match first
    df_exact = df_cdi[df_cdi['date_month'] == date_month]
    if not df_exact.empty:
        cdi = float(df_exact['cdi'].iloc[0])
    else:
        # Find the most recent month before the given date
        df_before = df_cdi[df_cdi['date_month'] < date_month]
        if df_before.empty:
            raise ValueError("No CDI data available for the given date or before.")
        
        df_before_sorted = df_before.sort_values('date_month')
        cdi = float(df_before_sorted.iloc[-1]['cdi'])
        
    return amount * (1 + cdi*0.85)


def load_and_preprocess_grupo(filepath, number_elements=None):
    if number_elements:
        df = pd.read_csv(filepath, nrows=number_elements, low_memory=False)
    else:
        df = pd.read_csv(filepath, low_memory=False)

    df.drop(columns=['id_quotas_santander', 'cd_grupo', 'cd_cota', 'cd_produto', 'nm_situ_entrega_bem', 'created_at', 'is_processed', 'cd_versao_cota', 'cd_tipo_pessoa', 'pz_comercializacao', 'vl_lance_proprio'], inplace=True)
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
        "qt_pc_lance": "qt_parc_lance",
    }
    df = df.rename(columns=rename_map)
    
    df['id'] = df['id'].astype(int)
    date_columns = ['dt_canc', 'dt_contemplacao', 'data_info', 'dt_entrega']
    for col in date_columns:
        df[col] = pd.to_datetime(df[col]).dt.date
    # Ensure 'data_info' is in datetime format
    df['data_info'] = pd.to_datetime(df['data_info'])

    # Group by 'id' and get the row with the most recent 'data_info' for each group
    df_most_recent = df.loc[df.groupby('id')['data_info'].idxmax()]

    return df_most_recent

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
    return monthly_data["APY"].mean() if not monthly_data.empty else df["APY"].loc[0], monthly_data["GAS_PRICE_MED"].mean()

def calcular_rentabilidade_mes(valor, data, apys_df=None, type='circulana'):
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
        apy, gas_fee = get_apy_by_month(data, apys_df)
        
        if apy is not None:
            apym = (1 + apy / 100) ** (1/12) - 1
            return valor * (1 + apym) - gas_fee
        else:
            return valor * (1 + 0.0007) - gas_fee
    else:
        return valor

def find_corrected_values(given_value, last_known_year, target_year):
    # Identify the year columns
    loader = DataFrameLoader()
    df_correction = loader.load_and_preprocess_correction('FIPE-GRUPO-655-FIPE.csv')
    year_columns = [col for col in df_correction.columns if col.startswith("valor_")]
    closest_match = None
    closest_diff = float('inf')
    closest_percentage = None
    closest_idx = None

    # Find the row where the given value matches any of the percentual_inicial or percentual_final
    for idx, row in df_correction.iterrows():
        percentual_inicial = float(row['percentual_inicial'].strip('%').replace(',', '.')) / 100
        percentual_final = float(row['percentual_final'].strip('%').replace(',', '.')) / 100

        for year in year_columns:
            if int(year.split('_')[1]) == last_known_year:
                full_car_value_initial = given_value / percentual_inicial
                full_car_value_final = given_value / percentual_final

                diff_initial = abs(full_car_value_initial * percentual_inicial - given_value)
                diff_final = abs(full_car_value_final * percentual_final - given_value)

                if diff_initial < 1e-6:
                    used_percentage = percentual_inicial
                    return {year: df_correction.at[idx, year] * used_percentage for year in year_columns if int(year.split('_')[1]) >= 2020}[f"valor_{target_year}"]
                elif diff_final < 1e-6:
                    used_percentage = percentual_final
                    return {year: df_correction.at[idx, year] * used_percentage for year in year_columns if int(year.split('_')[1]) >= 2020}[f"valor_{target_year}"]
                else:
                    min_diff = min(diff_initial, diff_final)
                    if min_diff < closest_diff:
                        closest_diff = min_diff
                        closest_match = full_car_value_initial if diff_initial < diff_final else full_car_value_final
                        closest_percentage = percentual_inicial if diff_initial < diff_final else percentual_final
                        closest_idx = idx

    # If no exact match, use the closest match
    if closest_match is not None:
        return {year: df_correction.at[closest_idx, year] * closest_percentage for year in year_columns if int(year.split('_')[1]) >= 2020}[f"valor_{target_year}"]

    return None  # Return None if no match is found

class DataFrameLoader:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DataFrameLoader, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self.df_usd = None
        self.df_correction = None

    def load_and_preprocess_usd_brl(self, filepath):
        if self.df_usd is None:
            self.df_usd = pd.read_csv(filepath)
            self.df_usd.drop(columns=['Último', 'Máxima', 'Mínima', 'Var%', 'Vol.'], inplace=True)
            self.df_usd.columns = ['date', 'usd']
            self.df_usd['date'] = pd.to_datetime(self.df_usd['date'], format='%d-%m-%Y', dayfirst=True)
            self.df_usd['usd'] = self.df_usd['usd'].str.replace(',', '.').astype(float)
            self.df_usd['usd'] = self.df_usd['usd'].apply(lambda x: x / 10)
        return self.df_usd

    def load_and_preprocess_correction(self, filepath):
        if self.df_correction is None:
            self.df_correction = pd.read_csv(filepath)
            for year in range(2020, 2026):
                self.df_correction[f'valor_{year}'] = (
                    self.df_correction[f'valor_{year}']
                    .astype(str)
                    .str.replace('.', '', regex=False)
                    .str.replace(',', '.', regex=False)
                    .astype(float)
                )
            self.df_correction['inicio_grupo'] = pd.to_datetime(self.df_correction['inicio_grupo'])
            self.df_correction['termino_grupo'] = pd.to_datetime(self.df_correction['termino_grupo'])
        return self.df_correction
    def load_and_preprocess_cdi(filepath = 'cdi.csv'):
        """Load and preprocess the CDI DataFrame."""
        df_cdi = pd.read_csv(filepath)
        df_cdi.rename(columns={'Data': 'date_month', 'Taxa de juros - CDI / Over - acumulada no mês': 'cdi'}, inplace=True)
        df_cdi['cdi'] = df_cdi['cdi'].str.replace(',', '.').astype(float)/100
        df_cdi['date_month'] = pd.to_datetime(df_cdi['date_month'], format='%Y-%m')
        df_cdi = df_cdi[df_cdi['date_month'] >= pd.Timestamp('2020-01')].reset_index(drop=True)
        return df_cdi

def correct_real(initial_date, initial_amount=1.0, final_date=None, correction_type='daily'):
    """
    Calculates the corrected value of an initial investment in BRL over time based on USD variation.

    Parameters:
    - initial_date (str or datetime): The start date of the investment.
    - initial_amount (float): The initial amount in BRL.
    - final_date (str or datetime, optional): The end date of the investment.
    - correction_type (str): 'daily' for daily correction, 'monthly' for monthly correction (same day each month).

    Returns:
    - Final corrected value (float)
    - Final date reached (datetime)
    """
    loader = DataFrameLoader()
    df_usd = loader.load_and_preprocess_usd_brl('USD_BRL.csv')
    # Convert input dates to datetime
    initial_date = pd.to_datetime(initial_date, format='%d-%m-%Y')
    if final_date:
        final_date = pd.to_datetime(final_date, format='%d-%m-%Y')

    # Ensure we start from the exact given date
    df_filtered = df_usd[df_usd['date'] >= initial_date].copy()
    
    if df_filtered.empty:
        raise ValueError("No data available for the given date. Choose an earlier date.")

    # Start with initial amount
    amount = initial_amount

    if correction_type == 'daily':
        if final_date:
            df_final = df_usd[df_usd['date'] <= final_date].copy()
            if df_final.empty:
                raise ValueError("No data available for the given final date. Choose a later date.")
            final_usd = df_final.iloc[-1]['usd']
        else:
            final_usd = df_filtered.iloc[-1]['usd']
        current_amount = amount * (final_usd / df_filtered.iloc[0]['usd'])

    elif correction_type == 'monthly':
        if final_date:
            final_year = final_date.year
            final_month = final_date.month
            df_final = df_usd[(df_usd['date'].dt.year == final_year) & (df_usd['date'].dt.month == final_month)]
            if df_final.empty:
                raise ValueError("No data available for the given final date. Choose a later date.")
            final_usd = df_final['usd'].mean()
        else:
            final_usd = df_filtered['usd'].mean()
        current_amount = amount * (final_usd / df_filtered.iloc[0]['usd'])

    return round(current_amount, 4)

def convert_currency(date, amount, to_currency='usd'):
    """
    Converts an amount between BRL and USD based on the exchange rate of a given date.

    Parameters:
    - date (str or datetime): The date for the conversion.
    - amount (float): The amount to be converted.
    - to_currency (str): 'usd' to convert BRL → USD, 'brl' to convert USD → BRL.

    Returns:
    - Converted amount (float).
    """
    loader = DataFrameLoader()
    df_usd = loader.load_and_preprocess_usd_brl('usd-variation.csv')

    date = pd.to_datetime(date, format='%d-%m-%Y')

    # Find the closest available date with exchange data
    df_filtered = df_usd[df_usd['date'] <= date]
    if df_filtered.empty:
        raise ValueError("No exchange rate data available for the given date or earlier.")

    exchange_rate = df_filtered.iloc[-1]['usd']  # Latest available rate before or on the given date

    if to_currency == 'usd':
        return round(amount / exchange_rate, 4)  # BRL → USD
    elif to_currency == 'brl':
        return round(amount * exchange_rate, 4)  # USD → BRL
    else:
        raise ValueError("Invalid currency conversion type. Use 'usd' or 'brl'.")

import numpy as np
import pandas as pd
import warnings

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


if __name__ == "__main__":
    # Input Parameters
    ## places of interest: aave, compound, uniswap, balancer
    rentability_type = "circulana"
    place_of_interest = "aave"
    percentual_colateral = 0.4
    compounded = False
    # Load Data
    apys_df = path_dict_to_df(place_of_interest)
    df_grupo = load_and_preprocess_grupo('santander_cotas_pre_grupo_md_cota655_202502211443.csv')

    # Process Data
    df_expanded_consorcio, df_expanded_circulana = expandir_cotas(
        df_grupo,
        colateral=percentual_colateral, 
        apys_df=apys_df,
        tx_adm_circulana=0.05
    )