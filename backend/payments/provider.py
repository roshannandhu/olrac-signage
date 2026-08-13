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


class PaymentProvider(Protocol):
    def create_subscription(
        self,
        *,
        provider_plan_id: str,
        billing_period: str,
        organization_id: int,
        local_plan_id: int,
    ) -> CheckoutSession: ...


class RazorpayProvider:
    API_URL = "https://api.razorpay.com/v1/subscriptions"

    def __init__(self) -> None:
        self.key_id = os.getenv("RAZORPAY_KEY_ID", "")
        self.key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
        if not self.key_id or not self.key_secret:
            raise RuntimeError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be configured")

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


def get_payment_provider() -> PaymentProvider:
    provider = os.getenv("PAYMENT_PROVIDER", "razorpay").lower()
    if provider == "mock":
        return MockPaymentProvider()
    if provider != "razorpay":
        raise RuntimeError(f"Unsupported PAYMENT_PROVIDER: {provider}")
    return RazorpayProvider()
