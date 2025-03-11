import requests
import pandas as pd
import mplfinance as mpf
import numpy as np
from datetime import datetime
import io
import base64
import json

# API URLs
data_url = "https://eximus.net/api/api/v1/ohlc/EURUSD?timeframe=M1"
# Örnek bir API endpoint'i - bunu kendi API endpoint'iniz ile değiştirin
upload_url = "https://api.example.com/upload"  

def calculate_rsi(data, periods=14):
    # Calculate price changes
    close_delta = data['Close'].diff()
    
    # Make two series: one for lower closes and one for higher closes
    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)
    
    # Calculate the EWMA (Exponential Weighted Moving Average)
    ma_up = up.ewm(com=periods-1, adjust=True, min_periods=periods).mean()
    ma_down = down.ewm(com=periods-1, adjust=True, min_periods=periods).mean()
    
    rsi = ma_up / ma_down
    rsi = 100 - (100/(1 + rsi))
    return rsi

def fetch_ohlc_data():
    try:
        # Fetch data from API
        response = requests.get(data_url)
        response.raise_for_status()
        data = response.json()
        
        # Convert data to DataFrame
        df = pd.DataFrame(data)
        
        # Convert time to datetime
        df['time'] = pd.to_datetime(df['time'])
        
        # Set time as index
        df.set_index('time', inplace=True)
        
        # Ensure column names match mplfinance requirements
        df = df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        })
        
        # Calculate RSI
        df['RSI'] = calculate_rsi(df)
        
        return df
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def plot_candlestick(df):
    # Create a buffer to save the plot
    buf = io.BytesIO()
    
    # Define custom style
    mc = mpf.make_marketcolors(up='green',down='red',
                              edge='black',
                              wick='black')
    s = mpf.make_mpf_style(marketcolors=mc, 
                          gridstyle='',
                          y_on_right=True)
    
    # Create the RSI panel
    rsi_panel = mpf.make_addplot(df['RSI'], panel=1, color='blue', title='RSI',
                                secondary_y=False)
    
    # Add RSI levels at 70 and 30
    overbought = pd.Series(70, index=df.index)
    oversold = pd.Series(30, index=df.index)
    ob_line = mpf.make_addplot(overbought, panel=1, color='red', secondary_y=False, linestyle='--')
    os_line = mpf.make_addplot(oversold, panel=1, color='green', secondary_y=False, linestyle='--')
    
    # Create the candlestick chart with RSI and save to buffer
    mpf.plot(df,
             type='candle',
             title='EUR/USD Candlestick Chart with RSI (M1)',
             ylabel='Price',
             volume=False,
             style=s,
             figsize=(15, 10),
             addplot=[rsi_panel, ob_line, os_line],
             panel_ratios=(2,1),
             savefig=buf)
    
    # Convert buffer to base64
    buf.seek(0)
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    
    return image_base64

def send_to_api(base64_image):
    try:
        # Prepare the JSON payload
        payload = {
            "image": base64_image,
            "timestamp": datetime.now().isoformat(),
            "symbol": "EURUSD",
            "timeframe": "M1"
        }
        
        # Send to API
        headers = {'Content-Type': 'application/json'}
        response = requests.post(upload_url, json=payload, headers=headers)
        response.raise_for_status()
        
        print("Successfully sent chart to API")
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"Error sending to API: {e}")
        return None

def main():
    # Fetch data
    df = fetch_ohlc_data()
    
    if df is not None:
        # Generate chart and get base64
        base64_image = plot_candlestick(df)
        
        # Save base64 to file (optional)
        with open('chart_base64.txt', 'w') as f:
            f.write(base64_image)
        
        # Send to API
        api_response = send_to_api(base64_image)
        if api_response:
            print("API Response:", api_response)
    else:
        print("Failed to create chart due to data fetching error.")

if __name__ == "__main__":
    main() 