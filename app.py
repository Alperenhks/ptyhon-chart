import matplotlib
matplotlib.use('Agg')  # Use Agg backend
import requests
import pandas as pd
import mplfinance as mpf
import numpy as np
from datetime import datetime
import io
import base64
from flask import Flask, jsonify

app = Flask(__name__)

# API URL for OHLC data
data_url = "https://eximus.net/api/api/v1/ohlc/EURUSD?timeframe=H1&count=100"

def calculate_rsi(data, periods=14):
    # Calculate price changes
    close_delta = data['Close'].diff()
    
    # Make two series: one for lower closes and one for higher closes
    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)
    
    # Calculate the EWMA
    ma_up = up.ewm(com=periods-1, adjust=True, min_periods=periods).mean()
    ma_down = down.ewm(com=periods-1, adjust=True, min_periods=periods).mean()
    
    rsi = ma_up / ma_down
    rsi = 100 - (100/(1 + rsi))
    return rsi

def fetch_ohlc_data():
    try:
        response = requests.get(data_url)
        response.raise_for_status()
        data = response.json()
        
        df = pd.DataFrame(data)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        
        df = df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        })
        
        df['RSI'] = calculate_rsi(df)
        return df
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def generate_chart(df):
    buf = io.BytesIO()
    
    # Define TradingView Light theme colors
    bg_color = '#FFFFFF'
    text_color = '#131722'
    grid_color = '#E0E3EB'
    border_color = '#B2B5BE'
    
    # Define custom style for candles
    mc = mpf.make_marketcolors(
        up='#089981',          # Green for up candles
        down='#F23645',        # Red for down candles
        edge='inherit',        # Edge color same as candle color
        wick='inherit',        # Wick color same as candle color
        volume='in',           # Volume colors same as candle colors
        ohlc='inherit'
    )
    
    # Create custom style
    s = mpf.make_mpf_style(
        marketcolors=mc,
        figcolor=bg_color,
        facecolor=bg_color,
        edgecolor=border_color,
        gridcolor=grid_color,
        gridstyle=':',         # Dotted grid
        gridaxis='both',
        y_on_right=True,
        rc={
            'axes.labelcolor': text_color,
            'axes.edgecolor': border_color,
            'xtick.color': text_color,
            'ytick.color': text_color,
            'figure.facecolor': bg_color,
            'axes.facecolor': bg_color,
            'axes.grid': True,
            'grid.alpha': 0.3
        }
    )
    
    # Calculate moving averages
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    # Create the RSI panel with custom colors
    rsi_panel = mpf.make_addplot(df['RSI'], panel=1, color='#787B86', title='RSI',
                                secondary_y=False, width=0.8)
    
    # Add moving averages
    ema20 = mpf.make_addplot(df['EMA20'], color='#2962FF', width=0.8)  # Blue
    ema50 = mpf.make_addplot(df['EMA50'], color='#FF6B00', width=0.8)  # Orange
    
    # Add RSI levels with custom colors
    overbought = pd.Series(70, index=df.index)
    oversold = pd.Series(30, index=df.index)
    ob_line = mpf.make_addplot(overbought, panel=1, color='#F23645', secondary_y=False,
                              linestyle='--', alpha=0.3)
    os_line = mpf.make_addplot(oversold, panel=1, color='#089981', secondary_y=False,
                              linestyle='--', alpha=0.3)
    
    # Create the chart with custom configuration
    fig, axes = mpf.plot(
        df,
        type='candle',
        style=s,
        title='EUR/USD',
        ylabel='Price',
        volume=False,
        figsize=(15, 10),
        addplot=[ema20, ema50, rsi_panel, ob_line, os_line],
        panel_ratios=(2,1),
        tight_layout=True,
        returnfig=True
    )
    
    # Customize title
    axes[0].set_title('EUR/USD (M1)', color=text_color, fontsize=14, pad=20)
    
    # Save figure to buffer
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor=bg_color)
    
    # Convert to base64
    buf.seek(0)
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    
    return image_base64

@app.route('/get_chart', methods=['GET'])
def get_chart():
    try:
        df = fetch_ohlc_data()
        if df is not None:
            chart_base64 = generate_chart(df)
            return jsonify({
                'status': 'success',
                'data': {
                    'image': chart_base64,
                    'timestamp': datetime.now().isoformat(),
                    'symbol': 'EURUSD',
                    'timeframe': 'M1'
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to fetch OHLC data'
            }), 500
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001) 