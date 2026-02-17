from trade_engine.core.stock_visualizer import StockVisualizer
from trade_engine.config.visualization_config import (
    VALID_PERIODS, VALID_INTERVALS, AVAILABLE_INDICATORS
)


class VisualizationMenu:
    """CLI menu for stock visualization features."""

    def __init__(self, interface):
        self.interface = interface
        self.visualizer = StockVisualizer()

    def show(self):
        """Display the visualization sub-menu."""
        while True:
            menu_options = [
                "Candlestick Chart",
                "Line Chart",
                "Technical Indicators",
                "Compare Stocks",
                "Back to Main Menu"
            ]

            choice = self.interface.show_menu(menu_options, "Stock Visualization")

            if choice == "Candlestick Chart":
                self._candlestick_chart()
            elif choice == "Line Chart":
                self._line_chart()
            elif choice == "Technical Indicators":
                self._technical_indicators()
            elif choice == "Compare Stocks":
                self._compare_stocks()
            elif choice == "Back to Main Menu":
                return

    def _get_symbol(self):
        return self.interface.input_prompt("Enter stock symbol (e.g. RELIANCE.NS): ")

    def _get_period(self):
        self.interface.print_info(f"Valid periods: {', '.join(VALID_PERIODS)}")
        period = self.interface.input_prompt("Enter period [1mo]: ") or "1mo"
        if period not in VALID_PERIODS:
            self.interface.print_error(f"Invalid period. Using '1mo'.")
            period = "1mo"
        return period

    def _get_interval(self):
        self.interface.print_info(f"Valid intervals: {', '.join(VALID_INTERVALS)}")
        interval = self.interface.input_prompt("Enter interval [1d]: ") or "1d"
        if interval not in VALID_INTERVALS:
            self.interface.print_error(f"Invalid interval. Using '1d'.")
            interval = "1d"
        return interval

    def _select_indicators(self):
        """Let user pick multiple indicators."""
        self.interface.print_info("Available indicators:")
        indicator_keys = list(AVAILABLE_INDICATORS.keys())
        for idx, key in enumerate(indicator_keys, 1):
            self.interface.console.print(f"  [green]{idx}.[/green] {key} - {AVAILABLE_INDICATORS[key]}")
        self.interface.console.print(f"  [green]0.[/green] None")

        raw = self.interface.input_prompt("Select indicators (comma-separated numbers, e.g. 1,3,5): ")
        selected = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                num = int(part)
                if 1 <= num <= len(indicator_keys):
                    selected.append(indicator_keys[num - 1])
        return selected

    def _candlestick_chart(self):
        symbol = self._get_symbol()
        period = self._get_period()
        interval = self._get_interval()
        try:
            self.interface.show_loading(
                f"[bold cyan]Fetching data for {symbol}...[/bold cyan]",
                self.visualizer.plot_with_indicators,
                symbol, period, interval, [], "candlestick"
            )
        except Exception as e:
            self.interface.print_error(f"Error: {e}")

    def _line_chart(self):
        symbol = self._get_symbol()
        period = self._get_period()
        interval = self._get_interval()
        try:
            self.interface.show_loading(
                f"[bold cyan]Fetching data for {symbol}...[/bold cyan]",
                self.visualizer.plot_with_indicators,
                symbol, period, interval, [], "line"
            )
        except Exception as e:
            self.interface.print_error(f"Error: {e}")

    def _technical_indicators(self):
        symbol = self._get_symbol()
        period = self._get_period()
        interval = self._get_interval()
        indicators = self._select_indicators()
        if not indicators:
            self.interface.print_info("No indicators selected.")
            return
        try:
            self.interface.show_loading(
                f"[bold cyan]Fetching data and computing indicators for {symbol}...[/bold cyan]",
                self.visualizer.plot_with_indicators,
                symbol, period, interval, indicators, "candlestick"
            )
        except Exception as e:
            self.interface.print_error(f"Error: {e}")

    def _compare_stocks(self):
        symbol1 = self.interface.input_prompt("Enter first symbol: ")
        symbol2 = self.interface.input_prompt("Enter second symbol: ")
        period = self._get_period()
        interval = self._get_interval()
        try:
            df1 = self.interface.show_loading(
                f"[bold cyan]Fetching {symbol1}...[/bold cyan]",
                self.visualizer.fetch_historical_data,
                symbol1, period, interval
            )
            df2 = self.interface.show_loading(
                f"[bold cyan]Fetching {symbol2}...[/bold cyan]",
                self.visualizer.fetch_historical_data,
                symbol2, period, interval
            )
            if df1 is not None and df2 is not None:
                import plotext as plt
                plt.clear_figure()
                plt.theme("dark")
                plt.title(f"{symbol1} vs {symbol2} - Close Price")
                plt.xlabel("Date")
                plt.ylabel("Price")

                dates1 = list(range(len(df1)))
                dates2 = list(range(len(df2)))
                plt.plot(dates1, df1["Close"].tolist(), label=symbol1)
                plt.plot(dates2, df2["Close"].tolist(), label=symbol2)
                plt.show()
        except Exception as e:
            self.interface.print_error(f"Error: {e}")


