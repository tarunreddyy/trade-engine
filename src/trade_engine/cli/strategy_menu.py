from trade_engine.core.stock_visualizer import StockVisualizer
from trade_engine.core.live_trading_console import LiveTradingConsole
from trade_engine.strategies import STRATEGY_DETAILS, STRATEGY_REGISTRY
from trade_engine.strategies.strategy_combiner import StrategyCombiner
from trade_engine.strategies.backtester import Backtester
from trade_engine.engine.portfolio_rebalancer import PortfolioRebalancer
from trade_engine.engine.recommendation_engine import RecommendationEngine
from trade_engine.engine.strategy_leaderboard import StrategyLeaderboard
from trade_engine.config.market_universe import DEFAULT_SCAN_UNIVERSE
from trade_engine.config.strategy_config import STRATEGY_DEFAULTS, COMBINE_MODES, DEFAULT_INITIAL_CAPITAL
from trade_engine.config.trading_config import (
    get_kill_switch_enabled,
    get_live_default_mode,
    get_live_default_max_position_pct,
    get_live_market_hours_only,
    get_live_max_orders_per_day,
    get_live_default_refresh_seconds,
    get_live_default_risk_per_trade_pct,
    get_live_default_stop_loss_pct,
    get_live_default_take_profit_pct,
    set_kill_switch_enabled,
    set_live_default_max_position_pct,
    set_live_market_hours_only,
    set_live_max_orders_per_day,
    set_live_default_mode,
    set_live_default_refresh_seconds,
    set_live_default_risk_per_trade_pct,
    set_live_default_stop_loss_pct,
    set_live_default_take_profit_pct,
)
import yfinance as yf


class StrategyMenu:
    """CLI menu for trading strategies and backtesting."""

    def __init__(self, interface, broker=None):
        self.interface = interface
        self.broker = broker
        self.visualizer = StockVisualizer()
        self.backtester = Backtester()
        self.rebalancer = PortfolioRebalancer()
        self.leaderboard = StrategyLeaderboard()
        self.recommendation_engine = RecommendationEngine()
        self.live_console = LiveTradingConsole(
            interface=self.interface,
            broker=self.broker,
            initial_capital=DEFAULT_INITIAL_CAPITAL,
        )
        self._apply_live_defaults()
        self.current_strategy = None
        self.current_strategy_name = None

    def _apply_live_defaults(self):
        self.live_console.router.set_mode(get_live_default_mode())
        self.live_console.risk_config.stop_loss_pct = get_live_default_stop_loss_pct() / 100.0
        self.live_console.risk_config.take_profit_pct = get_live_default_take_profit_pct() / 100.0
        self.live_console.risk_config.risk_per_trade_pct = get_live_default_risk_per_trade_pct() / 100.0
        self.live_console.risk_config.max_position_pct = get_live_default_max_position_pct() / 100.0
        self.live_console.risk_config.kill_switch_enabled = get_kill_switch_enabled()
        self.live_console.risk_config.market_hours_only = get_live_market_hours_only()
        self.live_console.risk_config.max_orders_per_day = get_live_max_orders_per_day()

    def show(self):
        """Display the strategy sub-menu."""
        while True:
            menu_options = [
                "Select Strategy",
                "Configure Parameters",
                "Run Signals on Stock",
                "Backtest Strategy",
                "Combine Strategies",
                "Stock Recommendations (20-25)",
                "Portfolio Rebalancer",
                "Strategy Leaderboard (Auto)",
                "Live Trading Console",
                "Back to Main Menu"
            ]

            choice = self.interface.show_menu(menu_options, "Trading Strategies")

            if choice == "Select Strategy":
                self._select_strategy()
            elif choice == "Configure Parameters":
                self._configure_params()
            elif choice == "Run Signals on Stock":
                self._run_signals()
            elif choice == "Backtest Strategy":
                self._backtest()
            elif choice == "Combine Strategies":
                self._combine_strategies()
            elif choice == "Stock Recommendations (20-25)":
                self._recommend_stocks()
            elif choice == "Portfolio Rebalancer":
                self._run_portfolio_rebalancer()
            elif choice == "Strategy Leaderboard (Auto)":
                self._run_strategy_leaderboard()
            elif choice == "Live Trading Console":
                self._run_live_console()
            elif choice == "Back to Main Menu":
                return

    def _select_strategy(self):
        names = list(STRATEGY_REGISTRY.keys())
        choice = self.interface.show_menu(names + ["Back"], "Select a Strategy")
        if choice == "Back":
            return
        cls = STRATEGY_REGISTRY[choice]
        # Use default params
        key = choice.replace(" ", "_")
        defaults = STRATEGY_DEFAULTS.get(key, {})
        self.current_strategy = cls(**defaults)
        self.current_strategy_name = choice
        self.interface.print_success(f"Selected: {choice}")
        self.interface.console.print(f"  {self.current_strategy.get_description()}")
        metadata = STRATEGY_DETAILS.get(choice)
        if metadata:
            self.interface.console.print(
                f"  Category: {metadata.category} | Risk: {metadata.risk_profile} | Timeframe: {metadata.preferred_timeframe}"
            )

    def _configure_params(self):
        if not self.current_strategy:
            self.interface.print_error("No strategy selected. Select one first.")
            return

        self.interface.print_info(f"Current: {self.current_strategy.get_description()}")
        self.interface.print_info("Enter new parameter values (leave blank to keep current):")

        cls = type(self.current_strategy)
        init_params = cls.__init__.__code__.co_varnames[1:cls.__init__.__code__.co_argcount]
        new_kwargs = {}
        for param in init_params:
            current_val = getattr(self.current_strategy, param, None)
            raw = self.interface.input_prompt(f"  {param} [{current_val}]: ")
            if raw.strip():
                try:
                    if isinstance(current_val, float):
                        new_kwargs[param] = float(raw)
                    elif isinstance(current_val, int):
                        new_kwargs[param] = int(raw)
                    else:
                        new_kwargs[param] = raw
                except ValueError:
                    self.interface.print_error(f"Invalid value for {param}, keeping {current_val}")
                    new_kwargs[param] = current_val
            else:
                new_kwargs[param] = current_val

        self.current_strategy = cls(**new_kwargs)
        self.interface.print_success("Parameters updated.")
        self.interface.console.print(f"  {self.current_strategy.get_description()}")

    def _run_signals(self):
        if not self.current_strategy:
            self.interface.print_error("No strategy selected. Select one first.")
            return

        symbol = self.interface.input_prompt("Enter stock symbol (e.g. TCS.NS): ")
        period = self.interface.input_prompt("Enter period [3mo]: ") or "3mo"
        interval = self.interface.input_prompt("Enter interval [1d]: ") or "1d"

        try:
            df = self.interface.show_loading(
                f"[bold cyan]Fetching data for {symbol}...[/bold cyan]",
                self.visualizer.fetch_historical_data,
                symbol, period, interval
            )
            if df is None:
                return

            df = self.current_strategy.calculate_signals(df)

            # Show signals summary
            buys = df[df["signal"] == 1]
            sells = df[df["signal"] == -1]
            self.interface.print_info(f"Strategy: {self.current_strategy_name}")
            self.interface.print_info(f"Period: {period}, Interval: {interval}")
            self.interface.print_success(f"BUY signals: {len(buys)}")
            self.interface.print_error(f"SELL signals: {len(sells)}")

            if len(buys) > 0:
                self.interface.console.print("\n[bold green]BUY Signals:[/bold green]")
                for date, row in buys.iterrows():
                    self.interface.console.print(f"  {date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else date} - Close: {row['Close']:.2f}")

            if len(sells) > 0:
                self.interface.console.print("\n[bold red]SELL Signals:[/bold red]")
                for date, row in sells.iterrows():
                    self.interface.console.print(f"  {date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else date} - Close: {row['Close']:.2f}")

        except Exception as e:
            self.interface.print_error(f"Error: {e}")

    def _backtest(self):
        if not self.current_strategy:
            self.interface.print_error("No strategy selected. Select one first.")
            return

        symbol = self.interface.input_prompt("Enter stock symbol (e.g. TCS.NS): ")
        period = self.interface.input_prompt("Enter period [1y]: ") or "1y"
        capital_str = self.interface.input_prompt("Initial capital [100000]: ") or "100000"

        try:
            initial_capital = float(capital_str)
            df = self.interface.show_loading(
                f"[bold cyan]Fetching data for {symbol}...[/bold cyan]",
                self.visualizer.fetch_historical_data,
                symbol, period, "1d"
            )
            if df is None:
                return

            results = self.interface.show_loading(
                "[bold cyan]Running backtest...[/bold cyan]",
                self.backtester.run_backtest,
                df, self.current_strategy, initial_capital
            )

            if results:
                self.interface.console.print(f"\n[bold cyan]Backtest Results - {self.current_strategy_name}[/bold cyan]")
                self.interface.console.print(f"  Initial Capital:  {results['initial_capital']:,.2f}")
                self.interface.console.print(f"  Final Value:      {results['final_value']:,.2f}")

                ret_color = "green" if results['total_return'] >= 0 else "red"
                self.interface.console.print(f"  Total Return:     [{ret_color}]{results['total_return']}%[/{ret_color}]")
                self.interface.console.print(f"  Win Rate:         {results['win_rate']}%")
                self.interface.console.print(f"  Max Drawdown:     {results['max_drawdown']}%")
                self.interface.console.print(f"  Sharpe Ratio:     {results['sharpe_ratio']}")
                self.interface.console.print(f"  Total Trades:     {results['total_trades']}")
                self.interface.console.print(f"  Total Costs:      {results.get('total_costs', 0.0):,.2f}")

                # Show equity curve
                self.backtester.plot_equity_curve(results)

                # Show trade log
                if results["trade_log"]:
                    self.interface.display_response(results["trade_log"], "Trade Log")

        except Exception as e:
            self.interface.print_error(f"Error: {e}")

    def _combine_strategies(self):
        self.interface.print_info("Select strategies to combine:")
        names = list(STRATEGY_REGISTRY.keys())
        for idx, name in enumerate(names, 1):
            self.interface.console.print(f"  [green]{idx}.[/green] {name}")

        raw = self.interface.input_prompt("Select strategies (comma-separated numbers): ")
        selected = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                num = int(part)
                if 1 <= num <= len(names):
                    key = names[num - 1].replace(" ", "_")
                    defaults = STRATEGY_DEFAULTS.get(key, {})
                    strategy = STRATEGY_REGISTRY[names[num - 1]](**defaults)
                    selected.append(strategy)

        if len(selected) < 2:
            self.interface.print_error("Select at least 2 strategies to combine.")
            return

        mode = self.interface.show_menu(COMBINE_MODES + ["Back"], "Combine Mode")
        if mode == "Back":
            return

        combiner = StrategyCombiner(selected, mode=mode)
        self.current_strategy = combiner
        self.current_strategy_name = f"Combined ({mode})"
        self.interface.print_success(f"Combined {len(selected)} strategies in '{mode}' mode.")
        self.interface.print_info("You can now use 'Run Signals' or 'Backtest' with the combined strategy.")

    def _recommend_stocks(self):
        if not self.current_strategy:
            self.interface.print_error("No strategy selected. Select one first.")
            return

        self.interface.print_info(
            f"Scanning default universe of {len(DEFAULT_SCAN_UNIVERSE)} stocks for strategy signals."
        )
        top_n_raw = self.interface.input_prompt("Recommendations per side [25]: ") or "25"
        period = self.interface.input_prompt("Scan period [6mo]: ") or "6mo"
        interval = self.interface.input_prompt("Scan interval [1d]: ") or "1d"
        lookback_raw = self.interface.input_prompt("Signal recency bars [5]: ") or "5"

        try:
            top_n = max(1, min(25, int(top_n_raw)))
            lookback = max(1, int(lookback_raw))
        except ValueError:
            self.interface.print_error("Invalid numeric input.")
            return

        results = self.interface.show_loading(
            "[bold cyan]Running strategy scanner across universe...[/bold cyan]",
            self.recommendation_engine.recommend,
            self.current_strategy,
            DEFAULT_SCAN_UNIVERSE,
            top_n,
            period,
            interval,
            lookback,
        )
        if not results:
            self.interface.print_error("No recommendations generated.")
            return

        buy_data = results.get("buy", [])
        sell_data = results.get("sell", [])

        if not buy_data and not sell_data:
            self.interface.print_info("No fresh buy/sell signals found in the current scan.")
            return

        self.interface.display_side_by_side(
            buy_data if buy_data else [{"status": "No BUY signals"}],
            sell_data if sell_data else [{"status": "No SELL signals"}],
            left_title=f"BUY Recommendations (Top {top_n})",
            right_title=f"SELL Recommendations (Top {top_n})",
        )

    def _run_live_console(self):
        if not self.current_strategy:
            self.interface.print_error("No strategy selected. Select one first.")
            return

        self._apply_live_defaults()

        self.interface.print_info("Real-time CLI console controls can be changed while running.")
        default_symbols = "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS"
        symbols_raw = self.interface.input_prompt(f"Watchlist symbols CSV [{default_symbols}]: ") or default_symbols
        interval = self.interface.input_prompt("Bar interval [5m]: ") or "5m"
        period = self.interface.input_prompt("Data period [5d]: ") or "5d"
        default_refresh = get_live_default_refresh_seconds()
        default_mode = get_live_default_mode()
        default_sl = get_live_default_stop_loss_pct()
        default_tp = get_live_default_take_profit_pct()
        default_risk = get_live_default_risk_per_trade_pct()
        default_max_pos = get_live_default_max_position_pct()
        default_kill = get_kill_switch_enabled()
        default_hours = get_live_market_hours_only()
        default_max_orders = get_live_max_orders_per_day()
        refresh_raw = self.interface.input_prompt(f"Refresh seconds [{default_refresh}]: ") or str(default_refresh)
        mode_raw = self.interface.input_prompt(f"Execution mode (paper/live) [{default_mode}]: ") or default_mode

        sl_raw = self.interface.input_prompt(f"Stop-loss % [{default_sl}]: ") or str(default_sl)
        tp_raw = self.interface.input_prompt(f"Take-profit % [{default_tp}]: ") or str(default_tp)
        risk_raw = self.interface.input_prompt(f"Risk per trade % [{default_risk}]: ") or str(default_risk)
        maxpos_raw = self.interface.input_prompt(f"Max position % [{default_max_pos}]: ") or str(default_max_pos)
        kill_raw = self.interface.input_prompt(
            f"Kill switch (on/off) [{'on' if default_kill else 'off'}]: "
        ) or ("on" if default_kill else "off")
        hours_raw = self.interface.input_prompt(
            f"Market-hours guard (on/off) [{'on' if default_hours else 'off'}]: "
        ) or ("on" if default_hours else "off")
        max_orders_raw = self.interface.input_prompt(
            f"Max orders per day [{default_max_orders}]: "
        ) or str(default_max_orders)

        symbols = [item.strip().upper() for item in symbols_raw.split(",") if item.strip()]
        if not symbols:
            self.interface.print_error("Watchlist cannot be empty.")
            return

        try:
            refresh_seconds = max(3, int(refresh_raw))
            self.live_console.risk_config.stop_loss_pct = max(0.1, float(sl_raw)) / 100.0
            self.live_console.risk_config.take_profit_pct = max(0.1, float(tp_raw)) / 100.0
            self.live_console.risk_config.risk_per_trade_pct = max(0.1, float(risk_raw)) / 100.0
            self.live_console.risk_config.max_position_pct = max(1.0, float(maxpos_raw)) / 100.0
            self.live_console.risk_config.kill_switch_enabled = kill_raw.strip().lower() == "on"
            self.live_console.risk_config.market_hours_only = hours_raw.strip().lower() == "on"
            self.live_console.risk_config.max_orders_per_day = max(1, int(max_orders_raw))
        except ValueError:
            self.interface.print_error("Invalid numeric input for runtime configuration.")
            return

        mode = mode_raw.strip().lower()
        if mode not in {"paper", "live"}:
            self.interface.print_error("Invalid mode. Using paper mode.")
            mode = "paper"

        save_defaults = (self.interface.input_prompt("Save these values as CLI defaults? (y/N): ") or "n").strip().lower()
        if save_defaults in {"y", "yes"}:
            set_live_default_refresh_seconds(refresh_seconds)
            set_live_default_mode(mode)
            set_live_default_stop_loss_pct(self.live_console.risk_config.stop_loss_pct * 100.0)
            set_live_default_take_profit_pct(self.live_console.risk_config.take_profit_pct * 100.0)
            set_live_default_risk_per_trade_pct(self.live_console.risk_config.risk_per_trade_pct * 100.0)
            set_live_default_max_position_pct(self.live_console.risk_config.max_position_pct * 100.0)
            set_kill_switch_enabled(self.live_console.risk_config.kill_switch_enabled)
            set_live_market_hours_only(self.live_console.risk_config.market_hours_only)
            set_live_max_orders_per_day(self.live_console.risk_config.max_orders_per_day)
            self.interface.print_success("Live console defaults saved to CLI settings.")

        try:
            self.live_console.run(
                strategy=self.current_strategy,
                strategy_name=self.current_strategy_name,
                symbols=symbols,
                refresh_seconds=refresh_seconds,
                period=period,
                interval=interval,
                execution_mode=mode,
            )
        except KeyboardInterrupt:
            self.interface.print_info("Stopped live trading console.")
        except Exception as e:
            self.interface.print_error(f"Live console error: {e}")

    def _fetch_latest_prices(self, symbols):
        prices = {}
        for symbol in symbols:
            try:
                df = yf.download(
                    symbol,
                    period="5d",
                    interval="1d",
                    progress=False,
                    auto_adjust=False,
                    threads=False,
                )
                if df is None or df.empty:
                    continue
                if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
                    df.columns = [c[0] for c in df.columns]
                close = float(df["Close"].iloc[-1])
                prices[symbol.upper()] = close
            except Exception:
                continue
        return prices

    def _run_portfolio_rebalancer(self):
        restored = self.live_console.try_restore_saved_state()
        if restored:
            self.interface.print_info("Loaded saved session state for rebalancing context.")

        current_symbols = sorted(self.live_console.positions.keys())
        if current_symbols:
            self.interface.print_info(f"Current symbols in session: {', '.join(current_symbols)}")
        else:
            self.interface.print_info("No open positions in session state. Rebalancer can still build entry plan from cash.")

        target_raw = self.interface.input_prompt(
            "Target weights CSV (e.g. RELIANCE.NS=25,TCS.NS=20,INFY.NS=15): "
        )
        targets = self.rebalancer.parse_target_weights(target_raw)
        if not targets:
            self.interface.print_error("No valid target weights found.")
            return

        drift_raw = self.interface.input_prompt("Drift threshold % [2.0]: ") or "2.0"
        try:
            drift_threshold = max(0.1, float(drift_raw))
        except ValueError:
            self.interface.print_error("Invalid drift threshold.")
            return

        symbols = sorted(set(current_symbols) | set(targets.keys()))
        prices = self.interface.show_loading(
            "[bold cyan]Fetching latest prices for rebalance universe...[/bold cyan]",
            self._fetch_latest_prices,
            symbols,
        )
        if not prices:
            self.interface.print_error("Could not fetch prices for rebalance symbols.")
            return

        portfolio_state = self.live_console.get_portfolio_state(latest_prices=prices)
        plan = self.rebalancer.create_rebalance_plan(
            portfolio_state=portfolio_state,
            prices=prices,
            target_weights=targets,
            drift_threshold_pct=drift_threshold,
        )

        self.interface.print_info(plan.get("summary", "Rebalance plan generated."))
        self.interface.display_response(plan.get("allocations", []), "Current vs Target Allocation")

        actions = plan.get("actions", [])
        if not actions:
            self.interface.print_success("No rebalance trades needed under current drift threshold.")
            return

        self.interface.display_response(actions, "Rebalance Actions")
        execute = (self.interface.input_prompt("Execute these rebalance actions now? (y/N): ") or "n").strip().lower()
        if execute not in {"y", "yes"}:
            return

        results = self.interface.show_loading(
            "[bold cyan]Executing rebalance actions...[/bold cyan]",
            self.rebalancer.execute_plan,
            self.live_console,
            actions,
        )
        if results:
            self.interface.display_response(results, "Rebalance Execution Results")
            self.live_console.save_runtime_state(symbols)

    def _run_strategy_leaderboard(self):
        self.interface.print_info("Builds ranked performance across all registered strategies and chosen symbols.")
        universe_count_raw = self.interface.input_prompt("How many symbols from default universe? [25]: ") or "25"
        period = self.interface.input_prompt("Backtest period [1y]: ") or "1y"
        interval = self.interface.input_prompt("Backtest interval [1d]: ") or "1d"
        top_n_raw = self.interface.input_prompt("Top rows to display [25]: ") or "25"
        eval_mode_raw = self.interface.input_prompt("Evaluation mode (full/oos) [full]: ") or "full"
        windows_raw = self.interface.input_prompt("Walk-forward windows [3]: ") or "3"

        try:
            universe_count = max(5, min(len(DEFAULT_SCAN_UNIVERSE), int(universe_count_raw)))
            top_n = max(5, min(100, int(top_n_raw)))
            walk_forward_windows = max(1, int(windows_raw))
        except ValueError:
            self.interface.print_error("Invalid numeric input.")
            return

        oos_only = eval_mode_raw.strip().lower() == "oos"
        selected_universe = DEFAULT_SCAN_UNIVERSE[:universe_count]
        leaderboard = self.interface.show_loading(
            "[bold cyan]Computing strategy leaderboard across symbols...[/bold cyan]",
            self.leaderboard.build,
            selected_universe,
            period,
            interval,
            top_n,
            DEFAULT_INITIAL_CAPITAL,
            oos_only,
            walk_forward_windows,
        )
        if not leaderboard:
            self.interface.print_error("Leaderboard computation failed.")
            return

        self.interface.print_info(leaderboard.get("message", "Leaderboard complete."))
        rows = leaderboard.get("rows", [])
        summary = leaderboard.get("strategy_summary", [])

        if rows:
            self.interface.display_response(rows, "Top Strategy-Symbol Leaderboard Rows")
        else:
            self.interface.print_info("No leaderboard rows produced.")

        if summary:
            self.interface.display_response(summary, "Strategy Average Performance Ranking")


