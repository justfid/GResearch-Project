import numpy as np
import polars as pl
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

amdData = pl.read_csv('AMD.csv')
metaData = pl.read_csv('META.csv')
msftData = pl.read_csv('MSFT.csv')
sbuxData = pl.read_csv('SBUX.csv')




fig = go.Figure(data=[go.Candlestick(x=amdData['Date'],
                open=amdData['Open'],
                high=amdData['High'],
                low=amdData['Low'],
                close=amdData['Close/Last'])])

fig.show()