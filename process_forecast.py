import streamlit as st
import numpy as np
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

def get_forecast_soar(model = "knmi_seamless"):
    forecast = []
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": [point["lat"] for point in st.session_state.soar_points],
        "longitude": [point["lon"] for point in st.session_state.soar_points],
        "daily": ["sunrise", "sunset"],
        "hourly": ["temperature_2m", "visibility", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "precipitation"],
        "models": model,
        "timezone": "Europe/Berlin",
        "past_days": 1,
        "forecast_days": 6,
    }

    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    responses = openmeteo.weather_api(url, params=params)

    for id, response in enumerate(responses):
        hourly = response.Hourly()
        hourly_data = {
            "date": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            ),
            "temperature": hourly.Variables(0).ValuesAsNumpy(),
            "visibility": hourly.Variables(1).ValuesAsNumpy(),
            "wind_speed": hourly.Variables(2).ValuesAsNumpy(),
            "wind_direction": hourly.Variables(3).ValuesAsNumpy(),
            "wind_gusts": hourly.Variables(4).ValuesAsNumpy(),
            "precipitation": hourly.Variables(5).ValuesAsNumpy()
        }

        daily = response.Daily()
        daily_data = {
            "date": pd.date_range(
                start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=daily.Interval()),
                inclusive="left"
            ),
            "sunrise": pd.to_datetime(daily.Variables(0).ValuesInt64AsNumpy(), unit="s", utc=True),
            "sunset": pd.to_datetime(daily.Variables(1).ValuesInt64AsNumpy(), unit="s", utc=True)
        }

        forecast.append({"id": id, "daily_data": daily_data, "hourly_data": hourly_data})
    return forecast

def get_forecast_therm():
    forecast = []
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": [point["lat"] for point in st.session_state.therm_points],
        "longitude": [point["lon"] for point in st.session_state.therm_points],
        "daily": ["sunrise", "sunset"],
        "hourly": ["temperature_2m", "visibility", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "precipitation", "temperature_1000hPa", "temperature_925hPa", "temperature_850hPa", "temperature_700hPa", "direct_radiation"],
        "models": "ecmwf_ifs",
        "timezone": "Europe/Berlin",
        "past_days": 1,
        "forecast_days": 7,
    }

    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    responses = openmeteo.weather_api(url, params=params)

    for id, response in enumerate(responses):
        hourly = response.Hourly()
        hourly_data = {
            "date": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            ),
            "temperature": hourly.Variables(0).ValuesAsNumpy(),
            "visibility": hourly.Variables(1).ValuesAsNumpy(),
            "wind_speed": hourly.Variables(2).ValuesAsNumpy(),
            "wind_direction": hourly.Variables(3).ValuesAsNumpy(),
            "wind_gusts": hourly.Variables(4).ValuesAsNumpy(),
            "precipitation": hourly.Variables(5).ValuesAsNumpy(),
            "temperature_110m": hourly.Variables(6).ValuesAsNumpy(),
            "temperature_800m": hourly.Variables(7).ValuesAsNumpy(),
            "temperature_1500m": hourly.Variables(8).ValuesAsNumpy(),
            "temperature_3000m": hourly.Variables(9).ValuesAsNumpy(),
            "solar_irradiation": hourly.Variables(10).ValuesAsNumpy()
        }

        daily = response.Daily()
        daily_data = {
            "date": pd.date_range(
                start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=daily.Interval()),
                inclusive="left"
            ),
            "sunrise": pd.to_datetime(daily.Variables(0).ValuesInt64AsNumpy(), unit="s", utc=True),
            "sunset": pd.to_datetime(daily.Variables(1).ValuesInt64AsNumpy(), unit="s", utc=True)
        }

        forecast.append({"id": id, "daily_data": daily_data, "hourly_data": hourly_data})
    return forecast

def process_soar_forecast(_raw_forecast):
    dates = list(set([date.date() for date in _raw_forecast[0]["daily_data"]["date"]]))
    dates.sort()

    if 'date_list' not in st.session_state:
        st.session_state.date_list = dates

    forecast = []
    for date in dates:
        daily = [{
            "sunrise": next(data for i, data in enumerate(point_forecast["daily_data"]["sunrise"])
                        if point_forecast["daily_data"]["date"][i].date() == date),
            "sunset": next(data for i, data in enumerate(point_forecast["daily_data"]["sunset"])
                        if point_forecast["daily_data"]["date"][i].date() == date)
        } for point_forecast in _raw_forecast]

        day_forecast = [{
            "sunrise": daily[point]["sunrise"],
            "sunset": daily[point]["sunset"],
            "time": [time for time in point_forecast["hourly_data"]["date"]
                    if (time >= daily[point]["sunrise"] and time <= daily[point]["sunset"])],
            "temperature": [data for i, data in enumerate(point_forecast["hourly_data"]["temperature"])
                        if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                            and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],
            "precipitation": [data for i, data in enumerate(point_forecast["hourly_data"]["precipitation"])
                            if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                                and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],
            "visibility": [data for i, data in enumerate(point_forecast["hourly_data"]["visibility"])
                        if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                            and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],
            "wind_speed": [data for i, data in enumerate(point_forecast["hourly_data"]["wind_speed"])
                        if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                            and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],
            "wind_direction": [data for i, data in enumerate(point_forecast["hourly_data"]["wind_direction"])
                            if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                                and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],
            "wind_gusts": [data for i, data in enumerate(point_forecast["hourly_data"]["wind_gusts"])
                        if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                            and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])]
        } for point, point_forecast in enumerate(_raw_forecast)]
        forecast.append(day_forecast)
    return forecast

def process_therm_forecast(_raw_forecast):
    dates = list(set([date.date() for date in _raw_forecast[0]["daily_data"]["date"]]))
    dates.sort()

    if 'date_list' not in st.session_state:
        st.session_state.date_list = dates

    forecast = []
    for date in dates:
        daily = [{
            "sunrise": next(data for i, data in enumerate(point_forecast["daily_data"]["sunrise"])
                        if point_forecast["daily_data"]["date"][i].date() == date),
            "sunset": next(data for i, data in enumerate(point_forecast["daily_data"]["sunset"])
                        if point_forecast["daily_data"]["date"][i].date() == date)
        } for point_forecast in _raw_forecast]

        day_forecast = [{
            "sunrise": daily[point]["sunrise"],
            "sunset": daily[point]["sunset"],
            "time": [time for time in point_forecast["hourly_data"]["date"]
                    if (time >= daily[point]["sunrise"] and time <= daily[point]["sunset"])],
            "temperature": [data for i, data in enumerate(point_forecast["hourly_data"]["temperature"])
                        if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                            and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],
            "temperature_110m": [data for i, data in enumerate(point_forecast["hourly_data"]["temperature_110m"])
                        if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                            and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],
            "temperature_800m": [data for i, data in enumerate(point_forecast["hourly_data"]["temperature_800m"])
                        if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                            and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],
            "temperature_1500m": [data for i, data in enumerate(point_forecast["hourly_data"]["temperature_1500m"])
                        if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                            and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],
            "temperature_3000m": [data for i, data in enumerate(point_forecast["hourly_data"]["temperature_3000m"])
                        if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                            and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],
            "solar_irradiation": [data for i, data in enumerate(point_forecast["hourly_data"]["solar_irradiation"])
                        if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                            and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],
            "precipitation": [data for i, data in enumerate(point_forecast["hourly_data"]["precipitation"])
                            if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                                and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],
            "visibility": [data for i, data in enumerate(point_forecast["hourly_data"]["visibility"])
                        if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                            and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],
            "wind_speed": [data for i, data in enumerate(point_forecast["hourly_data"]["wind_speed"])
                        if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                            and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],
            "wind_direction": [data for i, data in enumerate(point_forecast["hourly_data"]["wind_direction"])
                            if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                                and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])],
            "wind_gusts": [data for i, data in enumerate(point_forecast["hourly_data"]["wind_gusts"])
                        if (point_forecast["hourly_data"]["date"][i] >= daily[point]["sunrise"]
                            and point_forecast["hourly_data"]["date"][i] <= daily[point]["sunset"])]
        } for point, point_forecast in enumerate(_raw_forecast)]
        forecast.append(day_forecast)
    return forecast

def forecast_display_soar(forecast):
    disp_forecast = []
    for day in forecast:
        day_forecast = []
        for i, point_forecast in enumerate(day):
            point = st.session_state.soar_points[i]
            wind_pizza = np.zeros(int(360/22.5))

            for i, time in enumerate(point_forecast["time"]):
                # Check basic conditions
                if point_forecast["precipitation"][i] < 0.1 and point_forecast["visibility"][i] > 0.1 and point_forecast["wind_speed"][i] > st.session_state.min_speed:
                        rel_head = point_forecast["wind_direction"][i] - point["heading"]
                        wind_pizza[int(np.floor(rel_head/22.5))] += 1
            wind_pizza[0] = wind_pizza[0] + wind_pizza[-1]
            wind_pizza[-1] = wind_pizza[0]
            good_hours = wind_pizza[0]
            marginal_hours = wind_pizza[1] + wind_pizza[-2]
            day_forecast.append({"wind_pizza": wind_pizza, "good_hours": good_hours, "marginal_hours": marginal_hours})
        disp_forecast.append(day_forecast)
    return disp_forecast

def forecast_display_therm(forecast):
    disp_forecast = []
    for day in forecast:
        day_forecast = []
        for i, point_forecast in enumerate(day):
            point = st.session_state.soar_points[i]
            for i, time in enumerate(point_forecast["time"]):
                flyable_hours = 0
                thermal_hours = 0
                # Check basic conditions
                if point_forecast["precipitation"][i] < 0.1 and point_forecast["visibility"][i] > 0.5 and point_forecast["wind_speed"][i] < point.get("max_wind_speed", 30):
                    # Check if wind direction is within acceptable range
                    start_heading = point.get("start_heading_range", 0)
                    end_heading = point.get("end_heading_range", 360)

                    wind_dir = point_forecast["wind_direction"][i]
                    wind_ok = False

                    # Handle heading range that crosses 0° (e.g., 270°-90°)
                    if start_heading > end_heading:
                        if wind_dir >= start_heading or wind_dir <= end_heading:
                            wind_ok = True
                    else:
                        if start_heading <= wind_dir and  wind_dir <= end_heading:
                            wind_ok = True
                    if wind_ok:
                        flyable_hours += 1
                        env_lapse_rate = (point_forecast["temperature"][i] - point_forecast["temperature_800m"][i])/0.8
                        irradiation = point_forecast["solar_irradiation"][i]
                        
                        if env_lapse_rate >= 7 and irradiation >= 200:
                            thermal_hours += 1
                        
            day_forecast.append({"flyable_hours": flyable_hours, "thermal_hours": thermal_hours})
        disp_forecast.append(day_forecast)
    return disp_forecast