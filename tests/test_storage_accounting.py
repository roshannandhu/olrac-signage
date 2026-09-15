"""One answer to "how much storage is this workspace using".

Three places computed it and only the one that REFUSED uploads counted renditions. A
transcode writes a full-size master and a smaller copy on top of the upload, so the admin
console and the tenant's own billing page — both summing Content alone — showed roughly a
third of the truth. A tenant read "3 GB of 10 GB used" and was then refused the next upload
for being full, which is the same disease as the screen limit before effective_max_screens:
the number shown and the number enforced reading different things.

Also covers attributing bucket objects to workspaces, since a prefix that names no
workspace is real money being spent on nothing.
"""
import os
import pathlib
import sys
import tempfile
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_db_file = pathlib.Path(tempfile.gettempdir()) / f"olrac-storage-{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ.setdefault("SECRET_KEY", "pytest-storage-accounting")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "mock")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mock")

from backend import database, models  # noqa: E402
import backend.main  # noqa: E402,F401  (import order; see test_subscription_expiry)
from backend.services.storage_service import (  # noqa: E402
    organization_id_from_prefix,
    organization_storage_used,
)

models.Base.metadata.create_all(bind=database.engine)

MB = 1024 * 1024


def test_renditions_count_towards_a_workspaces_storage():
    """The whole bug: a video's renditions are objects the workspace caused to exist."""
    db = database.SessionLocal()
    try:
        org = models.Organization(name="Co", slug=f"o-{uuid.uuid4().hex[:8]}", status="active")
        db.add(org)
        db.flush()

        content = models.Content(
            organization_id=org.id, type="video", file_url="s3://org/x.mp4",
            name="Advert", file_size_bytes=10 * MB, status="ready",
        )
        db.add(content)
        db.flush()
        db.add_all([
            models.MediaRendition(
                content_id=content.id, resolution="1080p", width=1920, height=1080,
                rotation=0, file_size_bytes=6 * MB, file_url="s3://org/x_1080p.mp4",
            ),
            models.MediaRendition(
                content_id=content.id, resolution="480p", width=854, height=480,
                rotation=0, file_size_bytes=2 * MB, file_url="s3://org/x_480p.mp4",
            ),
        ])
        db.commit()

        used = organization_storage_used(db, org.id)
        # 10 + 6 + 2. Summing the source alone gives 10 -- well under half, which is how a
        # full workspace looked like it had room to spare.
        assert used == 18 * MB, f"expected 18MB, got {used / MB}MB"
    finally:
        db.close()


def test_a_workspace_with_nothing_uses_nothing():
    """Must be 0, not None -- callers compare it and format it."""
    db = database.SessionLocal()
    try:
        org = models.Organization(name="Empty", slug=f"e-{uuid.uuid4().hex[:8]}", status="active")
        db.add(org)
        db.commit()
        assert organization_storage_used(db, org.id) == 0
    finally:
        db.close()


def test_one_workspaces_files_are_not_counted_against_another():
    db = database.SessionLocal()
    try:
        a = models.Organization(name="A", slug=f"a-{uuid.uuid4().hex[:8]}", status="active")
        b = models.Organization(name="B", slug=f"b-{uuid.uuid4().hex[:8]}", status="active")
        db.add_all([a, b])
        db.flush()
        db.add(models.Content(
            organization_id=a.id, type="image", file_url="s3://a/1.png",
            name="A's", file_size_bytes=5 * MB, status="ready",
        ))
        db.commit()
        assert organization_storage_used(db, a.id) == 5 * MB
        assert organization_storage_used(db, b.id) == 0
    finally:
        db.close()


def test_bucket_prefixes_map_back_to_workspaces():
    """"org-<id>" and "tenants/<slug>-<id>" map back to their workspace id; anything else names nobody."""
    assert organization_id_from_prefix("tenants/Roshan-Nandhu-67") == 67
    assert organization_id_from_prefix("tenants/Acme-Corp-42") == 42
    assert organization_id_from_prefix("org-67") == 67
    assert organization_id_from_prefix("org-1") == 1
    # Real prefixes seen in the production bucket, both predating the convention. They are
    # bytes on the bill belonging to no workspace, which is exactly what must be surfaced
    # rather than silently folded into a total.
    assert organization_id_from_prefix("roshannandhu1100@gmail.com") is None
    assert organization_id_from_prefix("7") is None
    assert organization_id_from_prefix("shared") is None
    assert organization_id_from_prefix("org-") is None
    assert organization_id_from_prefix("org-abc") is None
    assert organization_id_from_prefix("tenants/no-id") is None


def test_measuring_the_bucket_never_raises_without_credentials():
    """The admin console must load and SAY storage is unreachable, not fail to render."""
    from backend.services.storage_service import bucket_usage

    usage = bucket_usage(force=True)
    assert usage["configured"] is False
    assert usage["total_bytes"] == 0
    assert usage["by_prefix"] == {}
    assert usage["error"]


if __name__ == "__main__":
    try:
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                fn()
                print(f"  ok  {name}")
        print("OK - one storage number, and bucket objects attributed to workspaces")
    finally:
        database.engine.dispose()
        _db_file.unlink(missing_ok=True)
