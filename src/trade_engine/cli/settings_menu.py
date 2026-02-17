from trade_engine.brokers.sdk_manager import (
    get_broker_sdk_status,
    install_broker_sdk,
    list_broker_sdk_status,
)
from trade_engine.config.broker_config import SUPPORTED_BROKERS, get_active_broker, set_active_broker
from trade_engine.config.groww_config import (
    get_groww_access_token,
    get_groww_api_key,
    get_groww_api_secret,
    set_groww_access_token,
    set_groww_credentials,
)
from trade_engine.config.llm_config import (
    get_claude_api_key,
    get_gemini_api_key,
    get_llm_provider,
    get_openai_api_key,
    set_claude_api_key,
    set_gemini_api_key,
    set_llm_provider,
    set_openai_api_key,
)
from trade_engine.config.pinecone_config import (
    get_pinecone_api_key,
    get_pinecone_index_name_eq,
    set_pinecone_api_key,
    set_pinecone_index_name_eq,
)
from trade_engine.config.settings_store import (
    get_setting,
    get_settings_file,
    load_settings,
    mask_secret,
    save_settings,
    set_setting,
)
from trade_engine.config.trading_config import (
    get_kill_switch_enabled,
    get_live_auto_resume_session,
    get_live_dashboard_control_file,
    get_live_dashboard_port,
    get_live_dashboard_state_file,
    get_live_default_max_position_pct,
    get_live_default_mode,
    get_live_default_refresh_seconds,
    get_live_default_risk_per_trade_pct,
    get_live_default_stop_loss_pct,
    get_live_default_take_profit_pct,
    get_live_market_hours_only,
    get_live_max_orders_per_day,
    get_live_session_state_file,
    get_order_journal_file,
    set_kill_switch_enabled,
    set_live_auto_resume_session,
    set_live_dashboard_control_file,
    set_live_dashboard_port,
    set_live_dashboard_state_file,
    set_live_default_max_position_pct,
    set_live_default_mode,
    set_live_default_refresh_seconds,
    set_live_default_risk_per_trade_pct,
    set_live_default_stop_loss_pct,
    set_live_default_take_profit_pct,
    set_live_market_hours_only,
    set_live_max_orders_per_day,
    set_live_session_state_file,
    set_order_journal_file,
)
from trade_engine.config.visualization_config import (
    get_default_chart_type,
    get_default_interval,
    get_default_period,
    set_default_chart_type,
    set_default_interval,
    set_default_period,
)


class SettingsMenu:
    """Interactive settings editor backed by persistent CLI settings JSON."""

    def __init__(self, interface):
        self.interface = interface

    def show(self) -> bool:
        changed = False
        while True:
            options = [
                "Quick Setup Wizard",
                "Active Broker",
                "Broker SDKs",
                "Broker Credentials",
                "LLM Provider and Keys",
                "Pinecone Settings",
                "Visualization Defaults",
                "Live Trading Defaults",
                "Advanced Key/Value",
                "View Effective Settings",
                "Back to Main Menu",
            ]
            choice = self.interface.show_menu(options, "Settings")
            if choice == "Quick Setup Wizard":
                changed = self._quick_setup_wizard() or changed
            elif choice == "Active Broker":
                changed = self._set_active_broker() or changed
            elif choice == "Broker SDKs":
                changed = self._manage_broker_sdks() or changed
            elif choice == "Broker Credentials":
                changed = self._set_broker_credentials() or changed
            elif choice == "LLM Provider and Keys":
                changed = self._set_llm_settings() or changed
            elif choice == "Pinecone Settings":
                changed = self._set_pinecone_settings() or changed
            elif choice == "Visualization Defaults":
                changed = self._set_visualization_defaults() or changed
            elif choice == "Live Trading Defaults":
                changed = self._set_live_defaults() or changed
            elif choice == "Advanced Key/Value":
                changed = self._set_advanced_key_value() or changed
            elif choice == "View Effective Settings":
                self._show_effective_settings()
            elif choice == "Back to Main Menu":
                return changed

    def quick_setup(self) -> bool:
        return self._quick_setup_wizard()

    def _quick_setup_wizard(self) -> bool:
        changed = False
        self.interface.print_info("Quick setup will configure broker and credentials in one flow.")

        current = get_active_broker()
        broker = self.interface.show_menu(
            [*SUPPORTED_BROKERS, "Keep current", "Cancel"],
            "Quick Setup: Select Broker",
        )
        if broker == "Cancel":
            return False
        if broker == "Keep current":
            broker = current

        if broker != current:
            set_active_broker(broker)
            self.interface.print_success(f"Active broker set to: {broker}")
            changed = True

        status = get_broker_sdk_status(broker)
        if not status["installed"]:
            missing = ", ".join(status["missing_imports"])
            self.interface.print_info(f"Missing modules for {broker}: {missing}")
            install_now = (
                self.interface.input_prompt(f"Install {broker.title()} SDK now? (Y/n): ").strip().lower()
            )
            if install_now in {"", "y", "yes"}:
                result = self.interface.show_loading(
                    f"[bold cyan]Installing {broker.title()} SDK...[/bold cyan]",
                    install_broker_sdk,
                    broker,
                )
                if result:
                    ok, message = result
                    if ok:
                        self.interface.print_success(message)
                        changed = True
                    else:
                        self.interface.print_error(message)

        if broker == "none":
            self.interface.print_info("Broker-free mode selected. Market data remains available.")
            self.interface.print_success("Quick setup complete.")
            return changed

        if broker == "groww":
            changed = self._set_groww_credentials() or changed
        else:
            changed = self._set_stub_broker_credentials(broker) or changed

        self.interface.print_success("Quick setup complete.")
        return changed

    def _set_active_broker(self) -> bool:
        current = get_active_broker()
        options = [name for name in SUPPORTED_BROKERS] + ["Back"]
        self.interface.print_info(f"Current active broker: {current}")
        choice = self.interface.show_menu(options, "Select Active Broker")
        if choice == "Back" or choice == current:
            return False

        status = get_broker_sdk_status(choice)
        if not status["installed"]:
            missing = ", ".join(status["missing_imports"])
            self.interface.print_info(
                f"{choice.title()} SDK missing modules: {missing}"
            )
            install_now = (
                self.interface.input_prompt(
                    f"Install {choice.title()} SDK now from CLI? (Y/n): "
                )
                .strip()
                .lower()
            )
            if install_now in {"", "y", "yes"}:
                ok, message = self.interface.show_loading(
                    f"[bold cyan]Installing {choice.title()} SDK...[/bold cyan]",
                    install_broker_sdk,
                    choice,
                ) or (False, "SDK install failed.")
                if ok:
                    self.interface.print_success(message)
                else:
                    self.interface.print_error(message)

        set_active_broker(choice)
        self.interface.print_success(f"Active broker set to: {choice}")
        return True

    def _manage_broker_sdks(self) -> bool:
        changed = False
        while True:
            choice = self.interface.show_menu(
                [
                    "View SDK Status",
                    "Install SDK for Active Broker",
                    "Install SDK for Specific Broker",
                    "Back",
                ],
                "Broker SDK Manager",
            )

            if choice == "Back":
                return changed

            if choice == "View SDK Status":
                rows = list_broker_sdk_status()
                self.interface.display_response(rows, "Broker SDK Status")
                continue

            if choice == "Install SDK for Active Broker":
                broker = get_active_broker()
                result = self.interface.show_loading(
                    f"[bold cyan]Installing {broker.title()} SDK...[/bold cyan]",
                    install_broker_sdk,
                    broker,
                )
                if result:
                    ok, message = result
                    if ok:
                        self.interface.print_success(message)
                        changed = True
                    else:
                        self.interface.print_error(message)
                continue

            broker = self.interface.show_menu(
                ["none", "groww", "upstox", "zerodha", "Back"],
                "Select Broker SDK to Install",
            )
            if broker == "Back":
                continue
            result = self.interface.show_loading(
                f"[bold cyan]Installing {broker.title()} SDK...[/bold cyan]",
                install_broker_sdk,
                broker,
            )
            if result:
                ok, message = result
                if ok:
                    self.interface.print_success(message)
                    changed = True
                else:
                    self.interface.print_error(message)

    def _set_broker_credentials(self) -> bool:
        broker = self.interface.show_menu(["none", "groww", "upstox", "zerodha", "Back"], "Broker Credential Target")
        if broker == "Back":
            return False
        if broker == "none":
            self.interface.print_info("No credentials required for broker-free mode.")
            return False
        if broker == "groww":
            return self._set_groww_credentials()
        return self._set_stub_broker_credentials(broker)

    def _set_groww_credentials(self) -> bool:
        current_key = get_groww_api_key()
        current_secret = get_groww_api_secret()
        current_token = get_groww_access_token()
        self.interface.print_info(f"GROWW_API_KEY: {mask_secret(current_key)}")
        self.interface.print_info(f"GROWW_API_SECRET: {mask_secret(current_secret)}")
        self.interface.print_info(f"GROWW_ACCESS_TOKEN: {mask_secret(current_token)}")

        key = self.interface.input_prompt("Groww API key (blank to keep current): ").strip()
        secret = self.interface.input_prompt("Groww API secret/TOTP seed (blank to keep current): ").strip()
        token = self.interface.input_prompt("Groww access token (blank to keep current): ").strip()

        updated = False
        if key or secret:
            set_groww_credentials(key or current_key, secret or current_secret)
            updated = True
        if token:
            set_groww_access_token(token)
            updated = True
        if updated:
            self.interface.print_success("Groww credentials updated in CLI settings.")
        return updated

    def _set_stub_broker_credentials(self, broker_name: str) -> bool:
        if broker_name == "upstox":
            fields = [
                ("api_key", "API key"),
                ("api_secret", "API secret"),
                ("access_token", "Access token"),
                ("redirect_uri", "Redirect URI"),
                ("auth_code", "Authorization code"),
            ]
        elif broker_name == "zerodha":
            fields = [
                ("api_key", "API key"),
                ("api_secret", "API secret"),
                ("access_token", "Access token"),
                ("request_token", "Request token"),
            ]
        else:
            fields = [
                ("api_key", "API key"),
                ("api_secret", "API secret"),
            ]

        updated = False
        for suffix, label in fields:
            key_path = f"broker.{broker_name}.{suffix}"
            current_value = str(get_setting(key_path, "", str) or "").strip()
            masked_value = mask_secret(current_value) if "token" in suffix or "secret" in suffix else current_value
            prompt = f"{broker_name.upper()} {label} [{masked_value}] (blank to keep current): "
            value = self.interface.input_prompt(prompt).strip()
            if value:
                set_setting(key_path, value)
                updated = True

        if updated:
            self.interface.print_success(f"{broker_name.title()} credentials updated in CLI settings.")
        return updated

    def _set_llm_settings(self) -> bool:
        updated = False
        current_provider = get_llm_provider()
        provider = self.interface.show_menu(["openai", "claude", "gemini", "Back"], "Default LLM Provider")
        if provider != "Back" and provider != current_provider:
            set_llm_provider(provider)
            self.interface.print_success(f"LLM provider set to: {provider}")
            updated = True

        openai_key = self.interface.input_prompt(
            f"OpenAI API key [{mask_secret(get_openai_api_key())}] (blank to keep): "
        ).strip()
        claude_key = self.interface.input_prompt(
            f"Claude API key [{mask_secret(get_claude_api_key())}] (blank to keep): "
        ).strip()
        gemini_key = self.interface.input_prompt(
            f"Gemini API key [{mask_secret(get_gemini_api_key())}] (blank to keep): "
        ).strip()
        if openai_key:
            set_openai_api_key(openai_key)
            updated = True
        if claude_key:
            set_claude_api_key(claude_key)
            updated = True
        if gemini_key:
            set_gemini_api_key(gemini_key)
            updated = True
        if updated:
            self.interface.print_success("LLM settings saved.")
        return updated

    def _set_pinecone_settings(self) -> bool:
        current_key = get_pinecone_api_key()
        current_index = get_pinecone_index_name_eq()
        key = self.interface.input_prompt(f"Pinecone API key [{mask_secret(current_key)}] (blank to keep): ").strip()
        index = self.interface.input_prompt(f"Pinecone index name [{current_index}] (blank to keep): ").strip()
        updated = False
        if key:
            set_pinecone_api_key(key)
            updated = True
        if index:
            set_pinecone_index_name_eq(index)
            updated = True
        if updated:
            self.interface.print_success("Pinecone settings saved.")
        return updated

    def _set_visualization_defaults(self) -> bool:
        period = self.interface.input_prompt(f"Default chart period [{get_default_period()}]: ").strip() or get_default_period()
        interval = (
            self.interface.input_prompt(f"Default chart interval [{get_default_interval()}]: ").strip()
            or get_default_interval()
        )
        chart_type = (
            self.interface.input_prompt(f"Default chart type [{get_default_chart_type()}]: ").strip().lower()
            or get_default_chart_type()
        )
        try:
            set_default_period(period)
            set_default_interval(interval)
            set_default_chart_type(chart_type)
            self.interface.print_success("Visualization defaults saved.")
            return True
        except ValueError as error:
            self.interface.print_error(f"Invalid visualization setting: {error}")
            return False

    @staticmethod
    def _parse_value(raw: str):
        value = raw.strip()
        lowered = value.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value

    def _set_advanced_key_value(self) -> bool:
        self.interface.print_info("Set any dotted key path (example: trading.live_default_refresh_seconds).")
        settings = load_settings()
        self.interface.print_info("Type '/' at prompt to view input commands.")
        key = self.interface.input_prompt(
            "Setting key: ",
            slash_commands={
                "/list": "Show current top-level sections",
                "/cancel": "Cancel",
            },
        ).strip()
        if key in {"/cancel", ""}:
            return False
        if key == "/list":
            self.interface.display_response(
                [{"section": k} for k in sorted(settings.keys())],
                "Available Top-Level Settings",
            )
            return False
        raw_value = self.interface.input_prompt("Value (string/int/float/bool): ").strip()
        if raw_value in {"/cancel", ""}:
            return False

        # Handle nested dict set.
        parts = key.split(".")
        cursor = settings
        for part in parts[:-1]:
            if part not in cursor or not isinstance(cursor[part], dict):
                cursor[part] = {}
            cursor = cursor[part]
        cursor[parts[-1]] = self._parse_value(raw_value)
        if save_settings(settings):
            self.interface.print_success(f"Saved setting: {key}")
            return True
        self.interface.print_error("Failed to save advanced setting.")
        return False

    def _set_live_defaults(self) -> bool:
        current_mode = get_live_default_mode()
        current_refresh = get_live_default_refresh_seconds()
        current_sl = get_live_default_stop_loss_pct()
        current_tp = get_live_default_take_profit_pct()
        current_risk = get_live_default_risk_per_trade_pct()
        current_max_pos = get_live_default_max_position_pct()
        current_state_file = get_live_session_state_file()
        current_journal_file = get_order_journal_file()
        current_resume = get_live_auto_resume_session()
        current_kill = get_kill_switch_enabled()
        current_hours = get_live_market_hours_only()
        current_max_orders = get_live_max_orders_per_day()
        current_dashboard_state_file = get_live_dashboard_state_file()
        current_dashboard_control_file = get_live_dashboard_control_file()
        current_dashboard_port = get_live_dashboard_port()

        mode = self.interface.input_prompt(f"Default mode (paper/live) [{current_mode}]: ").strip().lower() or current_mode
        refresh_raw = self.interface.input_prompt(f"Refresh seconds [{current_refresh}]: ").strip() or str(current_refresh)
        sl_raw = self.interface.input_prompt(f"Stop-loss % [{current_sl}]: ").strip() or str(current_sl)
        tp_raw = self.interface.input_prompt(f"Take-profit % [{current_tp}]: ").strip() or str(current_tp)
        risk_raw = self.interface.input_prompt(f"Risk per trade % [{current_risk}]: ").strip() or str(current_risk)
        max_pos_raw = self.interface.input_prompt(f"Max position % [{current_max_pos}]: ").strip() or str(current_max_pos)
        kill_raw = (
            self.interface.input_prompt(f"Kill switch enabled (true/false) [{str(current_kill).lower()}]: ").strip()
            or str(current_kill).lower()
        )
        hours_raw = (
            self.interface.input_prompt(f"Market-hours guard (true/false) [{str(current_hours).lower()}]: ").strip()
            or str(current_hours).lower()
        )
        max_orders_raw = self.interface.input_prompt(
            f"Max orders per day [{current_max_orders}]: "
        ).strip() or str(current_max_orders)
        state_file = self.interface.input_prompt(f"Session state file [{current_state_file}]: ").strip() or current_state_file
        journal_file = (
            self.interface.input_prompt(f"Order journal sqlite file [{current_journal_file}]: ").strip()
            or current_journal_file
        )
        dashboard_state_file = (
            self.interface.input_prompt(
                f"Live dashboard state JSON [{current_dashboard_state_file}]: "
            ).strip()
            or current_dashboard_state_file
        )
        dashboard_control_file = (
            self.interface.input_prompt(
                f"Live dashboard control JSON [{current_dashboard_control_file}]: "
            ).strip()
            or current_dashboard_control_file
        )
        dashboard_port_raw = (
            self.interface.input_prompt(f"Live dashboard port [{current_dashboard_port}]: ").strip()
            or str(current_dashboard_port)
        )
        resume_raw = (
            self.interface.input_prompt(f"Auto resume session (true/false) [{str(current_resume).lower()}]: ").strip()
            or str(current_resume).lower()
        )

        try:
            set_live_default_mode(mode)
            set_live_default_refresh_seconds(int(refresh_raw))
            set_live_default_stop_loss_pct(float(sl_raw))
            set_live_default_take_profit_pct(float(tp_raw))
            set_live_default_risk_per_trade_pct(float(risk_raw))
            set_live_default_max_position_pct(float(max_pos_raw))
            set_kill_switch_enabled(kill_raw.lower() in {"true", "1", "yes", "y", "on"})
            set_live_market_hours_only(hours_raw.lower() in {"true", "1", "yes", "y", "on"})
            set_live_max_orders_per_day(int(max_orders_raw))
            set_live_session_state_file(state_file)
            set_order_journal_file(journal_file)
            set_live_dashboard_state_file(dashboard_state_file)
            set_live_dashboard_control_file(dashboard_control_file)
            set_live_dashboard_port(int(dashboard_port_raw))
            set_live_auto_resume_session(resume_raw.lower() in {"true", "1", "yes", "y", "on"})
        except ValueError as error:
            self.interface.print_error(f"Invalid value: {error}")
            return False

        self.interface.print_success("Live trading defaults saved.")
        return True

    def _show_effective_settings(self):
        rows = [
            {"setting": "settings_file", "value": get_settings_file()},
            {"setting": "broker.active", "value": get_active_broker()},
            {"setting": "broker.groww.api_key", "value": mask_secret(get_groww_api_key())},
            {"setting": "broker.groww.api_secret", "value": mask_secret(get_groww_api_secret())},
            {"setting": "broker.groww.access_token", "value": mask_secret(get_groww_access_token())},
            {
                "setting": "broker.upstox.api_key",
                "value": mask_secret(str(get_setting("broker.upstox.api_key", "", str) or "")),
            },
            {
                "setting": "broker.upstox.api_secret",
                "value": mask_secret(str(get_setting("broker.upstox.api_secret", "", str) or "")),
            },
            {
                "setting": "broker.upstox.access_token",
                "value": mask_secret(str(get_setting("broker.upstox.access_token", "", str) or "")),
            },
            {
                "setting": "broker.upstox.redirect_uri",
                "value": str(get_setting("broker.upstox.redirect_uri", "", str) or ""),
            },
            {
                "setting": "broker.upstox.auth_code",
                "value": mask_secret(str(get_setting("broker.upstox.auth_code", "", str) or "")),
            },
            {
                "setting": "broker.zerodha.api_key",
                "value": mask_secret(str(get_setting("broker.zerodha.api_key", "", str) or "")),
            },
            {
                "setting": "broker.zerodha.api_secret",
                "value": mask_secret(str(get_setting("broker.zerodha.api_secret", "", str) or "")),
            },
            {
                "setting": "broker.zerodha.access_token",
                "value": mask_secret(str(get_setting("broker.zerodha.access_token", "", str) or "")),
            },
            {
                "setting": "broker.zerodha.request_token",
                "value": mask_secret(str(get_setting("broker.zerodha.request_token", "", str) or "")),
            },
            {"setting": "llm.provider", "value": get_llm_provider()},
            {"setting": "llm.openai_api_key", "value": mask_secret(get_openai_api_key())},
            {"setting": "llm.claude_api_key", "value": mask_secret(get_claude_api_key())},
            {"setting": "llm.gemini_api_key", "value": mask_secret(get_gemini_api_key())},
            {"setting": "pinecone.api_key", "value": mask_secret(get_pinecone_api_key())},
            {"setting": "pinecone.index_name_eq", "value": get_pinecone_index_name_eq()},
            {"setting": "visualization.default_period", "value": get_default_period()},
            {"setting": "visualization.default_interval", "value": get_default_interval()},
            {"setting": "visualization.default_chart_type", "value": get_default_chart_type()},
            {"setting": "trading.live_default_mode", "value": get_live_default_mode()},
            {"setting": "trading.live_default_refresh_seconds", "value": str(get_live_default_refresh_seconds())},
            {"setting": "trading.live_default_stop_loss_pct", "value": str(get_live_default_stop_loss_pct())},
            {"setting": "trading.live_default_take_profit_pct", "value": str(get_live_default_take_profit_pct())},
            {"setting": "trading.live_default_risk_per_trade_pct", "value": str(get_live_default_risk_per_trade_pct())},
            {"setting": "trading.live_default_max_position_pct", "value": str(get_live_default_max_position_pct())},
            {"setting": "trading.kill_switch_enabled", "value": str(get_kill_switch_enabled())},
            {"setting": "trading.live_market_hours_only", "value": str(get_live_market_hours_only())},
            {"setting": "trading.live_max_orders_per_day", "value": str(get_live_max_orders_per_day())},
            {"setting": "trading.live_session_state_file", "value": get_live_session_state_file()},
            {"setting": "trading.order_journal_file", "value": get_order_journal_file()},
            {"setting": "trading.live_dashboard_state_file", "value": get_live_dashboard_state_file()},
            {"setting": "trading.live_dashboard_control_file", "value": get_live_dashboard_control_file()},
            {"setting": "trading.live_dashboard_port", "value": str(get_live_dashboard_port())},
            {"setting": "trading.live_auto_resume_session", "value": str(get_live_auto_resume_session())},
        ]
        self.interface.display_response(rows, "Effective CLI Settings")

