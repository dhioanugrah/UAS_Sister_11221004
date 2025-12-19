import os
import time
import httpx
import pytest

BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")

@pytest.fixture(scope="session")
def base_url():
    return BASE_URL

@pytest.fixture(scope="session")
def client():
    return httpx.Client(timeout=10.0)

def wait_until_ready(base_url: str, timeout_s: int = 30):
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            r = httpx.get(f"{base_url}/stats", timeout=2.0)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("Service not ready")

@pytest.fixture(scope="session", autouse=True)
def _ready(base_url):
    wait_until_ready(base_url)
