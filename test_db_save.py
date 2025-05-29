from db import SessionLocal, TrafficData
from mock_data import generate_mock_data

def test_save_and_load():
    df = generate_mock_data()

    session = SessionLocal()
    for _, row in df.iterrows():
        session.add(TrafficData(timestamp=row['timestamp'], location_type='indoor', value=row['indoor_footfall']))
        session.add(TrafficData(timestamp=row['timestamp'], location_type='road', value=row['road_traffic']))
    session.commit()

    data = session.query(TrafficData).all()
    print(f"Records saved: {len(data)}")
    session.close()

if __name__ == "__main__":
    test_save_and_load()
