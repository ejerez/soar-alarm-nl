from datetime import datetime, date, timedelta
from knmy import knmy

# Return daily aggregated wind, temperature and sunshine duration data for station 209 (IJmond) for the 1st til
# 6th of January, 2017

yesterday = datetime.today() - timedelta(days=1)
now = datetime.now()
print(now)
print(yesterday)

__disclaimer, __stations, __variables, ijmuiden = knmy.get_hourly_data(stations=[225], start=yesterday, end=now,
                                                             variables=['WIND', 'PRCP'], parse=True)
__disclaimer, __stations, __variables, wijk_aan_zee = knmy.get_hourly_data(stations=[257], start=yesterday, end=now,
                                                             variables=['WIND', 'PRCP'], parse=True)
__disclaimer, __stations, __variables, vlissingen = knmy.get_hourly_data(stations=[310], start=yesterday, end=now,
                                                             variables=['WIND', 'PRCP'], parse=True)

print(ijmuiden)
measured_data = {
    'IJmuiden' : {
        'time' : ijmuiden["HH"].tolist(),
        'wind_speed' : ijmuiden["FH"].tolist(),
        'wind_heading' : ijmuiden["DD"].tolist(),
        'wind_gust' : ijmuiden["FX"].tolist(),
        'rain' : ijmuiden["RH"].tolist()
    },
    'Wijk aan Zee' : {
        'time' : wijk_aan_zee["HH"].tolist(),
        'wind_speed' : wijk_aan_zee["FH"].tolist(),
        'wind_heading' : wijk_aan_zee["DD"].tolist(),
        'wind_gust' : wijk_aan_zee["FX"].tolist(),
        'rain' : wijk_aan_zee["RH"].tolist()
    },
    'Vlissingen' : {
        'time' : vlissingen["HH"].tolist(),
        'wind_speed' : vlissingen["FH"].tolist(),
        'wind_heading' : vlissingen["DD"].tolist(),
        'wind_gust' : vlissingen["FX"].tolist(),
        'rain' : vlissingen["RH"].tolist()
    }
}

print(measured_data)

'''
HH time
DD Wind dir
FX gust
FH wind
RH rain
310: Vlissingen
225: IJmuiden
257: Wijk aan Zee
'''