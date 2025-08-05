import pandas as pd
import plotly.graph_objects as go

#loads CSV
df = pd.read_csv("AMD.csv", parse_dates=["Date"])

df['Close/Last'] = df['Close/Last'].str.replace('$', '', regex=False).astype(float) #turns to float

df.set_index("Date", inplace=True)

#calculate rolling mean and std dev, then Z-score
window = 30
df["Rolling_Mean"] = df["Close/Last"].rolling(window).mean()
df["Rolling_Std"] = df["Close/Last"].rolling(window).std()
df["Z_Score"] = (df["Close/Last"] - df["Rolling_Mean"]) / df["Rolling_Std"]

#### STRATEGY LOGIC ####
#enter long when price is low (Z-score < -1.5)
df["Long_Entry"] = df["Z_Score"] < -1.5
#exit long when price is high(Z-score > 1)
df["Long_Exit"] = df["Z_Score"] > 0

#short when price is high (Z-score > 1.5)
df["Short_Entry"] = df["Z_Score"] > 1.5
#exit short when price is low (Z-score < -1)
df["Short_Exit"] = df["Z_Score"] < -1

#### SIMULATION LOGIC ####
#trades half of balance each time

initial_balance = 1000
balance = initial_balance
position = 0  #0 = no position, 1 = long, -1 = short
entry_price = 0
shares = 0
portfolio_values = []
positions = []

for i in range(len(df)):
    price = df["Close/Last"].iloc[i]
    #Calculate portfolio value for this day
    if position == 1:
        portfolio_values.append(balance + shares * price)
    elif position == -1:
        portfolio_values.append(balance - shares * price)
    else:
        portfolio_values.append(balance)

#### TRADE LOGIC ####
    if position == 0:
        if df["Long_Entry"].iloc[i]:
            position = 1
            entry_price = price
            trade_amount = balance * 0.5
            shares = trade_amount / price
            balance -= trade_amount
        elif df["Short_Entry"].iloc[i]:
            position = -1
            entry_price = price
            trade_amount = balance * 0.5
            shares = trade_amount / price
            balance += trade_amount  #receive cash from short sale
    elif position == 1:
        if df["Long_Exit"].iloc[i]:
            position = 0
            exit_price = price
            balance += shares * exit_price
            shares = 0
    elif position == -1:
        if df["Short_Exit"].iloc[i]:
            position = 0
            exit_price = price
            balance -= shares * exit_price  #buy back shares
            shares = 0
    positions.append(position)

#fill portfolio_values for any missing days
while len(portfolio_values) < len(df):
    portfolio_values.append(balance + shares * df["Close/Last"].iloc[-1] if position == 1 else
                            balance - shares * df["Close/Last"].iloc[-1] if position == -1 else
                            balance)

df["Portfolio_Value"] = portfolio_values
df["Position"] = positions



#graph 1
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 4))
plt.plot(df.index, df["Portfolio_Value"], label="Portfolio Value ($)")
plt.title("Z-Score Mean Reversion Strategy (Simulated $1000, Half per Trade)")
plt.grid()
plt.legend()
plt.show()

#####

#graph 2
from plotly.subplots import make_subplots

fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                    vertical_spacing=0.1,
                    subplot_titles=("Price with Moving Average", "Z-Score"))

#candlestick plot for price
fig.add_trace(go.Candlestick(x=df.index,
                             open=df["Open"],
                             high=df["High"],
                             low=df["Low"],
                             close=df["Close/Last"],
                             name="Price"), row=1, col=1)

#rolling mean line
fig.add_trace(go.Scatter(x=df.index, y=df["Rolling_Mean"],
                         mode="lines",
                         line=dict(color="orange", width=2),
                         name=f"{window}-Day MA"), row=1, col=1)

#plot Z-score
fig.add_trace(go.Scatter(x=df.index, y=df["Z_Score"],
                         mode="lines",
                         line=dict(color="green", width=2),
                         name="Z-Score"), row=2, col=1)

#add horizontal lines for thresholds on Z-score plot
fig.add_hline(y=0, line_dash="dash", line_color="black", row=2, col=1)
fig.add_hline(y=1.5, line_dash="dash", line_color="red", row=2, col=1)
fig.add_hline(y=-1.5, line_dash="dash", line_color="red", row=2, col=1)

fig.update_layout(height=1050, width=1900, title_text="Stock Price & Z-Score Analysis")
fig.update_xaxes(rangeslider_visible=False)

fig.show()