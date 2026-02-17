import os

from dotenv import load_dotenv

load_dotenv()

LIVE_DEFAULT_MODE = os.getenv("LIVE_DEFAULT_MODE", "paper").strip().lower()
LIVE_DEFAULT_REFRESH_SECONDS = int(os.getenv("LIVE_DEFAULT_REFRESH_SECONDS", "15"))
LIVE_DEFAULT_STOP_LOSS_PCT = float(os.getenv("LIVE_DEFAULT_STOP_LOSS_PCT", "2.0"))
LIVE_DEFAULT_TAKE_PROFIT_PCT = float(os.getenv("LIVE_DEFAULT_TAKE_PROFIT_PCT", "4.0"))
LIVE_DEFAULT_RISK_PER_TRADE_PCT = float(os.getenv("LIVE_DEFAULT_RISK_PER_TRADE_PCT", "1.0"))
LIVE_DEFAULT_MAX_POSITION_PCT = float(os.getenv("LIVE_DEFAULT_MAX_POSITION_PCT", "10.0"))
LIVE_SESSION_STATE_FILE = os.getenv("LIVE_SESSION_STATE_FILE", "data/runtime/live_session_state.json")
LIVE_AUTO_RESUME_SESSION = os.getenv("LIVE_AUTO_RESUME_SESSION", "true").strip().lower() in {"1", "true", "yes", "y"}


