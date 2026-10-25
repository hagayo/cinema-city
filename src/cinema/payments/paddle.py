"""Sandbox-only Paddle API adapter. Never provisions cinema bookings."""

from typing import Any

import httpx

from cinema.exceptions import AuthorizationError, BusinessError

SANDBOX_API = "https://sandbox-api.paddle.com"
TEST_PURPOSE = "cinema-city-sandbox-test"


class PaddleSandboxError(BusinessError):
    """Safe payment error that contains no credentials or customer data."""


class PaddleSandboxClient:
    """Create one-time test transactions and verify their status server-side."""

    def __init__(self, api_key: str, price_id: str) -> None:
        if not api_key.startswith("pdl_sdbx_apikey_"):
            raise ValueError("Sandbox API key required")
        self._api_key = api_key
        self._price_id = price_id

    def create_checkout(self, user_id: int) -> dict[str, str]:
        price = self._request("GET", f"/prices/{self._price_id}")
        if (
            price.get("status") != "active"
            or "billing_cycle" not in price
            or price["billing_cycle"] is not None
            or "trial_period" not in price
            or price["trial_period"] is not None
        ):
            raise PaddleSandboxError("יש לבחור מחיר Sandbox פעיל וחד־פעמי, ללא תקופת ניסיון")
        transaction = self._request(
            "POST",
            "/transactions",
            {
                "items": [{"price_id": self._price_id, "quantity": 1}],
                "collection_mode": "automatic",
                "custom_data": {"purpose": TEST_PURPOSE, "user_id": str(user_id)},
            },
        )
        return self._summary(transaction)

    def transaction_status(self, transaction_id: str, user_id: int) -> dict[str, str]:
        transaction = self._request("GET", f"/transactions/{transaction_id}")
        metadata = transaction.get("custom_data") or {}
        if metadata.get("purpose") != TEST_PURPOSE or metadata.get("user_id") != str(user_id):
            raise AuthorizationError("העסקה אינה שייכת לבדיקת התשלום שלך")
        return self._summary(transaction)

    @staticmethod
    def _summary(transaction: dict[str, Any]) -> dict[str, str]:
        return {"transaction_id": transaction["id"], "status": transaction["status"]}

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        try:
            with httpx.Client(
                base_url=SANDBOX_API,
                headers={"Authorization": f"Bearer {self._api_key}", "Paddle-Version": "1"},
                timeout=15,
                follow_redirects=False,
            ) as client:
                response = client.request(method, path, json=payload)
            if response.status_code == 400:
                error_code = response.json().get("error", {}).get("code")
                if error_code == "transaction_default_checkout_url_not_set":
                    raise PaddleSandboxError(
                        "חסרה הגדרת Default payment link בחשבון Paddle Sandbox. "
                        "הגדירו אותה ב־Checkout → Checkout configuration ונסו שוב"
                    )
            response.raise_for_status()
            data = response.json()["data"]
            if not isinstance(data, dict):
                raise ValueError("Invalid Paddle response")
            return data
        except (httpx.HTTPError, ValueError, KeyError) as error:
            raise PaddleSandboxError(
                "הפנייה ל־Paddle Sandbox נכשלה. בדקו חיבור, הרשאות API, מחיר ו־Default payment link בחשבון הבדיקה"
            ) from error
