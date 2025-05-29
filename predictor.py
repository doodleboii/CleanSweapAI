import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from datetime import timedelta

def train_predictor(df, column='indoor_footfall'):
    ts = df.set_index('timestamp')[column]
    ts = ts.asfreq('H').interpolate()

    # Train ARIMA
    model = ARIMA(ts, order=(2, 1, 2))
    model_fit = model.fit()

    # Forecast next 24 hours
    forecast = model_fit.forecast(steps=24)
    last_time = df['timestamp'].max()

    forecast_df = pd.DataFrame({
        'ds': [last_time + timedelta(hours=i + 1) for i in range(24)],
        'yhat': forecast
    })
    
    print(f"=== Forecast for {column} ===")
    print(forecast_df)
    
    return forecast_df
