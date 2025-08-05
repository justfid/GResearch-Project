import pandas as pd
import pyarrow as pa
import pyarrow.csv as csv   
import polars as pl
import plotly.graph_objects as go

import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Load data using Pandas
amdData = pd.read_csv('AMD.csv')
metaData = pd.read_csv('META.csv')
msftData = pd.read_csv('MSFT.csv')
sbuxData = pd.read_csv('SBUX.csv')

# Ensure 'Date' column is in datetime format
amdData['Date'] = pd.to_datetime(amdData['Date'])

# Remove dollar sign and convert 'Close/Last' to numeric
amdData['Close/Last'] = amdData['Close/Last'].str.replace('$', '').astype(float)

# Calculate rolling averages using Pandas
amdData['rolling50'] = amdData['Close/Last'].rolling(window=50).mean()
amdData['rolling20'] = amdData['Close/Last'].rolling(window=20).mean()

# Candlestick graph with rolling averages
fig = go.Figure(data=[
    go.Candlestick(
        x=amdData['Date'],
        open=amdData['Open'],
        high=amdData['High'],
        low=amdData['Low'],
        close=amdData['Close/Last'],
        name='Candlestick'
    ),
    go.Scatter(
        x=amdData['Date'],
        y=amdData['rolling50'],
        mode='lines',
        name='50-Day Rolling Average',
        line=dict(color='blue')
    ),
    go.Scatter(
        x=amdData['Date'],
        y=amdData['rolling20'],
        mode='lines',
        name='20-Day Rolling Average',
        line=dict(color='orange')
    )
])

# Update layout
fig.update_layout(
    title='AMD Stock Price with Rolling Averages',
    xaxis_title='Date',
    yaxis_title='Price (USD)',
    xaxis_rangeslider_visible=False,
    autosize=False,
    width=700,
    height=500,
    showlegend=True
)

fig.show()