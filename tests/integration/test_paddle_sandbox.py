"""Exercise sandbox boundaries, Paddle requests and isolated checkout routes."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

import httpx
import pytest
from fastapi.testclient import TestClient

from cinema.composition import AuthAdapters, create_container
from cinema.config import ApiMode, AppEnvironment, Settings, load_settings
from cinema.payments.paddle import (
    SANDBOX_API,
    TEST_PURPOSE,
    PaddleSandboxClient,
    PaddleSandboxError,
)
from cinema.web import create_app
from tests.integration.test_web_api import FailingAuth

PRICE_ID = "pri_" + "a" * 26
TRANSACTION_ID = "txn_" + "b" * 26
API_KEY = "pdl_sdbx_apikey_test_fixture"
PUBLIC_CLIENT_TOKEN = "test_public_fixture"


def sandbox_settings(tmp_path: Path, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "app_env": "test",
        "cinema_data_dir": tmp_path / "data",
        "billing_provider": "paddle",
        "paddle_env": "sandbox",
        "paddle_api_key": API_KEY,
        "paddle_client_token": "test_fixture",
        "paddle_test_price_id": PRICE_ID,
    }
    return Settings(**(values | overrides))


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"paddle_env": "production"}, "PADDLE_ENV"),
        ({"app_env": "production"}, "non-production"),
        ({"paddle_api_key": "pdl_live_apikey_secret"}, "PADDLE_API_KEY"),
        ({"paddle_client_token": "live_secret"}, "PADDLE_CLIENT_TOKEN"),
        ({"paddle_test_price_id": "pri_wrong"}, "PADDLE_TEST_PRICE_ID"),
        ({"paddle_api_key": ""}, "PADDLE_API_KEY"),
        ({"paddle_client_token": ""}, "PADDLE_CLIENT_TOKEN"),
    ],
)
def test_rejects_unsafe_or_incomplete_settings(
    tmp_path: Path, overrides: dict[str, str], message: str
) -> None:
    with pytest.raises(ValueError, match=message) as error:
        sandbox_settings(tmp_path, **overrides)
    assert "pdl_live_apikey_secret" not in str(error.value)
    assert API_KEY not in str(error.value)


def mock_paddle(monkeypatch: pytest.MonkeyPatch, handler: Any) -> None:
    real_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(**kwargs, transport=httpx.MockTransport(handler)),
    )


def test_sandbox_checkout_and_server_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    requests: list[httpx.Request] = []
    transaction: dict[str, Any] = {"id": TRANSACTION_ID, "status": "draft"}

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert str(request.url).startswith(SANDBOX_API + "/")
        assert request.headers["authorization"] == f"Bearer {API_KEY}"
        if request.url.path.startswith("/prices/"):
            return httpx.Response(
                200,
                json={"data": {"status": "active", "billing_cycle": None, "trial_period": None}},
            )
        if request.method == "POST":
            payload = json.loads(request.content)
            assert payload["items"] == [{"price_id": PRICE_ID, "quantity": 1}]
            assert payload["collection_mode"] == "automatic"
            assert payload["custom_data"]["purpose"] == TEST_PURPOSE
            transaction["custom_data"] = payload["custom_data"]
        return httpx.Response(200, json={"data": transaction})

    mock_paddle(monkeypatch, handle)
    settings = sandbox_settings(tmp_path)
    client = TestClient(create_app(settings))
    config = client.get("/api/config")
    assert config.json()["paddle"]["clientToken"] == "test_fixture"
    assert API_KEY not in config.text
    assert "paddle_webhook_secret" not in config.text
    assert client.get("/sandbox-payment").status_code == 200
    created = client.post(
        "/api/customer/payments/sandbox-checkout",
        json={"price_id": "attacker-price", "quantity": 99},
    )
    assert created.status_code == 201
    assert created.json() == {"transaction_id": TRANSACTION_ID, "status": "draft"}
    assert len(requests) == 2
    transaction["status"] = "completed"
    status = client.get(f"/api/customer/payments/sandbox-checkout/{TRANSACTION_ID}")
    assert status.json()["status"] == "completed"
    assert client.get("/api/customer/bookings").json() == []
    assert client.get("/api/customer/payments/sandbox-checkout/invalid").status_code == 422
    transaction["custom_data"]["user_id"] = "another-user"
    assert (
        client.get(f"/api/customer/payments/sandbox-checkout/{TRANSACTION_ID}").status_code == 403
    )
    transaction["custom_data"] = None
    assert (
        client.get(f"/api/customer/payments/sandbox-checkout/{TRANSACTION_ID}").status_code == 403
    )


@pytest.mark.parametrize("provider", ["disabled", "fake"])
def test_disabled_payments_have_no_routes(
    tmp_path: Path, provider: Literal["disabled", "fake"]
) -> None:
    client = TestClient(create_app(Settings(cinema_data_dir=tmp_path, billing_provider=provider)))
    assert client.get("/api/config").json()["paddle"]["enabled"] is False
    assert client.get("/sandbox-payment").status_code == 404
    assert client.post("/api/customer/payments/sandbox-checkout").status_code == 404


def test_sandbox_routes_require_customer_auth_and_gateway(tmp_path: Path) -> None:
    settings = sandbox_settings(tmp_path)
    container = create_container(settings)
    client = TestClient(
        create_app(settings, replace(container, auth=AuthAdapters(FailingAuth(), FailingAuth())))
    )
    assert client.post("/api/customer/payments/sandbox-checkout").status_code == 401
    assert (
        client.get(f"/api/customer/payments/sandbox-checkout/{TRANSACTION_ID}").status_code == 401
    )
    manager = TestClient(create_app(sandbox_settings(tmp_path, api_mode=ApiMode.MANAGER)))
    assert manager.get("/sandbox-payment").status_code == 404
    assert manager.post("/api/customer/payments/sandbox-checkout").status_code == 404
    assert manager.get("/api/config").json()["paddle"]["enabled"] is False


@pytest.mark.parametrize(
    "price",
    [
        {"status": "archived", "billing_cycle": None, "trial_period": None},
        {"status": "active", "billing_cycle": {"interval": "month"}, "trial_period": None},
        {"status": "active", "billing_cycle": None, "trial_period": {"interval": "day"}},
        {"status": "active"},
    ],
)
def test_rejects_recurring_trial_archived_and_incomplete_prices(
    monkeypatch: pytest.MonkeyPatch, price: dict[str, Any]
) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"  # No transaction may be created.
        return httpx.Response(200, json={"data": price})

    mock_paddle(monkeypatch, handle)
    with pytest.raises(PaddleSandboxError, match="חד־פעמי"):
        PaddleSandboxClient(API_KEY, PRICE_ID).create_checkout(1)


@pytest.mark.parametrize(
    "failure", ["forbidden", "timeout", "redirect", "invalid-json", "invalid-data"]
)
def test_provider_errors_are_sanitized(monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if failure == "timeout":
            raise httpx.ReadTimeout(API_KEY, request=request)
        if failure == "redirect":
            return httpx.Response(302, headers={"location": "https://api.paddle.com/prices"})
        if failure == "invalid-json":
            return httpx.Response(200, text="bad json " + API_KEY)
        if failure == "invalid-data":
            return httpx.Response(200, json={"data": []})
        return httpx.Response(403, json={"error": {"detail": API_KEY}})

    mock_paddle(monkeypatch, handle)
    with pytest.raises(PaddleSandboxError) as error:
        PaddleSandboxClient(API_KEY, PRICE_ID).create_checkout(1)
    assert API_KEY not in str(error.value)


def test_adapter_refuses_live_key() -> None:
    with pytest.raises(ValueError, match="Sandbox"):
        PaddleSandboxClient("pdl_live_apikey_test", PRICE_ID)


def test_missing_default_payment_link_has_actionable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def handle(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"code": "transaction_default_checkout_url_not_set", "detail": API_KEY}},
        )

    mock_paddle(monkeypatch, handle)
    with pytest.raises(PaddleSandboxError, match="Checkout configuration") as error:
        PaddleSandboxClient(API_KEY, PRICE_ID).create_checkout(1)
    assert API_KEY not in str(error.value)


def test_secret_settings_are_redacted(tmp_path: Path) -> None:
    assert API_KEY not in repr(sandbox_settings(tmp_path))
    # Empty Paddle values in base .env do not break profiles with billing disabled.
    assert not Settings(billing_provider="disabled", paddle_env="").paddle_sandbox_enabled


def test_development_dotenv_loading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_ENV", "development")
    (tmp_path / ".env.development").write_text(
        f"BILLING_PROVIDER=paddle\nPADDLE_ENV=sandbox\nPADDLE_API_KEY={API_KEY}\n"
        f"PADDLE_CLIENT_TOKEN=test_fixture\nPADDLE_TEST_PRICE_ID={PRICE_ID}\n",
        encoding="utf-8",
    )
    settings = load_settings()
    assert settings.app_env is AppEnvironment.DEVELOPMENT
    assert settings.paddle_sandbox_enabled
    assert settings.paddle_test_price_id == PRICE_ID


def test_public_sandbox_payment_page_works_without_server_billing_in_production(
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_env=AppEnvironment.PRODUCTION,
        cinema_data_dir=tmp_path,
        billing_provider="disabled",
        paddle_payment_link_enabled=True,
        paddle_client_token=PUBLIC_CLIENT_TOKEN,
    )
    client = TestClient(create_app(settings))
    assert client.get("/paddle-payment").status_code == 200
    assert client.get("/paddle-payment", params={"_ptxn": TRANSACTION_ID}).status_code == 200
    assert client.get("/api/config").json()["paddlePaymentLink"] == {
        "enabled": True,
        "clientToken": "test_public_fixture",
    }
    assert client.get("/api/config").json()["paddle"]["enabled"] is False
    assert client.get("/sandbox-payment").status_code == 404
    assert client.post("/api/customer/payments/sandbox-checkout").status_code == 404
    assert client.get("/api/docs").status_code == 404
    assert settings.paddle_api_key.get_secret_value() == ""


@pytest.mark.parametrize(
    "environment, token",
    [("production", "test_fixture"), ("sandbox", "live_fixture"), ("sandbox", "")],
)
def test_public_payment_page_rejects_live_or_missing_credentials(
    environment: str, token: str
) -> None:
    with pytest.raises(ValueError, match="Sandbox payment link requires"):
        Settings(
            paddle_payment_link_enabled=True, paddle_env=environment, paddle_client_token=token
        )


def test_public_payment_page_requires_flag_and_customer_gateway(tmp_path: Path) -> None:
    disabled = TestClient(create_app(Settings(cinema_data_dir=tmp_path)))
    assert disabled.get("/paddle-payment").status_code == 404
    assert disabled.get("/api/config").json()["paddlePaymentLink"] == {
        "enabled": False,
        "clientToken": "",
    }
    manager = TestClient(
        create_app(
            Settings(
                cinema_data_dir=tmp_path,
                api_mode=ApiMode.MANAGER,
                paddle_payment_link_enabled=True,
                paddle_client_token=PUBLIC_CLIENT_TOKEN,
            )
        )
    )
    assert manager.get("/paddle-payment").status_code == 404
    assert manager.get("/api/config").json()["paddlePaymentLink"] == {
        "enabled": False,
        "clientToken": "",
    }
