from io import StringIO

import requests
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
import re


CIK = "0000320193"


def get_filings(cik):
    url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()  # Raise an exception for HTTP errors
    return response.json()

def pretty_print_json(json_data):
    print(json.dumps(json_data, indent=4))

def dump_json_to_file(json_data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=4)

def print_from_json(filings, key, form_type):
    form_indices = [i for i, form in enumerate(filings["form"]) if form == form_type]
    print(f"Indices of {form_type} filings: {form_indices}")
    for i in form_indices:
        print(filings[key][i])


def main():
    # cached_file = "filings.json"
    # with open(cached_file, 'r', encoding='utf-8') as f:
    #     json_data = json.load(f)
    # filings = json_data.get("filings", {}).get("recent", {})
    # keys = filings.keys()
    # print(f"Keys in filings: {keys}")
    # for i, key in enumerate(keys):
    #     #print the amount of elements in this part of filings
    #     print(f"{key}: {len(filings[key])}")
    
    # K10Indices = [i for i, form in enumerate(filings["form"]) if form == "10-K"]


    # print_from_json(filings, "form", "10-K")
    # print_from_json(filings, "core_type", "10-K")
    # print_from_json(filings, "isXBRL", "10-K")
    # print_from_json(filings, "size", "10-K")
    pass


HEADERS = {
    'User-Agent': "Leo (leo.caers@gmail.com)"
}

EDGAR_ARCHIVES = "https://www.sec.gov/Archives/"
EDGAR_INDEX_URL = "https://www.sec.gov/Archives/edgar/full-index/"
def get_form_index(year, quarter):
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

def extract_form_type_from_dataframe(df: pd.DataFrame, form_type: str) -> pd.DataFrame:
    return df[df["form_type"] == form_type]


if __name__ == "__main__":
    #response = get_form_index(2024, 3)
    #df = parse_form_idx(response)
    #df = extract_form_type_from_dataframe(df, "10-K")
    #save df into csv file
    #df.to_csv("form_index_2024_Q3.csv", index=False)
    df = pd.read_csv("form_index_2024_Q3.csv")

    #print all generic information about the dataframe
    head = df.head(5)
    tail = df.tail(5)
    print(head)
    print(tail)
    df.info()
    df.describe()
    print(df.shape)
    print(df.columns)


    file_url = f"{EDGAR_ARCHIVES}/{df.iloc[0]['file_name']}"
    response = requests.get(file_url, headers=HEADERS)
    response.raise_for_status()

    with open("output.txt", "w", encoding="utf-8") as f:
        f.write(response.text)

    # Save as .html
    with open("output.html", "w", encoding="utf-8") as f:
        f.write(response.text)


