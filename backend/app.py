from flask import Flask, jsonify, request
from mock_data import generate_mock_data
from predictor import train_predictor, evaluate_model
from scheduler import schedule_cleaning
from db import SessionLocal, TrafficData, Forecast, CleaningTask
from datetime import datetime
import time
import logging
import traceback
import requests

BOT_TOKEN = '7996895067:AAEMwpL74LLiqlIBwImLnjjz9Gl8to_b1dU'
CHAT_ID = '1315760644'

def send_sync_notification(task: str, time: str, priority: str):
    """Send a notification about a cleaning task using requests."""
    message = (
        f"🧹 *New Cleaning Task Scheduled!*\n\n"
        f"🧹 Task: {task}\n"
        f"⏰ Time: {time}\n"
        f"🔔 Priority: {priority.capitalize()}"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            return True
        else:
            logger.error(f"Telegram API error: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to send telegram message via requests: {e}")
        return False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# UPDATED — save_to_db now persists lower/upper confidence bounds
def save_to_db(df, forecast_indoor, forecast_road, indoor_tasks, road_tasks, indoor_mae=None, road_mae=None):
    session = SessionLocal()
    try:
        # Save raw traffic data
        for _, row in df.iterrows():
            session.add(TrafficData(timestamp=row['timestamp'], location_type='indoor', value=row['indoor_footfall']))
            session.add(TrafficData(timestamp=row['timestamp'], location_type='road', value=row['road_traffic']))

        # Save forecasts with confidence intervals
        for _, row in forecast_indoor.iterrows():
            session.add(Forecast(
                timestamp=row['ds'],
                location_type='indoor',
                predicted_value=row['yhat'],
                lower=row.get('lower'),      # NEW
                upper=row.get('upper'),      # NEW
                error=indoor_mae
            ))
        for _, row in forecast_road.iterrows():
            session.add(Forecast(
                timestamp=row['ds'],
                location_type='road',
                predicted_value=row['yhat'],
                lower=row.get('lower'),      # NEW
                upper=row.get('upper'),      # NEW
                error=road_mae
            ))

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

# UPDATED — Full pipeline: generate → predict → evaluate → schedule → store
@app.route("/predict-cleaning", methods=["GET"])
def predict_cleaning():
    try:
        mode = request.args.get("mode", "normal")
        df = generate_mock_data(mode=mode)

        # Train for future forecasting (now returns confidence intervals + best_order)
        indoor_forecast, indoor_order = train_predictor(df, column='indoor_footfall')    # UPDATED
        road_forecast, road_order = train_predictor(df, column='road_traffic')            # UPDATED

        # Evaluate model for MAE and MAPE (now returns best_order too)
        indoor_mae, indoor_mape, _, _, _ = evaluate_model(df, column='indoor_footfall')   # UPDATED
        road_mae, road_mape, _, _, _ = evaluate_model(df, column='road_traffic')           # UPDATED

        # NEW — Dynamic scheduling using historical mean
        indoor_mean = df['indoor_footfall'].mean()
        road_mean = df['road_traffic'].mean()
        indoor_tasks = schedule_cleaning(indoor_forecast, 'indoor', data_mean=indoor_mean)
        road_tasks = schedule_cleaning(road_forecast, 'road', data_mean=road_mean)

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

        save_to_db(df, indoor_forecast, road_forecast, indoor_tasks, road_tasks, indoor_mae=indoor_mae, road_mae=road_mae)

        # Send notifications if requested
        if request.args.get('notify', 'false').lower() == 'true':
            logger.info("Sending notifications from /predict-cleaning as requested...")
            for task in indoor_tasks_json:
                send_sync_notification(task['task'], task['time'], task['priority'])
                time.sleep(1)
            for task in road_tasks_json:
                send_sync_notification(task['task'], task['time'], task['priority'])
                time.sleep(1)

        # UPDATED — Response now includes confidence intervals, ARIMA orders, and data means
        return jsonify({
            "status": "success",
            "indoor": indoor_tasks_json,
            "roads": road_tasks_json,
            "forecast": {
                "indoor": indoor_forecast[['ds', 'yhat', 'lower', 'upper']].assign(
                    ds=indoor_forecast['ds'].dt.strftime('%Y-%m-%d %H:%M:%S')
                ).to_dict(orient='records'),
                "road": road_forecast[['ds', 'yhat', 'lower', 'upper']].assign(
                    ds=road_forecast['ds'].dt.strftime('%Y-%m-%d %H:%M:%S')
                ).to_dict(orient='records')
            },
            "metrics": {
                "indoor_mae": round(indoor_mae, 2),
                "road_mae": round(road_mae, 2),
                "indoor_mape": round(indoor_mape, 2),
                "road_mape": round(road_mape, 2),
                "best_order_indoor": list(indoor_order),    # NEW
                "best_order_road": list(road_order),        # NEW
                "indoor_mean": round(indoor_mean, 2),       # NEW
                "road_mean": round(road_mean, 2),           # NEW
                "mode": mode
            }
        })
    except Exception as e:
        logger.error(f"Error in predict_cleaning: {e}\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# UPDATED — evaluate-all now returns ARIMA orders + auto insights
@app.route("/evaluate-all", methods=["GET"])
def evaluate_all():
    """Evaluate all scenarios and return comparison metrics with insights."""
    modes = ["normal", "peak", "low", "random", "trend"]
    results = []

    for mode in modes:
        try:
            df = generate_mock_data(mode=mode)
            indoor_mae, indoor_mape, _, _, indoor_order = evaluate_model(df, column='indoor_footfall')   # UPDATED
            road_mae, road_mape, _, _, road_order = evaluate_model(df, column='road_traffic')             # UPDATED

            results.append({
                "mode": mode,
                "indoor_mae": round(indoor_mae, 2),
                "road_mae": round(road_mae, 2),
                "indoor_mape": round(indoor_mape, 2),
                "road_mape": round(road_mape, 2),
                "indoor_order": list(indoor_order),    # NEW
                "road_order": list(road_order)         # NEW
            })
        except Exception as e:
            logger.error(f"Error evaluating mode {mode}: {e}")

    # NEW — Auto insights: best and worst performing modes
    insights = {}
    if results:
        best_indoor = min(results, key=lambda x: x['indoor_mae'])
        worst_indoor = max(results, key=lambda x: x['indoor_mae'])
        best_road = min(results, key=lambda x: x['road_mae'])
        worst_road = max(results, key=lambda x: x['road_mae'])

        avg_mae = sum(r['indoor_mae'] + r['road_mae'] for r in results) / (len(results) * 2)

        insights = {
            "best_indoor_mode": best_indoor['mode'],
            "best_indoor_mae": best_indoor['indoor_mae'],
            "worst_indoor_mode": worst_indoor['mode'],
            "worst_indoor_mae": worst_indoor['indoor_mae'],
            "best_road_mode": best_road['mode'],
            "best_road_mae": best_road['road_mae'],
            "worst_road_mode": worst_road['mode'],
            "worst_road_mae": worst_road['road_mae'],
            "average_mae": round(avg_mae, 2),
            "system_insight": _generate_system_insight(results)    # NEW
        }

    return jsonify({
        "status": "success",
        "results": results,
        "insights": insights
    })


# NEW — Generate human-readable system insights
def _generate_system_insight(results):
    """Analyze results and produce actionable insight text."""
    insights = []

    mae_values = [(r['mode'], r['indoor_mae'] + r['road_mae']) for r in results]
    mae_values.sort(key=lambda x: x[1])

    best_mode = mae_values[0][0]
    worst_mode = mae_values[-1][0]

    insights.append(f"Model performs best on '{best_mode}' traffic patterns (structured, predictable data).")

    if worst_mode in ['random', 'trend']:
        insights.append(f"Performance degrades in '{worst_mode}' conditions — consider ensemble methods for noisy scenarios.")
    else:
        insights.append(f"Worst performance observed in '{worst_mode}' mode — review data characteristics.")

    # Check if ARIMA is consistent across modes
    orders = set()
    for r in results:
        orders.add(tuple(r.get('indoor_order', [1, 1, 1])))
    if len(orders) > 2:
        insights.append("Dynamic ARIMA selection is adapting order per scenario — good model flexibility.")
    else:
        insights.append("ARIMA order is relatively stable across scenarios — data patterns are consistent.")

    return " | ".join(insights)


@app.route("/send-notifications", methods=["GET"])
def send_notifications():
    logger.info("Starting to send notifications...")

    try:
        df = generate_mock_data()
        indoor_forecast, _ = train_predictor(df, column='indoor_footfall')    # UPDATED
        road_forecast, _ = train_predictor(df, column='road_traffic')          # UPDATED

        indoor_mean = df['indoor_footfall'].mean()
        road_mean = df['road_traffic'].mean()
        indoor_tasks = schedule_cleaning(indoor_forecast, 'indoor', data_mean=indoor_mean)
        road_tasks = schedule_cleaning(road_forecast, 'road', data_mean=road_mean)

        logger.info(f"Generated {len(indoor_tasks)} indoor tasks and {len(road_tasks)} road tasks")

        # Send Telegram notifications for tasks with minimal delay
        for i, task in enumerate(indoor_tasks, 1):
            logger.info(f"Sending indoor task notification {i}/{len(indoor_tasks)}")
            try:
                success = send_sync_notification(
                    task['task'],
                    task['time'].strftime('%Y-%m-%d %H:%M:%S'),
                    task['priority']
                )
                if success:
                    logger.info(f"Successfully sent indoor task notification {i}")
                time.sleep(1)  # Just 1 second delay between notifications
            except Exception as e:
                logger.error(f"Failed to send indoor task notification {i}: {e}\n{traceback.format_exc()}")
                continue  # Continue with next task instead of failing completely

        time.sleep(2)  # Just 2 seconds delay between indoor and road tasks

        for i, task in enumerate(road_tasks, 1):
            logger.info(f"Sending road task notification {i}/{len(road_tasks)}")
            try:
                success = send_sync_notification(
                    task['task'],
                    task['time'].strftime('%Y-%m-%d %H:%M:%S'),
                    task['priority']
                )
                if success:
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

        # Run the notification function synchronously
        result = send_sync_notification(
            "Test Cleaning Task",
            "2025-05-30 15:00:00",
            "High"
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

    except Exception as e:
        logger.error(f"Error sending test notification: {e}\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(debug=True)