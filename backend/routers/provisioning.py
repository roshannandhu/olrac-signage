import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import schemas, models
from ..tenancy import TenantScope, require_tenant_roles
from .enrollment_tokens import create_token

router = APIRouter()

class ProvisioningRequest(BaseModel):
    wifi_ssid: str
    wifi_password: str
    wifi_security_type: str = "WPA"
    max_uses: int = 1

@router.post("/qr")
def generate_provisioning_qr(
    req: ProvisioningRequest,
    scope: TenantScope = Depends(require_tenant_roles("owner"))
):
    cert_hash = os.getenv("PROVISIONING_CERT_SHA256_BASE64")
    apk_url = os.getenv("PROVISIONING_APK_URL")
    base_url = os.getenv("PUBLIC_BASE_URL")

    if not cert_hash or not apk_url or not base_url:
        missing = [
            name for name, value in (
                ("PROVISIONING_CERT_SHA256_BASE64", cert_hash),
                ("PROVISIONING_APK_URL", apk_url),
                ("PUBLIC_BASE_URL", base_url),
            ) if not value
        ]
        # 503, not 500: nothing has crashed, the feature simply has no configuration yet.
        # A 500 here reads as a bug and sends people looking in the wrong place.
        raise HTTPException(
            status_code=503,
            detail=f"Provisioning is not configured yet. Set {', '.join(missing)} in .env and restart the API.",
        )

    # Generate an enrollment token
    token_create_req = schemas.EnrollmentTokenCreate(
        description=f"Provisioning QR token for site {req.wifi_ssid}",
        max_uses=req.max_uses,
        expires_at=None
    )
    
    # We can reuse the create_token logic
    token_response = create_token(token_create_req, scope)
    enrollment_token = token_response["token"]

    payload = {
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME": "com.olrac.signage/.receivers.SignageDeviceAdminReceiver",
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_PACKAGE_DOWNLOAD_LOCATION": apk_url,
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM": cert_hash,
        "android.app.extra.PROVISIONING_WIFI_SSID": req.wifi_ssid,
        "android.app.extra.PROVISIONING_WIFI_PASSWORD": req.wifi_password,
        "android.app.extra.PROVISIONING_WIFI_SECURITY_TYPE": req.wifi_security_type,
        "android.app.extra.PROVISIONING_SKIP_ENCRYPTION": True,
        "android.app.extra.PROVISIONING_LEAVE_ALL_SYSTEM_APPS_ENABLED": True,
        "android.app.extra.PROVISIONING_ADMIN_EXTRAS_BUNDLE": {
            "enrollment_token": enrollment_token,
            "api_base_url": base_url
        }
    }

    return payload
