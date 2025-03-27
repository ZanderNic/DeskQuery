#!/usr/bin/env python 
import pandas as pd

def rename_columns(data: pd.DataFrame) -> pd.DataFrame:
    """
    Rename specific columns in the DataFrame for consistency.
    """
    column_mapping = {
        "Name": "userName",
        "roomID": "roomId",
        "name": "roomName",
        "userIdAnonym": "userId",
        "at": "bookedAt",
        "blockedByIdAnonym": "userId",
        "deskNumber": "deskId",
        "id": "bookingID"
    }
    return data.rename(columns=column_mapping)

def create_dataset(path: str = "OpTisch_anonymisiert.xlsx") -> pd.DataFrame:
    """This Function denormalizes the excel file to make it easier to handle.

    Args:
        path (str, optional): Path of the excel file. Defaults to "OpTisch_anonymisiert.xlsx".
        num_sheets (int, optional): Number of sheets in the excel file. Defaults to 4.

    Returns:
        pd.DataFrame: A denormalized dataset
    """
    # Load all sheets from the Excel file into a dictionary of DataFrames
    sheets = pd.read_excel(path, sheet_name=None)
    
    # Strip trailing whitespaces from all column names
    for _, df in sheets.items():
        df.columns = df.columns.str.strip()

    # fixed bookings with room
    data_fixed = pd.merge(sheets["fixedBooking"], sheets["room"], how="left", left_on="roomID", right_on="id").drop(columns=["id_x", "id_y"])
    data_fixed = pd.merge(sheets["fixedBooking"], sheets["user"], how="left", left_on="blockedByIdAnonym", right_on="ID").drop(columns=["ID"])
    data_fixed["variableBooking"] = 0 # Indicate fixed bookings
    data_fixed = rename_columns(data_fixed)

    # variable bookings with room
    #data_variable = pd.merge(sheets["variableBooking"], sheets["room"], how="left", left_on="roomID", right_on="id")
    data_variable = pd.merge(sheets["variableBooking"], sheets["user"], how="left", left_on="userIdAnonym", right_on="ID").drop(columns=["ID"])
    data_variable["variableBooking"] = 1 # Indicate variable bookings
    data_variable = rename_columns(data_variable)

    data = pd.concat([data_fixed, data_variable], axis=0)

    return data

if __name__ == "__main__":
    data = create_dataset()
    data.to_csv("OpTisch.csv", index=False)  # Save dataset to CSV without index
