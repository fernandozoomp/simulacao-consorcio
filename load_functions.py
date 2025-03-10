import pandas as pd
import json
import os
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build

    
def create_credentials_file():
    credentials_data = os.environ['CREDENTIALS']
    
    if not credentials_data:
        raise ValueError("A variável de ambiente 'CREDENTIALS' está vazia ou não foi definida.")
    try:
        json.loads(credentials_data)
    except json.JSONDecodeError:
        raise ValueError("O conteúdo da variável de ambiente 'CREDENTIALS' não é um JSON válido.")

    with open('credentials.json', 'w') as f:
        f.write(credentials_data)

    credentials_path = './credentials.json'
    
    with open(credentials_path, 'r') as f:
        credentials = f.read()
    
    return credentials

SCOPES = ["https://www.googleapis.com/auth/drive"]
creds = service_account.Credentials.from_service_account_info(json.loads(create_credentials_file()), scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

def get_folder_id(drive_service, folder_name):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    results = drive_service.files().list(
        q=query,
        fields="files(id, name)"
    ).execute()
    folders = results.get('files', [])
    if not folders:
        print(f"Pasta '{folder_name}' não encontrada.")
        return None
    return folders[0]['id']

def fetch_file_from_google_drive(drive_service, file_name, destination, folder_id=None):
    query = f"name='{file_name}'"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    results = drive_service.files().list(
        q=query,
        fields="files(id, name)"
    ).execute()
    items = results.get('files', [])
    
    if not items:
        print("Arquivo não encontrado.")
        return False

    file_id = items[0]['id']
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.FileIO(destination, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"Download {int(status.progress() * 100)}% concluído.")

def load_and_preprocess_apys(filepath):
    """Load and preprocess the APYs DataFrame."""
    if not os.path.exists(filepath):
        folder_id = get_folder_id(drive_service, "Base_simulacao")
        fetch_file_from_google_drive(drive_service, filepath, filepath, folder_id=folder_id)
    apys_df = pd.read_csv(filepath)
    apys_df.drop(labels=['APY_REWARD', 'APY_BASE', 'TVL'], axis=1, inplace=True)
    apys_df["DATE"] = pd.to_datetime(apys_df["DATE"]).dt.date
    return apys_df
def path_dict_to_df(type):
    """Reads all files in the given dictionary and concatenates them into a single DataFrame."""
    dict_path = {
        'aave': 'apys_aave_v2_USDC.csv',
        'compound': 'apys_compound_USDC.csv',
        'uniswap': 'apys_uniswap_USDC.csv',
        'balancer': 'apys_balancer_USDC.csv',
    }
    df = load_and_preprocess_apys(dict_path[type])
    return df


def load_and_preprocess_grupo(filepath, number_elements=None):
    if not os.path.exists(filepath):
        folder_id = get_folder_id(drive_service, "Base_simulacao")
        fetch_file_from_google_drive(drive_service, filepath, filepath, folder_id=folder_id)
    if number_elements:
        df = pd.read_csv(filepath, nrows=number_elements, low_memory=False)
    else:
        df = pd.read_csv(filepath, low_memory=False)
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
    
def get_corrected_value(vl_bem_atual, year, month, data_entrada):
    vl_bem_atual = float(vl_bem_atual)
    loader = DataFrameLoader()
    df_correction = loader.load_and_preprocess_correction('FIPE-GRUPO-655-FIPE.csv')
    # Find exact match or closest value
    item = df_correction[df_correction[f'valor_{year}'] == vl_bem_atual]
    if item.empty:
        closest_index = (df_correction[f'valor_{year}'] - vl_bem_atual).abs().idxmin()
        item = df_correction.loc[[closest_index]]  # Ensure item is a DataFrame

    # Calculate new date and corresponding year
    data_entrada = pd.to_datetime(data_entrada)
    data_corrigida = data_entrada + pd.DateOffset(months=month)
    year_corrigido = data_corrigida.year

    # Retrieve corrected value and ensure it's returned as a float
    valor_corrigido = item[f'valor_{year_corrigido}'].values[0]
    return float(valor_corrigido)

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
        if not os.path.exists(filepath):
            folder_id = get_folder_id(drive_service, "Base_simulacao")
            fetch_file_from_google_drive(drive_service, filepath, filepath, folder_id=folder_id)
        if self.df_usd is None:
            self.df_usd = pd.read_csv(filepath)
            self.df_usd.drop(columns=['Último', 'Máxima', 'Mínima', 'Var%', 'Vol.'], inplace=True)
            self.df_usd.columns = ['date', 'usd']
            self.df_usd['date'] = pd.to_datetime(self.df_usd['date'], format='%d-%m-%Y', dayfirst=True)
            self.df_usd['usd'] = self.df_usd['usd'].str.replace(',', '.').astype(float)
            self.df_usd['usd'] = self.df_usd['usd'].apply(lambda x: x / 10)
        return self.df_usd

    def load_and_preprocess_correction(self, filepath):
        if not os.path.exists(filepath):
            folder_id = get_folder_id(drive_service, "Base_simulacao")
            fetch_file_from_google_drive(drive_service, filepath, filepath, folder_id=folder_id)
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

