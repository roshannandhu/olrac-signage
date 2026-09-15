"""A stored storage credential that cannot be one must not switch object storage on.

Production held the admin's login email as the access key and a password as the secret --
a browser autofill into the old storage form. Because a stored override beats the
environment, that pair made every media URL unsignable and every TV report its adverts as
undownloadable, while the files sat intact in the database mirror.
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
os.environ.pop("PYTEST_CURRENT_TEST", None)
os.environ["AWS_ACCESS_KEY_ID"] = "mock"
os.environ["AWS_SECRET_ACCESS_KEY"] = "mock"

from backend import media_urls  # noqa: E402

REAL_SHAPED_KEY = "0" * 32
REAL_SHAPED_SECRET = "a" * 64


def test_login_pair_typed_into_the_storage_form_is_ignored():
    media_urls.apply_storage_overrides({
        "AWS_ACCESS_KEY_ID": "admin@olrac.com",
        "AWS_SECRET_ACCESS_KEY": "pass@word1",
        "S3_ENDPOINT_URL": "https://example.r2.cloudflarestorage.com",
    })
    assert media_urls.get_s3_config()["aws_access_key_id"] != "admin@olrac.com"
    assert not media_urls.is_s3_enabled(), "a login email switched object storage on"
    # Non-credential settings are not second-guessed.
    assert "S3_ENDPOINT_URL" in media_urls.storage_override_names()


def test_credential_shaped_override_still_applies():
    media_urls.apply_storage_overrides({
        "AWS_ACCESS_KEY_ID": REAL_SHAPED_KEY,
        "AWS_SECRET_ACCESS_KEY": REAL_SHAPED_SECRET,
    })
    assert media_urls.get_s3_config()["aws_access_key_id"] == REAL_SHAPED_KEY
    assert media_urls.is_s3_enabled()
    media_urls.apply_storage_overrides({})


if __name__ == "__main__":
    test_login_pair_typed_into_the_storage_form_is_ignored()
    test_credential_shaped_override_still_applies()
    print("OK - only credential-shaped overrides reach object storage")
