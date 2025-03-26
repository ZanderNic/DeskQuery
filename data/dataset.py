#!/usr/bin/env python 
import pandas as pd

def merge_user():
    pass

def rename_columns(data: pd.DataFrame) -> pd.DataFrame:
    return data.rename(columns={"Name": "userName", 
                                "roomID": "roomId", 
                                "name": "roomName", 
                                "userIdAnonym": "userId", 
                                "at": "bookedAt", 
                                "blockedByIdAnonym": "userId",
                                "deskNumber": "deskId"})

def create_dataset(path: str = "OpTisch_anonymisiert.xlsx") -> pd.DataFrame:
    """This Function denormalizes the excel file to make it easier to handle.

    Args:
        path (str, optional): Path of the excel file. Defaults to "OpTisch_anonymisiert.xlsx".
        num_sheets (int, optional): Number of sheets in the excel file. Defaults to 4.

    Returns:
        pd.DataFrame: A denormalized dataset
    """
    sheets = pd.read_excel(path, sheet_name=None)
    
    # Remove trailing whitespaces from column names
    for data in sheets.values():
        data.columns = data.columns.str.strip()

    # fixed bookings with room
    temp_fixed = pd.merge(sheets["fixedBooking"], sheets["room"], how="left", left_on="roomID", right_on="id").drop(columns=["id_x", "id_y"])
    temp_fixed = pd.merge(sheets["fixedBooking"], sheets["user"], how="left", left_on="blockedByIdAnonym", right_on="ID").drop(columns=["ID"])
    temp_fixed["variableBooking"] = 0
    temp_fixed = rename_columns(temp_fixed)

    # variable bookings with room
    #temp_variable = pd.merge(sheets["variableBooking"], sheets["room"], how="left", left_on="roomID", right_on="id")
    temp_variable = pd.merge(sheets["variableBooking"], sheets["user"], how="left", left_on="userIdAnonym", right_on="ID").drop(columns=["ID"])
    temp_variable["variableBooking"] = 1
    temp_variable = rename_columns(temp_variable)

    data = pd.concat([temp_fixed, temp_variable], axis=0)

    return data

data = create_dataset()
data.to_csv("OpTisch.csv")