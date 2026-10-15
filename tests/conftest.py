import os
from pathlib import Path

_CONTENT_ROOT = Path(__file__).parent / "fixtures" / "content"

os.environ["ORACLE_PROVIDER"] = "mock"
os.environ["ORACLE_AUTH_TOKEN"] = "test-oracle-token"
os.environ["ORACLE_CONTENT_ROOT"] = str(_CONTENT_ROOT)
os.environ["ORACLE_DAILY_BUDGET"] = "1000"
