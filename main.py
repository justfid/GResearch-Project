import pandas as pd
import plotly.graph_objects as go

# Load CSV (make sure you have columns: Date, Open, High, Low, Close)
df = pd.read_csv("AMD.csv", parse_dates=["Date"])

df['Close/Last'] = df['Close/Last'].str.replace('$', '', regex=False).astype(float)

df.set_index("Date", inplace=True)

# Sort the DataFrame by index (Date) in ascending order
df = df.sort_index(ascending=True)

# Calculate rolling mean and std dev, then Z-score
window = 20
df["Rolling_Mean"] = df["Close/Last"].rolling(window).mean()
df["Rolling_Std"] = df["Close/Last"].rolling(window).std()
df["Z_Score"] = (df["Close/Last"] - df["Rolling_Mean"]) / df["Rolling_Std"]

############

# Buy when price is far below average (Z-score < -1.5)
df["Long_Entry"] = df["Z_Score"] < -1.5
# Exit long when price returns to average (Z-score > 0)
df["Long_Exit"] = df["Z_Score"] > 0.5

# Short when price is far above average (Z-score > 1.5)
df["Short_Entry"] = df["Z_Score"] > 1.5
# Exit short when price returns to average (Z-score < 0)
df["Short_Exit"] = df["Z_Score"] < -0.5

initial_balance = 1000
balance = initial_balance
position = 0  # 0 = no position, 1 = long, -1 = short
entry_price = 0
shares = 0
portfolio_values = []
positions = []

for i in range(len(df)):
    price = df["Close/Last"].iloc[i]
    # Always mark to market, even if flat
    portfolio_values.append(
        balance + shares * price if position == 1 else
        balance - shares * price if position == -1 else
        balance
    )

    # Trading logic
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
            balance += trade_amount  # Receive cash from short sale
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
            balance -= shares * exit_price  # Buy back shares
            shares = 0
    positions.append(position)

# Force close any open position at the last price
last_price = df["Close/Last"].iloc[-1]
if position == 1 and shares > 0:
    balance += shares * last_price
    shares = 0
    position = 0
    print("Force-closed long at end.")
elif position == -1 and shares > 0:
    balance -= shares * last_price
    shares = 0
    position = 0
    print("Force-closed short at end.")

# Update final portfolio value to reflect forced close
portfolio_values[-1] = balance

df["Portfolio_Value"] = portfolio_values
df["Position"] = positions

print(f"Final balance: {balance:.2f}")
print(f"Final shares: {shares:.4f}")
print(f"Final position: {position}")

import matplotlib.pyplot as plt

plt.figure(figsize=(10, 4))
plt.plot(df.index, df["Portfolio_Value"], label="Portfolio Value ($)")
plt.title("Z-Score Mean Reversion Strategy (Simulated $1000, Half per Trade)")
plt.grid()
plt.legend()
plt.show()

#####



# Create figure with subplots (price + MA on top, Z-score below)
from plotly.subplots import make_subplots

fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                    vertical_spacing=0.1,
                    subplot_titles=("Price with Moving Average", "Z-Score"))

# Find buy (long entry) and sell (short entry) signal indices
buy_signals = df[df["Long_Entry"]].index
buy_prices = df.loc[buy_signals, "Close/Last"]

sell_signals = df[df["Short_Entry"]].index
sell_prices = df.loc[sell_signals, "Close/Last"]

# Candlestick plot for price
fig.add_trace(go.Candlestick(x=df.index,
                             open=df["Open"],
                             high=df["High"],
                             low=df["Low"],
                             close=df["Close/Last"],
                             name="Price"), row=1, col=1)

# Add rolling mean line
fig.add_trace(go.Scatter(x=df.index, y=df["Rolling_Mean"],
                         mode="lines",
                         line=dict(color="orange", width=2),
                         name=f"{window}-Day MA"), row=1, col=1)

# Add buy signals (green triangle-up)
fig.add_trace(go.Scatter(
    x=buy_signals,
    y=buy_prices,
    mode="markers",
    marker=dict(symbol="triangle-up", color="green", size=12),
    name="Buy Signal"
), row=1, col=1)

# Add sell signals (red triangle-down)
fig.add_trace(go.Scatter(
    x=sell_signals,
    y=sell_prices,
    mode="markers",
    marker=dict(symbol="triangle-down", color="red", size=12),
    name="Sell Signal"
), row=1, col=1)

# Plot Z-score
fig.add_trace(go.Scatter(x=df.index, y=df["Z_Score"],
                         mode="lines",
                         line=dict(color="green", width=2),
                         name="Z-Score"), row=2, col=1)

# Add horizontal lines for thresholds on Z-score plot
fig.add_hline(y=0, line_dash="dash", line_color="black", row=2, col=1)
fig.add_hline(y=1.5, line_dash="dash", line_color="red", row=2, col=1)
fig.add_hline(y=-1.5, line_dash="dash", line_color="red", row=2, col=1)

# Update layout
fig.update_layout(height=1050, width=1900, title_text="Stock Price & Z-Score Analysis")
fig.update_xaxes(rangeslider_visible=False)

fig.show()
