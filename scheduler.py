def schedule_cleaning(forecast_df, threshold=70):
    tasks = []
    for _, row in forecast_df.iterrows():
        if row['yhat'] > threshold:
            tasks.append({
                "time": row['ds'],
                "task": "High Priority Cleaning",
                "priority": "High"
            })
    return tasks
