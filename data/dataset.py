#!/usr/bin/env python 
import pandas as pd
import numpy as np

pd.set_option('future.no_silent_downcasting', True)

def rename_columns(data: pd.DataFrame) -> pd.DataFrame:
    """
    Rename specific columns in the DataFrame for consistency.
    """
    column_mapping = {
        "Name": "userName",
        "roomID": "roomId",
        "name": "roomName",
        "userIdAnonym": "userId",
        "at": "blockedFrom",
        "blockedByIdAnonym": "userId",
        "id": "bookingId"
    }
    return data.rename(columns=column_mapping)

def get_desk_room_mapping(fixedBooking_sheet: pd.DataFrame, room_sheet: pd.DataFrame) -> pd.DataFrame:
    desk_room_mapping = fixedBooking_sheet[["bookingId", "deskNumber", "roomId"]].sort_values(by=["roomId", "deskNumber"]).rename(columns={"bookingId": "deskId"}).astype(int)
    desk_room_mapping = pd.merge(desk_room_mapping, room_sheet, how="left", left_on="roomId", right_on="bookingId").drop(columns="bookingId").set_index("deskId")
    desk_room_mapping.index.name = "deskId"

    return desk_room_mapping

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
    
    for sheet_name, data in sheets.items():
        # Strip trailing whitespaces from all column names
        data.columns = data.columns.str.strip()
        # Replace all occurrences of "null" or any string that consists only of whitespaces with NaN
        # Use a regex sind there are many trailing whitespaces and so on
        sheets[sheet_name] = data.replace(r'^\s*(null|\s*)\s*$', np.nan, regex=True).infer_objects(copy=False)
        sheets[sheet_name] = rename_columns(sheets[sheet_name])

    sheets["fixedBooking"].loc[sheets["fixedBooking"]["bookingId"] == 5, "deskNumber"] = 1
    sheets["fixedBooking"]["deskNumber"] = sheets["fixedBooking"]["deskNumber"].astype(int)
    sheets["variableBooking"]["userId"] += 1

    desk_room_mapping = get_desk_room_mapping(sheets["fixedBooking"], sheets["room"])
    # fixed bookings with room
    data_fixed = pd.merge(sheets["fixedBooking"], sheets["user"], how="left", left_on="userId", right_on="ID").drop(columns=["ID"])
    data_fixed = pd.merge(data_fixed, desk_room_mapping[['roomName']], left_on='bookingId', right_on="deskId", how='left')
    data_fixed["variableBooking"] = 0 # Indicate fixed bookings
    # According to Mr. Fraunhofer, these are leftover entries from old bookings. Therefore we drop them    
    data_fixed = data_fixed.dropna(subset=['blockedFrom', 'userId', 'blockedUntil'], how='all')
    data_fixed.loc[data_fixed['blockedUntil'].isna(), 'blockedUntil'] = 'unlimited'

    # variable bookings with room
    data_variable = pd.merge(sheets["variableBooking"], sheets["user"], how="left", left_on="userId", right_on="ID").drop(columns=["ID"])
    data_variable = pd.merge(data_variable, desk_room_mapping, on='deskId', how='left').drop(columns="deskId")
    data_variable["blockedUntil"] = data_variable["blockedFrom"]
    data_variable["variableBooking"] = 1 # Indicate variable bookings

    data = pd.concat([data_fixed, data_variable], axis=0)

    return data

def get_days():
    pass

def get_users():
    pass

def get_rooms():
    pass

if __name__ == "__main__":
    data = create_dataset()
    data.to_csv("OpTisch.csv", index=False)  # Save dataset to CSV without index
