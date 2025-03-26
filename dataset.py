#!/usr/bin/env python 
import pandas as pd

def create_dataset(path: str = "OpTisch_anonymisiert.xlsx", num_sheets: int = 4) -> pd.DataFrame:
    """This Function denormalizes the excel file to make it easier to handle.

    Args:
        path (str, optional): Path of the excel file. Defaults to "OpTisch_anonymisiert.xlsx".
        num_sheets (int, optional): Number of sheets in the excel file. Defaults to 4.

    Returns:
        pd.DataFrame: A denormalized dataset
    """
    data = pd.read_excel(path, sheet_name=list(range(num_sheets)))
    temp = data[0]
    merge_keys = [("id", "roomID"), ("deskNumber", "deskId"), ("userIdAnonym", "ID")]
    for sheet_idx, keys in enumerate(merge_keys, start=1):
        temp = pd.merge(temp, data[sheet_idx], left_on=keys[0], right_on=keys[1])

    temp = temp.drop(columns=["ID", "deskId", "id_x", "id_y", "id"])
    # Remove trailing whitespaces
    temp.columns = temp.columns.str.strip()
    temp = temp.rename(columns={"Name": "userName", "name": "roomName", "userIdAnonym": "userId", "at": "bookedAt"})
    return temp

data = create_dataset()
data.to_csv("OpTisch.csv")