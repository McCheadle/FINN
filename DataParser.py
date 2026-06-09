from pathlib import Path
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
from decorators import timer_dec


def strip_until_xml_declaration(s: str) -> str:
    idx = s.find("<?xml")
    if idx == -1:
        raise ValueError("No XML declaration found in string")
    return s[idx:]

def get_xml_tree_from_raw_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")  # or "html.parser" if needed
    
    docs = soup.find_all('xml')
    if (len(docs) != 2):
        return None
    root = docs[-1].decode_contents()
    xbrl = strip_until_xml_declaration(root)
    return ET.fromstring(xbrl)


def extract_dataframes_from_tree(tree :ET.Element):
    contexts = []
    values = []
    DefiningContext = False
    row = []
    for element in tree.iter():
        if not '}' in element.tag:
            return None, None
        element_type = element.tag.split('}')[1]
        if DefiningContext:
            match element_type:
                case "startdate":
                    row.append(element.text)
                case "enddate":
                    row.append(element.text)
                    row.append(datetime.strptime(element.text, "%Y-%m-%d").year)
                    contexts.append(row)
                    row = []
                    DefiningContext = False
                case "instant":
                    row.append("None")
                    row.append(element.text)
                    row.append(datetime.strptime(element.text, "%Y-%m-%d").year)
                    contexts.append(row)
                    row = []
                    DefiningContext = False
                case _:
                    continue
        else:
            match element_type:
                case "context":
                    row.append(element_type)
                    row.append(element.get('id'))
                    DefiningContext = True
                case "unit" | "measure" | "unitdenominator" | "unitnumerator" | "xbrl" | "schemaref" | "divide":
                    continue
                case _:
                    value = element.text
                    if len(str(value)) > 20:
                        continue
                    row.append(element_type)
                    row.append(element.get("contextref"))
                    row.append(value)
                    values.append(row)
                    row = []
    df_Contexts = pd.DataFrame(contexts, columns=["type", "context", "startdate", "enddate", "year"])
    df_Values = pd.DataFrame(values, columns=["type", "context", "value"])

    return df_Contexts, df_Values
                    

def Extract_Contexts_and_Values_from_xbrl(filepath):
    html_file = Path.cwd() / filepath
    tree = get_xml_tree_from_raw_file(html_file)
    if tree is None:
        return None, None
    df_Contexts, df_values = extract_dataframes_from_tree(tree)
    return df_Contexts, df_values


if __name__ == "__main__":
    
    filepath = Path.cwd() / "data/company_data/GBDC/10-K_2025_Q4.html"
    #filepath = Path.cwd() / "data/no_ticker_data/1874999/10-K_2025_Q4.html"
    Extract_Contexts_and_Values_from_xbrl(filepath)

    
