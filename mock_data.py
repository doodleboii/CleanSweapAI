import pandas as pd
import random
from datetime import datetime, timedelta

def generate_mock_data(hours=168):  # 7 days = 168 hours
    now = datetime.now()
    timestamps = [now - timedelta(hours=i) for i in range(hours)][::-1]

    indoor = []
    road = []

    for t in timestamps:
        # Simulate indoor footfall with peak in morning/evening
        if 8 <= t.hour <= 10 or 17 <= t.hour <= 19:
            indoor.append(random.randint(80, 150))  # Rush hours
        else:
            indoor.append(random.randint(10, 40))   # Off hours

        # Simulate road traffic
        if 7 <= t.hour <= 11 or 16 <= t.hour <= 20:
            road.append(random.randint(200, 400))  # Busy roads
        else:
            road.append(random.randint(50, 150))   # Low traffic

    return pd.DataFrame({
        'timestamp': timestamps,
        'indoor_footfall': indoor,
        'road_traffic': road
    })
