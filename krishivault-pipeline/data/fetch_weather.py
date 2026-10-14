import json, sys, urllib.request, csv
sys.stdout.reconfigure(encoding='utf-8')

# Fetch weather for all target districts from Open-Meteo (free, no API key)
districts = {
    'Bogura':  {'lat': 24.8465, 'lon': 89.3773},
    'Rangpur': {'lat': 25.7439, 'lon': 89.2752},
    'Dinajpur':{'lat': 25.6279, 'lon': 88.6332},
    'Rajshahi':{'lat': 24.3636, 'lon': 88.6241},
    'Dhaka':   {'lat': 23.8103, 'lon': 90.4125},
}

all_weather = []

for district, coords in districts.items():
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={coords['lat']}&longitude={coords['lon']}"
        f"&daily=temperature_2m_max,temperature_2m_min,rain_sum,relative_humidity_2m_mean,wind_speed_10m_max"
        f"&timezone=Asia/Dhaka&past_days=90"
    )
    req = urllib.request.Request(url, headers={'User-Agent': 'KrishiVault/1.0'})
    
    try:
        response = urllib.request.urlopen(req, timeout=15)
        data = json.loads(response.read().decode())
        daily = data.get('daily', {})
        dates = daily.get('time', [])
        temp_max = daily.get('temperature_2m_max', [])
        temp_min = daily.get('temperature_2m_min', [])
        rain = daily.get('rain_sum', [])
        humidity = daily.get('relative_humidity_2m_mean', [])
        wind = daily.get('wind_speed_10m_max', [])
        
        print(f"  {district}: {len(dates)} days fetched")
        
        for i, d in enumerate(dates):
            tmin = temp_min[i] if i < len(temp_min) else None
            tmax = temp_max[i] if i < len(temp_max) else None
            all_weather.append({
                'date': d,
                'district': district,
                'temp_min': tmin,
                'temp_max': tmax,
                'temp_avg': round((tmin + tmax) / 2, 1) if tmin and tmax else None,
                'rainfall_mm': rain[i] if i < len(rain) else 0,
                'humidity_pct': humidity[i] if i < len(humidity) else None,
                'wind_speed_kmh': wind[i] if i < len(wind) else None,
                'source': 'open-meteo'
            })
    except Exception as e:
        print(f"  {district}: FAILED - {e}")

# Save as JSON
with open('data/raw/weather_all_districts_90d.json', 'w') as f:
    json.dump(all_weather, f, indent=2)

# Save as CSV
with open('data/processed/weather_all_districts.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['date','district','temp_min','temp_max','temp_avg','rainfall_mm','humidity_pct','wind_speed_kmh','source'])
    writer.writeheader()
    writer.writerows(all_weather)

print(f"\nTotal weather records: {len(all_weather)}")
print(f"Saved to data/raw/weather_all_districts_90d.json")
print(f"Saved to data/processed/weather_all_districts.csv")
