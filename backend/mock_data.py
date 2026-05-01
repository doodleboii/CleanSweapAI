import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from db import SessionLocal, TrafficData

def generate_mock_data(start_date=None, periods=72, freq='H', noise_level=5, mode='normal'):
    """
    Generate mock footfall and road traffic data with timestamps.
    
    Parameters:
    - start_date: datetime, default 3 days before now if None
    - periods: int, number of periods to generate
    - freq: str, frequency string compatible with pandas date_range (e.g., 'H', '15T')
    - noise_level: int, max noise to add/subtract randomly
    - mode: str, scenario mode - one of 'normal', 'peak', 'low', 'random', 'trend'
    
    Returns:
    - pandas DataFrame with columns ['timestamp', 'indoor_footfall', 'road_traffic']
    """
    if start_date is None:
        start_date = datetime.now() - timedelta(days=3)
    
    date_range = pd.date_range(start=start_date, periods=periods, freq=freq)

    indoor_footfall = []
    road_traffic = []

    # Mode-specific multipliers and adjustments
    if mode == 'peak':
        indoor_mult, road_mult = 1.8, 1.6
        noise_level = int(noise_level * 1.5)
    elif mode == 'low':
        indoor_mult, road_mult = 0.4, 0.5
        noise_level = max(1, int(noise_level * 0.5))
    elif mode == 'random':
        indoor_mult, road_mult = 1.0, 1.0
        noise_level = int(noise_level * 3)
    elif mode == 'trend':
        indoor_mult, road_mult = 1.0, 1.0  # will apply gradual increase
    else:  # 'normal'
        indoor_mult, road_mult = 1.0, 1.0

    for i, dt in enumerate(date_range):
        hour = dt.hour

        # Indoor footfall logic
        base_indoor = 10
        if 8 <= hour <= 10 or 17 <= hour <= 19:
            base_indoor = 40
        elif 11 <= hour <= 16:
            base_indoor = 25
        base_indoor = int(base_indoor * indoor_mult)

        # Road traffic logic
        base_road = 30
        if 7 <= hour <= 9 or 16 <= hour <= 18:
            base_road = 100
        elif 10 <= hour <= 15:
            base_road = 60
        base_road = int(base_road * road_mult)

        # Apply trend: gradual increase over time
        if mode == 'trend':
            trend_factor = 1.0 + (i / periods) * 0.5  # up to 50% increase
            base_indoor = int(base_indoor * trend_factor)
            base_road = int(base_road * trend_factor)

        noise_indoor = np.random.randint(-noise_level, noise_level + 1)
        indoor_footfall.append(max(0, base_indoor + noise_indoor))

        noise_road = np.random.randint(-2*noise_level, 2*noise_level + 1)
        road_traffic.append(max(0, base_road + noise_road))

    df = pd.DataFrame({
        'timestamp': date_range,
        'indoor_footfall': indoor_footfall,
        'road_traffic': road_traffic
    })

    # Ensure timestamps are timezone naive 
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)

    return df

def save_mock_data_to_db(df):
    session = SessionLocal()
    try:
        for _, row in df.iterrows():
            # Save indoor footfall
            indoor_record = TrafficData(timestamp=row['timestamp'], location_type='indoor', value=row['indoor_footfall'])
            session.add(indoor_record)
            
            # Save road traffic
            road_record = TrafficData(timestamp=row['timestamp'], location_type='road', value=row['road_traffic'])
            session.add(road_record)
        
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error saving data: {e}")
    finally:
        session.close()