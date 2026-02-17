import yfinance as yf
import pandas as pd
import plotext as plt
import ta


class StockVisualizer:
    """Terminal-based stock visualization with technical indicators."""

    def fetch_historical_data(self, symbol, period="1mo", interval="1d"):
        """Fetch historical OHLCV data from Yahoo Finance."""
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            raise ValueError(f"No data found for symbol '{symbol}'")
        return df

    def plot_candlestick(self, df, symbol, show_volume=True):
        """Render a candlestick chart in the terminal using plotext."""
        plt.clear_figure()
        plt.theme("dark")
        plt.title(f"{symbol} Candlestick Chart")
        plt.xlabel("Date")
        plt.ylabel("Price")

        dates = list(range(len(df)))
        opens = df["Open"].tolist()
        closes = df["Close"].tolist()
        highs = df["High"].tolist()
        lows = df["Low"].tolist()

        plt.candlestick(dates, {"Open": opens, "Close": closes, "High": highs, "Low": lows})

        # Set date labels on x-axis
        date_labels = [d.strftime("%m-%d") if hasattr(d, "strftime") else str(d) for d in df.index]
        step = max(1, len(date_labels) // 10)
        plt.xticks(dates[::step], date_labels[::step])

        plt.show()

        if show_volume:
            plt.clear_figure()
            plt.theme("dark")
            plt.title(f"{symbol} Volume")
            plt.xlabel("Date")
            plt.ylabel("Volume")
            plt.bar(dates, df["Volume"].tolist())
            plt.xticks(dates[::step], date_labels[::step])
            plt.show()

    def plot_line_chart(self, df, symbol, column="Close"):
        """Render a simple line chart in the terminal."""
        plt.clear_figure()
        plt.theme("dark")
        plt.title(f"{symbol} - {column}")
        plt.xlabel("Date")
        plt.ylabel(column)

        dates = list(range(len(df)))
        plt.plot(dates, df[column].tolist(), label=column)

        date_labels = [d.strftime("%m-%d") if hasattr(d, "strftime") else str(d) for d in df.index]
        step = max(1, len(date_labels) // 10)
        plt.xticks(dates[::step], date_labels[::step])
        plt.show()

    def add_sma(self, df, period=20):
        """Add Simple Moving Average to DataFrame."""
        col = f"SMA_{period}"
        df[col] = ta.trend.sma_indicator(df["Close"], window=period)
        return df

    def add_ema(self, df, period=20):
        """Add Exponential Moving Average to DataFrame."""
        col = f"EMA_{period}"
        df[col] = ta.trend.ema_indicator(df["Close"], window=period)
        return df

    def add_bollinger_bands(self, df, period=20, std_dev=2):
        """Add Bollinger Bands to DataFrame."""
        bb = ta.volatility.BollingerBands(df["Close"], window=period, window_dev=std_dev)
        df["BB_Upper"] = bb.bollinger_hband()
        df["BB_Middle"] = bb.bollinger_mavg()
        df["BB_Lower"] = bb.bollinger_lband()
        return df

    def add_rsi(self, df, period=14):
        """Add RSI to DataFrame."""
        df["RSI"] = ta.momentum.rsi(df["Close"], window=period)
        return df

    def add_macd(self, df, fast=12, slow=26, signal=9):
        """Add MACD to DataFrame."""
        macd = ta.trend.MACD(df["Close"], window_fast=fast, window_slow=slow, window_sign=signal)
        df["MACD"] = macd.macd()
        df["MACD_Signal"] = macd.macd_signal()
        df["MACD_Hist"] = macd.macd_diff()
        return df

    def plot_with_indicators(self, symbol, period="1mo", interval="1d", indicators=None, chart_type="candlestick"):
        """Main method: fetch data, compute indicators, and plot."""
        df = self.fetch_historical_data(symbol, period, interval)
        indicators = indicators or []

        for ind in indicators:
            if ind == "SMA":
                df = self.add_sma(df)
            elif ind == "EMA":
                df = self.add_ema(df)
            elif ind == "Bollinger":
                df = self.add_bollinger_bands(df)
            elif ind == "RSI":
                df = self.add_rsi(df)
            elif ind == "MACD":
                df = self.add_macd(df)

        # Main price chart
        if chart_type == "candlestick":
            self.plot_candlestick(df, symbol, show_volume=True)
        else:
            self.plot_line_chart(df, symbol)

        dates = list(range(len(df)))
        date_labels = [d.strftime("%m-%d") if hasattr(d, "strftime") else str(d) for d in df.index]
        step = max(1, len(date_labels) // 10)

        # Overlay moving averages / Bollinger
        overlay_cols = [c for c in df.columns if c.startswith(("SMA_", "EMA_", "BB_"))]
        if overlay_cols:
            plt.clear_figure()
            plt.theme("dark")
            plt.title(f"{symbol} Price + Overlays")
            plt.xlabel("Date")
            plt.ylabel("Price")
            plt.plot(dates, df["Close"].tolist(), label="Close")
            for col in overlay_cols:
                vals = df[col].dropna()
                idx = [dates[i] for i in vals.index.map(lambda x: df.index.get_loc(x))]
                plt.plot(idx, vals.tolist(), label=col)
            plt.xticks(dates[::step], date_labels[::step])
            plt.show()

        # RSI subplot
        if "RSI" in df.columns:
            plt.clear_figure()
            plt.theme("dark")
            plt.title(f"{symbol} RSI")
            plt.xlabel("Date")
            plt.ylabel("RSI")
            rsi_vals = df["RSI"].dropna()
            rsi_idx = [dates[i] for i in rsi_vals.index.map(lambda x: df.index.get_loc(x))]
            plt.plot(rsi_idx, rsi_vals.tolist(), label="RSI")
            plt.hline(70, "red")
            plt.hline(30, "green")
            plt.xticks(dates[::step], date_labels[::step])
            plt.show()

        # MACD subplot
        if "MACD" in df.columns:
            plt.clear_figure()
            plt.theme("dark")
            plt.title(f"{symbol} MACD")
            plt.xlabel("Date")
            plt.ylabel("MACD")
            macd_vals = df["MACD"].dropna()
            sig_vals = df["MACD_Signal"].dropna()
            macd_idx = [dates[i] for i in macd_vals.index.map(lambda x: df.index.get_loc(x))]
            sig_idx = [dates[i] for i in sig_vals.index.map(lambda x: df.index.get_loc(x))]
            plt.plot(macd_idx, macd_vals.tolist(), label="MACD")
            plt.plot(sig_idx, sig_vals.tolist(), label="Signal")
            plt.xticks(dates[::step], date_labels[::step])
            plt.show()

        return df


