"""Test helpers. The API suite never hits the network: the single engine seam
(`api.jobs.run_build` and the resolver in `api.routes`) is monkeypatched per test."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # imported lazily so app import errors surface inside the test, not at collection
    from api.app import create_app
    return TestClient(create_app())
