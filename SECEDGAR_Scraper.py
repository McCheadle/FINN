from io import StringIO

import requests
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
import re
import xml.etree.ElementTree as ET
from tqdm import tqdm
import time
from DataParser import Extract_Contexts_and_Values_from_xbrl

HEADERS = {
    'User-Agent': "Leo (leo.caers@gmail.com)"
}
EDGAR_ARCHIVES = "https://www.sec.gov/Archives/"
EDGAR_INDEX_URL = "https://www.sec.gov/Archives/edgar/full-index/"


def fetch_form_index(year, quarter):
    if (year < 1993) or (year > 2025):
        raise ValueError("Year must be between 1993 and 2025")
    if (quarter < 1) or (quarter > 4):
        raise ValueError("Quarter must be between 1 and 4")
    index_url = f"{EDGAR_INDEX_URL}/{year}/QTR{quarter}/form.idx"
    response = requests.get(index_url, headers=HEADERS)
    response.raise_for_status()
    return response.text

def parse_form_idx(text: str) -> pd.DataFrame:
    lines = text.splitlines()
    # find start of data
    start = 0
    for i, line in enumerate(lines):
        if re.match(r"-{5,}", line):  # dashed separator line
            start = i + 1
            break

    rows = []
    for line in lines[start:]:
        if not line.strip():
            continue

        # split on 2+ spaces (SEC standard behavior)
        parts = re.split(r"\s{2,}", line.strip())

        if len(parts) != 5:
            continue  # skip malformed rows safely

        rows.append(parts)

    df = pd.DataFrame(rows, columns=[
        "form_type",
        "company_name",
        "cik",
        "date_filed",
        "file_name"
    ])

    df["cik"] = df["cik"].astype(str)
    return df

def prune_forms_not_of_type(df: pd.DataFrame, form_type: str) -> pd.DataFrame:
    return df[df["form_type"] == form_type]



def Lookup_Ticker_from_CIK(CIK, df:pd.DataFrame):
    match = df.loc[df["cik_str"] == CIK, "ticker"]
    return match.iloc[0] if not match.empty else None

ticker_lookup_file = "data/company_tickers.json"

def main():
    YEAR = 2025
    QUARTER = 2
    FORM_TYPE = "10-K"
    request_rate = 0.1
    CIK_Lookup_df = pd.read_json(ticker_lookup_file).T
    MAX_KBYTES = 50000
    BLACKLIST = [] 
    BLACKLIST_FILE = Path("data/blacklisted_CIKs.txt")

    with open(BLACKLIST_FILE, 'r') as f:
        BLACKLIST = [line.strip() for line in f if line.strip()]

    save_path = Path(f"data/form_indexes/form_index_{FORM_TYPE}_{YEAR}_Q{QUARTER}.csv")
    if save_path.exists():
        df = pd.read_csv(save_path)
    else:
        #get the form index of a specific year and quarter
        response = fetch_form_index(YEAR, QUARTER)
        df = parse_form_idx(response)
        #extract only the 10-K forms from the index
        df = prune_forms_not_of_type(df, FORM_TYPE)
        #cache the index in storage
        df.to_csv(save_path, index=False)
    
    progress_bar = tqdm(df.iterrows(), total=len(df), desc=f"Scraping {FORM_TYPE}'s")
    for index, row in progress_bar:
        start = time.perf_counter()

        CIK = int(row['cik'])
        ticker = Lookup_Ticker_from_CIK(CIK, CIK_Lookup_df)
        if str(CIK) in BLACKLIST:
            continue

        if ticker is not None:
            progress_bar.set_description(f"Scraping {ticker}", refresh=True)
            local_file_dir = Path(f"data/company_data/{ticker}/")
        else:
            progress_bar.set_description(f"Scraping {CIK}", refresh=True)
            local_file_dir = Path(f"data/no_ticker_data/{CIK}/")
        
        local_file_dir.mkdir(parents=True, exist_ok=True)
        local_file_path = local_file_dir / f"{FORM_TYPE}_{YEAR}_Q{QUARTER}.html"

        if not local_file_path.exists():
            form_file_path = row['file_name']
            file_url = f"{EDGAR_ARCHIVES}/{form_file_path}"
            response = requests.get(file_url, headers=HEADERS)
            response.raise_for_status()
            with open(local_file_path, "w", encoding="utf-8") as f:
                f.write(response.text)

        contexts_file_path = local_file_dir / f"Contexts_{FORM_TYPE}_{YEAR}_Q{QUARTER}.csv"
        values_file_path = local_file_dir / f"Values_{FORM_TYPE}_{YEAR}_Q{QUARTER}.csv"

        if not (contexts_file_path.exists() and values_file_path.exists()):
            size_bytes = local_file_path.stat().st_size
            if size_bytes / 1024 > MAX_KBYTES:
                continue

            try:
                df_Contexts, df_Values = Extract_Contexts_and_Values_from_xbrl(local_file_path)
                if df_Contexts is None or df_Values is None:
                    with open(BLACKLIST_FILE, 'a') as f:
                        f.write(f"{CIK}\n")
                    BLACKLIST.append(CIK)
                    continue
                df_Contexts.to_csv(contexts_file_path, index=False)
                df_Values.to_csv(values_file_path, index=False)
            except Exception:
                with open(BLACKLIST_FILE, 'a') as f:
                        f.write(f"{CIK}\n")
                BLACKLIST.append(CIK)
                continue

        else:
            continue

        elapsed_time = time.perf_counter() - start
        remaining = request_rate - elapsed_time
        if (remaining > 0):
            time.sleep(remaining)

    


        
        
        



if __name__ == "__main__":
    main()


