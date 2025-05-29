from flask import Flask, jsonify
from mock_data import generate_mock_data
from predictor import train_predictor
from scheduler import schedule_cleaning
from db import SessionLocal, TrafficData, Forecast, CleaningTask
from telegram_bot import send_cleaning_notification

from apscheduler.schedulers.background import BackgroundScheduler  

import requests  

app = Flask(__name__)

def save_to_db(df, forecast_indoor, forecast_road, indoor_tasks, road_tasks):
    session = SessionLocal()
    for _, row in df.iterrows():
        session.add(TrafficData(timestamp=row['timestamp'], location_type='indoor', value=row['indoor_footfall']))
        session.add(TrafficData(timestamp=row['timestamp'], location_type='road', value=row['road_traffic']))
    for _, row in forecast_indoor.iterrows():
        session.add(Forecast(timestamp=row['ds'], location_type='indoor', predicted_value=row['yhat']))
    for _, row in forecast_road.iterrows():
        session.add(Forecast(timestamp=row['ds'], location_type='road', predicted_value=row['yhat']))
    for task in indoor_tasks:
        session.add(CleaningTask(time=task['time'], task=task['task'], priority=task['priority'], location_type='indoor'))
    for task in road_tasks:
        session.add(CleaningTask(time=task['time'], task=task['task'], priority=task['priority'], location_type='road'))
    session.commit()
    session.close()

@app.route("/predict-cleaning", methods=["GET"])
def predict_cleaning():
    df = generate_mock_data()
    indoor_forecast = train_predictor(df, column='indoor_footfall')
    road_forecast = train_predictor(df, column='road_traffic')

    indoor_tasks = schedule_cleaning(indoor_forecast, threshold=20)
    road_tasks = schedule_cleaning(road_forecast, threshold=100)

    for task in indoor_tasks:
        send_cleaning_notification(task['task'], task['time'], task['priority'])
    for task in road_tasks:
        send_cleaning_notification(task['task'], task['time'], task['priority'])

    save_to_db(df, indoor_forecast, road_forecast, indoor_tasks, road_tasks)

    return jsonify({
        "indoor": indoor_tasks,
        "roads": road_tasks
    })


def scheduled_task():
    try:
        requests.get("http://127.0.0.1:5000/predict-cleaning")
        print("Scheduled cleaning prediction run successfully")
    except Exception as e:
        print("Error running scheduled cleaning prediction:", e)

scheduler = BackgroundScheduler()
scheduler.add_job(func=scheduled_task, trigger="interval", minutes=1)  # every 60 mins
scheduler.start()


if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=scheduled_task, trigger="interval", minutes=1)
    scheduler.start()

    print("Starting Flask app with background scheduler...")
    app.run(debug=True)
    
