import os

from src.core.settings import get_settings


os.environ.setdefault("CARDIOSENSE_DB_BACKEND", "inmemory")


def pytest_runtest_setup():
    get_settings.cache_clear()
