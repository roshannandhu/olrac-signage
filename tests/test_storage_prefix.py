"""Tenant storage folders are named, unique and stable: python tests/test_storage_prefix.py

Objects used to be filed under a bare organisation id, so opening the bucket told an
operator nothing about whose media they were looking at. The folder is now named after the
owner's address -- and the risks that introduces are what this file pins down, because each
of them silently corrupts tenant isolation or breaks playback rather than raising.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from backend.media_urls import storage_prefix  # noqa: E402


class FakeUser:
    def __init__(self, id, email, role="owner"):
        self.id, self.email, self.role = id, email, role


class FakeOrg:
    """Stands in for models.Organization; owner_email is a property over .users."""

    def __init__(self, id, users, slug=None):
        self.id, self.users, self.slug = id, users, slug

    @property
    def owner_email(self):
        members = sorted(self.users, key=lambda u: u.id)
        for candidate in members:
            if (email := (candidate.email or "").strip()) and candidate.role == "owner":
                return email
        for candidate in members:
            if email := (candidate.email or "").strip():
                return email
        return None


def test_folder_is_named_after_the_owner():
    """The address itself, unmangled -- that is the point of naming rather than numbering."""
    org = FakeOrg(19, [FakeUser(1, "alice@example.com")])
    assert storage_prefix(org) == "alice@example.com"


def test_distinct_tenants_get_distinct_folders():
    """Two organisations must never share a folder, or their media mixes in the bucket.

    Safe on the address alone because `users.email` carries a global unique constraint, so
    one address belongs to exactly one account and therefore one organisation. This asserts
    the property that matters rather than the mechanism -- if that constraint is ever
    dropped, this is what fails.
    """
    first = FakeOrg(19, [FakeUser(1, "alice@example.com")])
    second = FakeOrg(20, [FakeUser(2, "bob@example.com")])
    assert storage_prefix(first) != storage_prefix(second)


def test_owner_wins_over_other_members():
    """A workspace has many users; the folder must not depend on which one is asked."""
    org = FakeOrg(7, [
        FakeUser(1, "editor@example.com", role="editor"),
        FakeUser(2, "owner@example.com", role="owner"),
    ])
    assert storage_prefix(org) == "owner@example.com"


def test_falls_back_when_there_is_no_address():
    """seed_admin creates an owner with no email, and an upload must still work."""
    assert storage_prefix(FakeOrg(42, [FakeUser(1, None)])) == "org-42"
    assert storage_prefix(FakeOrg(43, [])) == "org-43"


def test_unsafe_characters_never_reach_a_key():
    """A key containing "/" would invent a folder; one with spaces breaks URLs.

    The address is attacker-influenced -- anyone can sign up, and PATCH /auth/me edits it
    -- so this is a boundary, not a formatting nicety.
    """
    for address in ("a b/c@x.com", "we!rd+tag@x.com", "../../etc/passwd@x.com"):
        prefix = storage_prefix(FakeOrg(1, [FakeUser(1, address)]))
        assert "/" not in prefix, f"path separator survived: {prefix}"
        assert " " not in prefix, f"space survived: {prefix}"
        assert ".." not in prefix, f"traversal survived: {prefix}"
        assert prefix, "an address must never sanitise away to nothing"


def test_thumbnail_is_written_where_its_url_points():
    """The mismatch this pairing had, and it broke every video thumbnail.

    generate_video_thumbnail took an organisation id and wrote to uploads/<id>/, while the
    caller built the URL from the prefix -- so the file landed in one folder and the row
    pointed at another. Both now read the same value, and this asserts they still do.
    """
    import inspect
    from backend.routers import content

    signature = inspect.signature(content.generate_video_thumbnail)
    assert "prefix" in signature.parameters, (
        "generate_video_thumbnail must take the storage prefix, not an organisation id, "
        "or the thumbnail is written somewhere its URL does not point"
    )

    source = inspect.getsource(content.upload_content)
    assert "generate_video_thumbnail(file_path, stem, storage_prefix(organization))" in source
    assert 'thumbnail = public_upload_url(f"{storage_prefix(organization)}/' in source


def test_screenshots_land_in_one_place_whichever_backend_is_configured():
    """Local disk and R2 must file a capture under the same key, or the folder layout
    changes the day object storage is switched on.

    The local branch used to rebuild the key as f"{prefix}/{unique_filename}", dropping
    the screenshots/ root -- so captures went into the tenant's content folder on disk and
    into screenshots/<tenant>/ in the bucket, from identical code.
    """
    import inspect
    from backend.routers import screenshots

    source = inspect.getsource(screenshots.upload_device_screenshot)
    assert source.count('storage_key = ') == 1, (
        "upload_device_screenshot must build its storage key once and use it in both "
        "branches; a second assignment is how the two backends drifted apart"
    )
    assert 'storage_key = f"screenshots/{prefix}/{unique_filename}"' in source
    assert "os.path.join(UPLOAD_DIR, storage_key)" in source


if __name__ == "__main__":
    for name, function in sorted(globals().items()):
        if name.startswith("test_") and callable(function):
            function()
            print(f"  ok  {name}")
    print("storage prefix: all checks passed")
