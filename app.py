from flask import Flask, jsonify
from mock_data import generate_mock_data
from predictor import train_predictor
from scheduler import schedule_cleaning
from db import SessionLocal, TrafficData, Forecast, CleaningTask
from telegram_bot import send_notification
from datetime import datetime
import time
import logging
import asyncio
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def save_to_db(df, forecast_indoor, forecast_road, indoor_tasks, road_tasks):
    session = SessionLocal()
    try:
        # Save raw traffic data
        for _, row in df.iterrows():
            session.add(TrafficData(timestamp=row['timestamp'], location_type='indoor', value=row['indoor_footfall']))
            session.add(TrafficData(timestamp=row['timestamp'], location_type='road', value=row['road_traffic']))

        # Save forecasts
        for _, row in forecast_indoor.iterrows():
            session.add(Forecast(timestamp=row['ds'], location_type='indoor', predicted_value=row['yhat']))
        for _, row in forecast_road.iterrows():
            session.add(Forecast(timestamp=row['ds'], location_type='road', predicted_value=row['yhat']))

        # Save tasks
        for task in indoor_tasks:
            session.add(CleaningTask(time=task['time'], task=task['task'], priority=task['priority'], location_type='indoor'))
        for task in road_tasks:
            session.add(CleaningTask(time=task['time'], task=task['task'], priority=task['priority'], location_type='road'))

        session.commit()
        logger.info("Successfully saved data to database")
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving to database: {e}")
        raise
    finally:
        session.close()

@app.route("/predict-cleaning", methods=["GET"])
def predict_cleaning():
    try:
        df = generate_mock_data()
        indoor_forecast = train_predictor(df, column='indoor_footfall')
        road_forecast = train_predictor(df, column='road_traffic')

        indoor_tasks = schedule_cleaning(indoor_forecast, 'indoor')
        road_tasks = schedule_cleaning(road_forecast, 'road')

        # Convert datetime objects to strings for JSON serialization
        indoor_tasks_json = [
            {
                'time': task['time'].strftime('%Y-%m-%d %H:%M:%S'),
                'task': task['task'],
                'priority': task['priority']
            }
            for task in indoor_tasks
        ]
        
        road_tasks_json = [
            {
                'time': task['time'].strftime('%Y-%m-%d %H:%M:%S'),
                'task': task['task'],
                'priority': task['priority']
            }
            for task in road_tasks
        ]

        save_to_db(df, indoor_forecast, road_forecast, indoor_tasks, road_tasks)

        return jsonify({
            "status": "success",
            "indoor": indoor_tasks_json,
            "roads": road_tasks_json
        })
    except Exception as e:
        logger.error(f"Error in predict_cleaning: {e}\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/send-notifications", methods=["GET"])
def send_notifications():
    logger.info("Starting to send notifications...")
    
    try:
        df = generate_mock_data()
        indoor_forecast = train_predictor(df, column='indoor_footfall')
        road_forecast = train_predictor(df, column='road_traffic')

        indoor_tasks = schedule_cleaning(indoor_forecast, 'indoor')
        road_tasks = schedule_cleaning(road_forecast, 'road')

        logger.info(f"Generated {len(indoor_tasks)} indoor tasks and {len(road_tasks)} road tasks")

        # Send Telegram notifications for tasks with minimal delay
        for i, task in enumerate(indoor_tasks, 1):
            logger.info(f"Sending indoor task notification {i}/{len(indoor_tasks)}")
            try:
                send_notification(
                    task['task'],
                    task['time'].strftime('%Y-%m-%d %H:%M:%S'),
                    task['priority']
                )
                logger.info(f"Successfully sent indoor task notification {i}")
                time.sleep(1)  # Just 1 second delay between notifications
            except Exception as e:
                logger.error(f"Failed to send indoor task notification {i}: {e}\n{traceback.format_exc()}")
                continue  # Continue with next task instead of failing completely
        
        time.sleep(2)  # Just 2 seconds delay between indoor and road tasks
        
        for i, task in enumerate(road_tasks, 1):
            logger.info(f"Sending road task notification {i}/{len(road_tasks)}")
            try:
                send_notification(
                    task['task'],
                    task['time'].strftime('%Y-%m-%d %H:%M:%S'),
                    task['priority']
                )
                logger.info(f"Successfully sent road task notification {i}")
                time.sleep(1)  # Just 1 second delay between notifications
            except Exception as e:
                logger.error(f"Failed to send road task notification {i}: {e}\n{traceback.format_exc()}")
                continue  # Continue with next task instead of failing completely

        logger.info("Finished sending all notifications")
        return jsonify({
            "status": "success",
            "message": "Notifications sent successfully"
        })
    except Exception as e:
        logger.error(f"Error in send_notifications: {e}\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/test-notification", methods=["GET"])
def test_notification():
    """Test endpoint to send a single notification"""
    try:
        logger.info("Sending test notification...")
        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Run the notification function
            result = loop.run_until_complete(
                send_notification(
                    "Test Cleaning Task",
                    "2025-05-30 15:00:00",
                    "High"
                )
            )
            if result:
                logger.info("Test notification sent successfully")
                return jsonify({
                    "status": "success",
                    "message": "Test notification sent successfully"
                })
            else:
                logger.error("Failed to send test notification")
                return jsonify({
                    "status": "error",
                    "message": "Failed to send test notification"
                }), 500
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Error sending test notification: {e}\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)