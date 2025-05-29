from statsmodels.tsa.arima.model import ARIMA
import pandas as pd

def train_predictor(df, column):
    ts = df.set_index('timestamp')[column]

    model = ARIMA(ts, order=(2, 1, 2))
    model_fit = model.fit()

    forecast = model_fit.get_forecast(steps=24)
    forecast_df = forecast.summary_frame()
    forecast_df = forecast_df.reset_index()
    forecast_df.rename(columns={'index': 'ds', 'mean': 'yhat'}, inplace=True)

    return forecast_df

