"""Deleting an asset actually deletes it, and says so when it cannot.

The reported bug was "deleting an ad does not remove it from the bucket", and the delete
call was already there. What was missing was any way to find out it had failed:
`media_storage.delete` caught every exception and returned a bare False that the caller
discarded, and it never checked whether storage was configured at all -- so on a deployment
with no credentials every delete was a silent no-op while the rows went away regardless.

The second leak is quieter and has no bucket in it. Media was served out of a Postgres
`media_blob` mirror for as long as R2 was unconfigured, and nothing in the codebase has ever
deleted a row from that table: `grep -ri media_blob` finds two files, and both only read.
Every asset deleted in that period still has its bytes in the database, where no bucket
sweep can see them and no quota reflects them.

Runs with AWS_ACCESS_KEY_ID=mock, which is exactly the "storage not configured" state the
bug needs -- so these assertions are about the deployment that actually broke.
"""
import logging
import os
import pathlib
import sys
import tempfile
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_db_file = pathlib.Path(tempfile.gettempdir()) / f"olrac-media-del-{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ.setdefault("SECRET_KEY", "pytest-media-deletion")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "mock")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mock")

from sqlalchemy import text  # noqa: E402

from backend import database, media_storage, models  # noqa: E402

models.Base.metadata.create_all(bind=database.engine)


def _create_mirror():
    """The out-of-band table: no model, no migration, so tests build it by hand too."""
    with database.engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS media_blob"))
        connection.execute(text(
            "CREATE TABLE media_blob ("
            "  key TEXT PRIMARY KEY,"
            "  content_type TEXT,"
            "  data BLOB,"
            "  size_bytes INTEGER"
            ")"
        ))


def _drop_mirror():
    with database.engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS media_blob"))


def _mirror_rows(key):
    with database.engine.connect() as connection:
        return connection.execute(
            text("SELECT COUNT(*) FROM media_blob WHERE key = :key"), {"key": key}
        ).scalar()


def _mirror(key, payload=b"bytes"):
    with database.engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO media_blob (key, content_type, data, size_bytes)"
                " VALUES (:key, :ct, :data, :size)"
            ),
            {"key": key, "ct": "video/mp4", "data": payload, "size": len(payload)},
        )


def test_deleting_an_object_clears_the_database_mirror():
    """The live leak: nothing in the codebase has ever deleted one of these rows."""
    _create_mirror()
    key = f"org-1/{uuid.uuid4().hex}.mp4"
    _mirror(key)
    assert _mirror_rows(key) == 1

    media_storage.delete(f"s3://{key}")

    assert _mirror_rows(key) == 0, "the Postgres mirror kept the bytes of a deleted asset"


def test_the_mirror_is_cleared_for_local_files_too():
    """Which backend held the object does not change who else is holding a copy."""
    _create_mirror()
    key = f"org-2/{uuid.uuid4().hex}.mp4"
    _mirror(key)

    target = pathlib.Path(media_storage.UPLOAD_DIR) / key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"bytes")

    assert media_storage.delete(f"/uploads/{key}") is True
    assert not target.exists()
    assert _mirror_rows(key) == 0


def test_a_missing_mirror_table_is_not_an_error():
    """Most deployments never had this table. Its absence must not break deleting."""
    _drop_mirror()
    try:
        # Must not raise. The object is not deletable without credentials, which is a
        # different answer from "this blew up".
        assert media_storage.delete("s3://org-3/nothing.mp4") is False
    finally:
        _create_mirror()


def test_unconfigured_storage_reports_the_miss_instead_of_swallowing_it(caplog=None):
    """The actual bug. False was already returned; nobody could tell why, or that it was."""
    _create_mirror()
    records = []

    class _Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = _Capture()
    logger = logging.getLogger("backend.media_storage")
    logger.addHandler(handler)
    previous_level = logger.level
    logger.setLevel(logging.WARNING)
    try:
        assert media_storage.delete("s3://org-4/orphan.mp4") is False
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    assert records, "a failed delete produced no log line at all"
    message = records[0].getMessage()
    assert "org-4/orphan.mp4" in message, "the log does not say WHICH object was left"
    assert "not configured" in message, "the log does not distinguish this from a refusal"


def test_an_unrecognised_location_is_refused_rather_than_guessed():
    """An external URL is not ours to delete, and must not be parsed into a bucket key."""
    assert media_storage.delete("https://example.com/somebody-elses.mp4") is False
    assert media_storage.delete("") is False
    assert media_storage.delete(None) is False


if __name__ == "__main__":
    try:
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                fn()
                print(f"  ok  {name}")
        print("OK - deletes reach every copy, and announce the ones that did not")
    finally:
        database.engine.dispose()
        _db_file.unlink(missing_ok=True)
