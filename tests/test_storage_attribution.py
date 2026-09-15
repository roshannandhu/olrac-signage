"""Attributing bucket objects to the workspace that put them there.

Two key schemes are live at once: the legacy flat `org-<id>/...` and the current
`tenants/<Slug>-<id>/...`. Both resolve to the same workspace, and the admin page listed
them as separate rows -- each repeating that workspace's FULL database bytes and quota
while showing only its share of the bucket. A tenant comfortably inside its quota could
therefore be read off the page as several tenants, each apparently near their limit.

A rename does the same thing without any migration: the prefix is derived from the
workspace NAME, so objects uploaded before the rename keep the old slug for ever. Only the
trailing id is stable, which is exactly what the merge keys on.

The grouping inside `bucket_usage` had no test at all -- nothing stubbed `list_objects_v2`
-- so the two-segment `tenants/` split that makes any of this work was unverified.
"""
import os
import pathlib
import sys
import tempfile
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_db_file = pathlib.Path(tempfile.gettempdir()) / f"olrac-attr-{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ.setdefault("SECRET_KEY", "pytest-storage-attribution")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "mock")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mock")

from fastapi.testclient import TestClient  # noqa: E402

from backend import database, models  # noqa: E402
from backend.main import app  # noqa: E402
from backend.services import storage_service  # noqa: E402
from backend.tenancy import TenantScope, require_super_admin  # noqa: E402

models.Base.metadata.create_all(bind=database.engine)


def _stub_bucket(by_prefix):
    """What bucket_usage would have returned after walking a bucket shaped like this."""
    return {
        "configured": True,
        "error": None,
        "bucket": "olrac",
        "total_bytes": sum(v["bytes"] for v in by_prefix.values()),
        "object_count": sum(v["objects"] for v in by_prefix.values()),
        "by_prefix": by_prefix,
        "cached": False,
    }


def _as_super_admin(db):
    # users.organization_id is NOT NULL, so even the platform operator lives in one.
    home = models.Organization(
        name="Platform", slug=f"platform-{uuid.uuid4().hex[:8]}", status="active",
        storage_quota_bytes=0,
    )
    db.add(home)
    db.flush()
    user = models.User(
        username=f"admin-{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="x", role="super_admin", organization_id=home.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_the_tenants_prefix_is_split_on_two_segments_not_one():
    """Without this every workspace collapses into a single row called "tenants"."""
    listed = [
        {"Key": "tenants/Acme-42/general/ad.mp4", "Size": 100},
        {"Key": "tenants/Acme-42/clients/Bob/ads/spot.mp4", "Size": 50},
        {"Key": "tenants/Other-7/general/x.mp4", "Size": 25},
        {"Key": "org-42/legacy.mp4", "Size": 10},
        {"Key": "loose-file.mp4", "Size": 5},
    ]

    class _Paginator:
        def paginate(self, **_kwargs):
            yield {"Contents": listed}

    class _Client:
        def get_paginator(self, _name):
            return _Paginator()

    import backend.media_urls as media_urls

    original_client, original_enabled = media_urls.s3_client, media_urls.is_s3_enabled
    media_urls.s3_client = lambda: _Client()
    media_urls.is_s3_enabled = lambda: True
    try:
        storage_service.forget_cached_usage()
        usage = storage_service.bucket_usage(force=True)
    finally:
        media_urls.s3_client, media_urls.is_s3_enabled = original_client, original_enabled
        storage_service.forget_cached_usage()

    by_prefix = usage["by_prefix"]
    assert by_prefix["tenants/Acme-42"] == {"bytes": 150, "objects": 2}
    assert by_prefix["tenants/Other-7"] == {"bytes": 25, "objects": 1}
    assert by_prefix["org-42"] == {"bytes": 10, "objects": 1}
    assert by_prefix["(no prefix)"] == {"bytes": 5, "objects": 1}
    assert usage["total_bytes"] == 190


def test_one_workspace_under_two_prefixes_is_one_row():
    """The bug on the page: the same tenant counted twice, quota repeated on both."""
    db = database.SessionLocal()
    try:
        org = models.Organization(
            name="Acme", slug=f"acme-{uuid.uuid4().hex[:8]}", status="active",
            storage_quota_bytes=1000,
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        org_id = org.id
        admin = _as_super_admin(db)
    finally:
        db.close()

    usage = _stub_bucket({
        f"org-{org_id}": {"bytes": 300, "objects": 3},
        f"tenants/Acme-{org_id}": {"bytes": 700, "objects": 7},
        # A rename leaves the old slug behind, still carrying the stable trailing id.
        f"tenants/Acme-Old-{org_id}": {"bytes": 100, "objects": 1},
        "mystery": {"bytes": 42, "objects": 1},
    })

    original = storage_service.bucket_usage
    storage_service.bucket_usage = lambda force=False: usage
    app.dependency_overrides[require_super_admin] = lambda: TenantScope(
        db=database.SessionLocal(), user=admin, acting_organization_id=None
    )
    try:
        response = TestClient(app).get("/api/admin/storage")
        assert response.status_code == 200, response.text
        body = response.json()
    finally:
        storage_service.bucket_usage = original
        app.dependency_overrides.pop(require_super_admin, None)

    ours = [row for row in body["tenants"] if row["organization_id"] == org_id]
    assert len(ours) == 1, f"one workspace rendered as {len(ours)} rows"

    row = ours[0]
    assert row["bucket_bytes"] == 1100, "the workspace's prefixes were not summed"
    assert row["bucket_objects"] == 11
    assert row["quota_bytes"] == 1000, "quota must be stated once, not once per prefix"
    for prefix in (f"org-{org_id}", f"tenants/Acme-{org_id}"):
        assert prefix in row["prefix"], f"{prefix} is not named on the merged row"

    orphans = [row for row in body["tenants"] if row["organization_id"] is None]
    assert any("mystery" in row["prefix"] for row in orphans), (
        "a prefix belonging to no workspace must stay visible -- it is still on the bill"
    )


def test_an_empty_workspace_advertises_the_prefix_its_uploads_would_use():
    """It said `org-<id>`, a scheme nothing has minted since tenant_storage_root landed."""
    db = database.SessionLocal()
    try:
        org = models.Organization(
            name="Fresh Co", slug=f"fresh-{uuid.uuid4().hex[:8]}", status="active",
            storage_quota_bytes=500,
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        org_id = org.id
        admin = _as_super_admin(db)
    finally:
        db.close()

    original = storage_service.bucket_usage
    storage_service.bucket_usage = lambda force=False: _stub_bucket({})
    app.dependency_overrides[require_super_admin] = lambda: TenantScope(
        db=database.SessionLocal(), user=admin, acting_organization_id=None
    )
    try:
        body = TestClient(app).get("/api/admin/storage").json()
    finally:
        storage_service.bucket_usage = original
        app.dependency_overrides.pop(require_super_admin, None)

    row = next(r for r in body["tenants"] if r["organization_id"] == org_id)
    assert row["prefix"] == f"tenants/Fresh-Co-{org_id}", row["prefix"]
    assert row["bucket_bytes"] == 0


if __name__ == "__main__":
    try:
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                fn()
                print(f"  ok  {name}")
        print("OK - one row per workspace, however many prefixes it has")
    finally:
        database.engine.dispose()
        _db_file.unlink(missing_ok=True)
