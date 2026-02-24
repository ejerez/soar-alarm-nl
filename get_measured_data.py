from datetime import datetime, date, timedelta
import datetime as dt
import ddlpy
import pandas as pd

def since_yesterday():
    now = datetime.now()
    start = dt.datetime.combine((datetime.now() - timedelta(days=1)).date(), dt.time.min)
    return (start, now)

def get_wind_measurements():
    locations = ddlpy.locations()

    bool_stations = locations.index.isin(["ijmuiden.buitenhaven", "stellendam.haringvlietsluizen.schuif1", 
                                      "cadzand.1", "brouwersdam.brouwershavensegat.2"])
    bool_grootheid_wind = locations["Grootheid.Code"].isin(["WINDSHD", "WINDRTG"])

    selected = locations.loc[
        bool_stations
        & bool_grootheid_wind
        ]

    dates = since_yesterday()

    data = {}

    # provide a single row of the locations dataframe to ddlpy.measurements
    for index, row in selected.iterrows():
        measurements = ddlpy.measurements(row, start_date=dates[0], end_date=dates[1])
        if not measurements.empty:
            if index not in data:
                data[index] = {'lon': row["Lon"],
                            'lat': row["Lat"]}
            data[index][row["Grootheid.Code"]] = measurements[["Meetwaarde.Waarde_Numeriek"]]

    return data