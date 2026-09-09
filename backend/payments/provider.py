import base64
import json
import os
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CheckoutSession:
    provider_subscription_id: str
    checkout_url: str


@dataclass(frozen=True)
class Order:
    """A one-time charge. The storefront sells a fixed access window this way rather than a
    recurring subscription, so a package (or a bespoke request) is bought outright for its
    period. `key_id`/`checkout_url` are whatever the client needs to open the payment sheet;
    the mock provider needs neither and is completed through /billing/mock/confirm."""

    order_id: str
    amount_paise: int
    provider: str
    key_id: str | None = None
    checkout_url: str | None = None


class PaymentProvider(Protocol):
    def create_subscription(
        self,
        *,
        provider_plan_id: str,
        billing_period: str,
        organization_id: int,
        local_plan_id: int,
    ) -> CheckoutSession: ...

    def create_order(
        self,
        *,
        amount_paise: int,
        organization_id: int,
        notes: dict,
    ) -> Order: ...


class RazorpayProvider:
    API_URL = "https://api.razorpay.com/v1/subscriptions"
    ORDERS_URL = "https://api.razorpay.com/v1/orders"

    def __init__(self) -> None:
        self.key_id = os.getenv("RAZORPAY_KEY_ID", "")
        self.key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
        if not self.key_id or not self.key_secret:
            raise RuntimeError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be configured")

    def _post(self, url: str, body: dict) -> dict:
        payload = json.dumps(body).encode("utf-8")
        credentials = base64.b64encode(f"{self.key_id}:{self.key_secret}".encode()).decode()
        request = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read())
        except (urllib.error.URLError, ValueError) as exc:
            raise RuntimeError(f"Razorpay request failed: {exc}") from exc

    def create_order(self, *, amount_paise: int, organization_id: int, notes: dict) -> Order:
        result = self._post(
            self.ORDERS_URL,
            {
                "amount": amount_paise,
                "currency": "INR",
                # Razorpay echoes notes back on the order.paid webhook, which is how the
                # webhook attributes the payment without trusting anything the client sends.
                "notes": {**{k: str(v) for k, v in notes.items()}, "organization_id": str(organization_id)},
            },
        )
        order_id = result.get("id")
        if not order_id:
            raise RuntimeError("Razorpay returned an incomplete order response")
        # No hosted URL for a one-time order: the client opens Razorpay Checkout with the
        # key id and order id. key_id is publishable, so returning it is safe.
        return Order(order_id=order_id, amount_paise=amount_paise, provider="razorpay", key_id=self.key_id)

    def create_subscription(
        self,
        *,
        provider_plan_id: str,
        billing_period: str,
        organization_id: int,
        local_plan_id: int,
    ) -> CheckoutSession:
        payload = json.dumps(
            {
                "plan_id": provider_plan_id,
                "total_count": 120 if billing_period == "monthly" else 10,
                "quantity": 1,
                "customer_notify": 1,
                "notes": {
                    "organization_id": str(organization_id),
                    "local_plan_id": str(local_plan_id),
                    "billing_period": billing_period,
                },
            }
        ).encode("utf-8")
        credentials = base64.b64encode(f"{self.key_id}:{self.key_secret}".encode()).decode()
        request = urllib.request.Request(
            self.API_URL,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result = json.loads(response.read())
        except (urllib.error.URLError, ValueError) as exc:
            raise RuntimeError(f"Razorpay subscription creation failed: {exc}") from exc
        subscription_id = result.get("id")
        checkout_url = result.get("short_url")
        if not subscription_id or not checkout_url:
            raise RuntimeError("Razorpay returned an incomplete subscription response")
        return CheckoutSession(subscription_id, checkout_url)


class MockPaymentProvider:
    def create_subscription(
        self,
        *,
        provider_plan_id: str,
        billing_period: str,
        organization_id: int,
        local_plan_id: int,
    ) -> CheckoutSession:
        subscription_id = f"sub_mock_{uuid.uuid4().hex}"
        return CheckoutSession(subscription_id, f"https://checkout.test/{subscription_id}")

    def create_order(self, *, amount_paise: int, organization_id: int, notes: dict) -> Order:
        # No real charge: the client finishes the buy by calling /billing/mock/confirm with
        # this id, which runs the same activation the real webhook would.
        return Order(order_id=f"order_mock_{uuid.uuid4().hex}", amount_paise=amount_paise, provider="mock")


def get_payment_provider() -> PaymentProvider:
    provider = os.getenv("PAYMENT_PROVIDER", "razorpay").lower()
    if provider == "mock":
        return MockPaymentProvider()
    if provider != "razorpay":
        raise RuntimeError(f"Unsupported PAYMENT_PROVIDER: {provider}")
    return RazorpayProvider()
