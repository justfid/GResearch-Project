import numpy as np
import polars as pl
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime

amdData = pl.read_csv('AMD.csv')
metaData = pl.read_csv('META.csv')
msftData = pl.read_csv('MSFT.csv')
sbuxData = pl.read_csv('SBUX.csv')

#candlestick graph
# fig = go.Figure(data=[go.Candlestick(x=amdData['Date'],
#                 open=amdData['Open'],
#                 high=amdData['High'],
#                 low=amdData['Low'],
#                 close=amdData['Close/Last'])])

# fig.show()

###
selectedData = amdData.select(['Date', 'Close/Last'])

signal = dict()
dates = selectedData["Date"].to_list()
close_last = selectedData["Close/Last"].to_list()

for d in range(1, len(dates)):
    if close_last[d] > close_last[d-1]:
        signal[dates[d]] = 1
    else:
        signal[dates[d]] = 0

print(signal)
