import os
import tempfile

import pytest

# the planner tests use the small 17-city network and the weather rules, so they
# don't need the downloaded data or a trained model and always give the same answers
os.environ["RAILSKY_SAMPLE"] = "1"
os.environ["RAILSKY_NO_MODEL"] = "1"

# test_api.py starts the whole app, which creates tables and an admin account.
# Give it its own database file, and no SMTP so the OTP comes back in the response.
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(
    tempfile.mkdtemp(), "api_test.db"
)
for key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS"):
    os.environ.pop(key, None)
os.environ.pop("OWM_API_KEY", None)  # demo weather, same answers every run

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAS_DATA = os.path.exists(os.path.join(ROOT, "data", "processed", "trains.csv"))
HAS_MODEL = os.path.exists(os.path.join(ROOT, "models", "delay_p50.txt"))


@pytest.fixture
def real_network(monkeypatch):
    """Swap in the real network for one test (skipped if build_data.py hasn't run)."""
    if not HAS_DATA:
        pytest.skip("run scripts/build_data.py first")
    from backend import network

    monkeypatch.setenv("RAILSKY_SAMPLE", "0")
    net = network.Network.load()
    monkeypatch.setattr(network, "_network", net)
    return net
