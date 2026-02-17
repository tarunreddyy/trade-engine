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
from trade_engine.config.settings_store import get_settings_file, mask_secret, set_setting
from trade_engine.config.trading_config import (
    get_kill_switch_enabled,
    get_live_auto_resume_session,
    get_live_default_max_position_pct,
    get_live_default_mode,
    get_live_market_hours_only,
    get_live_max_orders_per_day,
    get_order_journal_file,
    get_live_default_refresh_seconds,
    get_live_default_risk_per_trade_pct,
    get_live_default_stop_loss_pct,
    get_live_default_take_profit_pct,
    get_live_session_state_file,
    set_kill_switch_enabled,
    set_live_auto_resume_session,
    set_live_default_max_position_pct,
    set_live_default_mode,
    set_live_market_hours_only,
    set_live_max_orders_per_day,
    set_order_journal_file,
    set_live_default_refresh_seconds,
    set_live_default_risk_per_trade_pct,
    set_live_default_stop_loss_pct,
    set_live_default_take_profit_pct,
    set_live_session_state_file,
)


class SettingsMenu:
    """Interactive settings editor backed by persistent CLI settings JSON."""

    def __init__(self, interface):
        self.interface = interface

    def show(self) -> bool:
        changed = False
        while True:
            options = [
                "Active Broker",
                "Broker Credentials",
                "LLM Provider and Keys",
                "Pinecone Settings",
                "Live Trading Defaults",
                "View Effective Settings",
                "Back to Main Menu",
            ]
            choice = self.interface.show_menu(options, "Settings")
            if choice == "Active Broker":
                changed = self._set_active_broker() or changed
            elif choice == "Broker Credentials":
                changed = self._set_broker_credentials() or changed
            elif choice == "LLM Provider and Keys":
                changed = self._set_llm_settings() or changed
            elif choice == "Pinecone Settings":
                changed = self._set_pinecone_settings() or changed
            elif choice == "Live Trading Defaults":
                changed = self._set_live_defaults() or changed
            elif choice == "View Effective Settings":
                self._show_effective_settings()
            elif choice == "Back to Main Menu":
                return changed

    def _set_active_broker(self) -> bool:
        current = get_active_broker()
        options = [name for name in SUPPORTED_BROKERS] + ["Back"]
        self.interface.print_info(f"Current active broker: {current}")
        choice = self.interface.show_menu(options, "Select Active Broker")
        if choice == "Back" or choice == current:
            return False
        set_active_broker(choice)
        self.interface.print_success(f"Active broker set to: {choice}")
        return True

    def _set_broker_credentials(self) -> bool:
        broker = self.interface.show_menu(["groww", "upstox", "zerodha", "Back"], "Broker Credential Target")
        if broker == "Back":
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
        key_path = f"broker.{broker_name}.api_key"
        secret_path = f"broker.{broker_name}.api_secret"
        key = self.interface.input_prompt(f"{broker_name.upper()} API key (blank to keep current): ").strip()
        secret = self.interface.input_prompt(f"{broker_name.upper()} API secret (blank to keep current): ").strip()
        updated = False
        if key:
            set_setting(key_path, key)
            updated = True
        if secret:
            set_setting(secret_path, secret)
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
            {"setting": "llm.provider", "value": get_llm_provider()},
            {"setting": "llm.openai_api_key", "value": mask_secret(get_openai_api_key())},
            {"setting": "llm.claude_api_key", "value": mask_secret(get_claude_api_key())},
            {"setting": "llm.gemini_api_key", "value": mask_secret(get_gemini_api_key())},
            {"setting": "pinecone.api_key", "value": mask_secret(get_pinecone_api_key())},
            {"setting": "pinecone.index_name_eq", "value": get_pinecone_index_name_eq()},
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
            {"setting": "trading.live_auto_resume_session", "value": str(get_live_auto_resume_session())},
        ]
        self.interface.display_response(rows, "Effective CLI Settings")
