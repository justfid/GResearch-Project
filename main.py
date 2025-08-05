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
filtered_df = amdData.filter(pl.col('Date') > "06/01/2025")
selectedData = filtered_df.select(['Date', 'Close/Last'])



signal = []
dates = []



for d in range(1, len(selectedData["Date"])):
    if selectedData["Close/Last"][d] > selectedData["Close/Last"][d-1]:
        signal.append(1)

    else:
        dates.append(selectedData["Date"])
        signal.append(0)

print(dates)

print(signal)



# if P(t) > P(t-1):
#     signal(t+1) = 1 
# else:
#     signal(t+1) 0

