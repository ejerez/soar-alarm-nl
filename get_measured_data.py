from datetime import datetime, date, timedelta
import datetime as dt
import ddlpy
import pandas as pd
import streamlit as st

async def get_wind_measurements():
    locations = ddlpy.locations()

    bool_stations = locations.index.isin(["ijmuiden.havenhoofd.zuid", "stellendam.haringvlietsluizen.schuif1", 
                                      "vlaktevanderaan", "brouwersdam.brouwershavensegat.2"])
    bool_grootheid_wind = locations["Grootheid.Code"].isin(["WINDSHD", "WINDRTG"])

    selected = locations.loc[
        bool_stations
        & bool_grootheid_wind
        ]

    dates = (dt.datetime.combine((datetime.now() - timedelta(days=1)).date(), dt.time.min), datetime.now())

    data = {}

    # provide a single row of the locations dataframe to ddlpy.measurements
    for index, row in selected.iterrows():
        measurements = ddlpy.measurements(row, start_date=dates[0], end_date=dates[1])
        if not measurements.empty:
            if index not in data:
                data[index] = {
                    'name': row["Naam"],
                    'lon': row["Lon"],
                    'lat': row["Lat"]}
            data[index][row["Grootheid.Code"]] = measurements[["Meetwaarde.Waarde_Numeriek"]]

    st.session_state.measurements = data

'''
locations = ddlpy.locations()

bool_stations = locations.index.str.contains("raan")
bool_grootheid_wind = locations["Grootheid.Code"].isin(["WINDSHD", "WINDRTG"])

selected = locations.loc[
        bool_stations
        & bool_grootheid_wind
        ]

print(selected)

locations = ddlpy.locations()

bool_stations = locations.index.str.contains("vlaktevanderaan")
bool_grootheid_wind = locations["Grootheid.Code"].isin(["WINDSHD", "WINDRTG"])

selected = locations.loc[
    bool_stations
    & bool_grootheid_wind
    ]

dates = (dt.datetime.combine((datetime.now() - timedelta(days=1)).date(), dt.time.min), datetime.now())

data = {}

# provide a single row of the locations dataframe to ddlpy.measurements
for index, row in selected.iterrows():
    measurements = ddlpy.measurements(row, start_date=dates[0], end_date=dates[1])
    if not measurements.empty:
        if index not in data:
            data[index] = {
                'name': row["Naam"],
                'lon': row["Lon"],
                'lat': row["Lat"]}
        data[index][row["Grootheid.Code"]] = measurements[["Meetwaarde.Waarde_Numeriek"]]

print(data)
'''