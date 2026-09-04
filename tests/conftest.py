"""Run each backend test script in its own process.

`backend/database.py` builds the SQLAlchemy engine at import time from
DATABASE_URL. Each test script points that variable at its own temporary
database, but a single pytest process imports every module together, so the
first import wins and the rest end up querying a database that has already been
torn down — every script passes alone and the suite fails as a whole.

Collecting these files as subprocesses fixes it at the root: one process per
script, one engine per database, and no import-order coupling. It also keeps
each file directly runnable (`python tests/test_quotas.py`).
"""

import os
import pathlib
import socket
import subprocess
import sys

import pytest

# Point the in-process engine somewhere harmless BEFORE any test module is imported.
#
# backend/database.py calls load_dotenv() and builds its engine at import, so whichever
# module imports backend first decides the database for the whole pytest process -- and
# the modules in python_files are imported in alphabetical order, most of which never set
# DATABASE_URL. With a developer's backend/.env present, the first importer therefore bound
# the engine to the REAL database: verified, it resolved to the production Supabase host,
# and test_media_worker's uploads landed there. That is how its rendition count grew run
# over run (2, then 4) and failed only in a full-suite run, never alone.
#
# Set here rather than in each module because it has to happen before the first import, and
# because a rule that every new test file must remember is one that will eventually be
# forgotten -- exactly as it was. Scripts in ISOLATED_SCRIPTS run as subprocesses and set
# their own DATABASE_URL, which still wins.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("SECRET_KEY", "pytest-in-process-secret")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "mock")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mock")

ISOLATED_SCRIPTS = {
    "test_feature_parity.py",
    "test_tenant_isolation.py",
    "test_quotas.py",
    "test_datetime_aware.py",
    "test_sqlite_utc.py",
    "test_proof_of_play.py",
    "test_play_log_attribution.py",
    "test_account_profile.py",
    "test_screen_approval.py",
    "test_platform_admin.py",
    "test_reinstall_reconnect.py",
    "test_role_separation.py",
    "test_signup_lifecycle.py",
    "test_analytics.py",
    "test_p6_websockets.py",
    "test_media_selection.py",
    # These six were written, committed, and then never run: they were absent from this
    # set and from python_files in pytest.ini, so pytest collected neither. The suite
    # reported success while six files' worth of assertions sat untouched. The guard in
    # `pytest_collection_finish` below now makes that state impossible to reach again.
    "test_ad_placements.py",
    "test_booking_report.py",
    "test_tenant_plans.py",
    "test_ad_payments.py",
    "test_media_report.py",
    "test_reinstall_dedup.py",
    "test_storage_cleanup.py",
    "test_sync_invalidation.py",
    "test_release_rollout.py",
    # Google sign-in: authorisation, a case-insensitive lookup and a tenant guard.
    # Owns a database, so it belongs here rather than in pytest.ini.
    "test_google_signin.py",
    # Proves a websocket does not pin a pooled database connection.
    "test_ws_connection_pool.py",
    # Exercises the S3 branch that test_storage_cleanup disables.
    "test_r2_cleanup.py",
    "test_storage_budget.py",
    "test_bring_to_front.py",
    "test_ad_counting_detail.py",
    "test_counting_integrity.py",
    "test_all_five_areas_e2e.py",
    # Removing a TV: play history survives, the panel is signed out, quota is freed.
    "test_screen_removal.py",
    # The screen cap: package limits, admin overrides, and the /enroll bypass.
    "test_screen_quota.py",
    # One booking, different run lengths per location.
    "test_per_location_ad_window.py",
    # The dashboard and the player must resolve the same playlist for a screen.
    "test_playlist_resolution_parity.py",
    # The client-ad editor obeys the same booking rules as the placements routes.
    "test_client_ad_editor.py",
}

# Pure-logic tests: no database, no import-time engine, safe to run in-process.
# Listed here only so the orphan guard knows they are accounted for; pytest.ini's
# python_files is what actually collects them.
PURE_MODULES = {
    "test_media_worker.py",
    "test_rotation.py",
    "test_rollout_policy.py",
    "test_media_storage.py",
    "test_alerting.py",
    "test_maps_link.py",
    "test_rendition_defaults.py",
    # Pure logic over a fake Organization; no database, no engine at import.
    "test_storage_prefix.py",
    # Pure string rewriting over the TV hand-back link; reads no rows.
    "test_tv_deep_link.py",
    # Pricing a custom run in screen-days; arithmetic over a fake plan, no session.
    "test_plan_quote.py",
}


def _postgres_reachable() -> bool:
    """Whether a server is listening on the port the scripts create their databases on.

    Cached for the run: 16 scripts would otherwise each pay the connect timeout.
    """
    global _PG_REACHABLE
    if _PG_REACHABLE is None:
        probe = socket.socket()
        probe.settimeout(3)
        try:
            probe.connect(("127.0.0.1", 5432))
            _PG_REACHABLE = True
        except OSError:
            _PG_REACHABLE = False
        finally:
            probe.close()
    return _PG_REACHABLE


_PG_REACHABLE = None

# Scripts that build their own throwaway Postgres database and cannot run without a
# server. Distinguished from the rest so that a machine with no database reports "these
# were skipped, and why" rather than sixteen identical connection tracebacks that bury
# whatever else went wrong in the run.
NEEDS_POSTGRES = ISOLATED_SCRIPTS - {
    "test_sqlite_utc.py",
    "test_release_rollout.py",
    # Falls back to SQLite when no server is listening; nothing it checks is
    # dialect-specific, so it still runs on a machine with no database.
    "test_google_signin.py",
    # Skips itself when Redis is absent; falls back to SQLite otherwise.
    "test_ws_connection_pool.py",
    # Playlist resolution is plain Python over the ORM, so SQLite exercises it fully.
    "test_playlist_resolution_parity.py",
}


def pytest_collect_file(parent, file_path):
    if file_path.name in ISOLATED_SCRIPTS:
        return ScriptFile.from_parent(parent, path=file_path)
    return None


def pytest_collection_modifyitems(config, items):
    """Fail loudly if a script also got imported as a module.

    pytest.ini restricts `python_files` so these scripts are never imported, but that is
    easy to undo by accident. If both collectors ever pick up the same file the suite
    silently loses its database isolation, so surface it instead.
    """
    seen = {}
    for item in items:
        name = getattr(item.path, "name", None)
        if name in ISOLATED_SCRIPTS:
            seen.setdefault(name, []).append(type(item).__name__)
    doubled = {n: k for n, k in seen.items() if len(k) > 1}
    if doubled:
        raise pytest.UsageError(
            "These files were collected twice (as a script AND as a module), which breaks "
            f"database isolation: {doubled}. Check python_files in pytest.ini."
        )


class ScriptFile(pytest.File):
    def collect(self):
        yield ScriptItem.from_parent(self, name=self.path.stem)


class ScriptItem(pytest.Item):
    def runtest(self):
        if self.path.name in NEEDS_POSTGRES and not _postgres_reachable():
            pytest.skip(
                "PostgreSQL is not reachable on localhost:5432; this script creates its "
                "own throwaway database and cannot run without a server"
            )
        result = subprocess.run(
            [sys.executable, str(self.path)],
            capture_output=True,
            text=True,
            cwd=str(self.path.parents[1]),
        )
        if result.returncode != 0:
            raise AssertionError(
                f"{self.path.name} exited {result.returncode}\n"
                f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
            )

    def repr_failure(self, excinfo):
        return str(excinfo.value)

    def reportinfo(self):
        return self.path, 0, f"script: {self.path.name}"


def pytest_collection_finish(session):
    """Fail if any tests/test_*.py is collected by neither mechanism.

    A file that is in neither ISOLATED_SCRIPTS nor python_files is simply not run, and
    nothing says so -- the suite still exits 0. Six files sat in that state. Checking the
    directory against both registries turns a silent omission into a failed run.
    """
    directory = pathlib.Path(__file__).parent
    on_disk = {p.name for p in directory.glob("test_*.py")}
    registered = ISOLATED_SCRIPTS | PURE_MODULES
    orphans = sorted(on_disk - registered)
    if orphans:
        raise pytest.UsageError(
            "These test files are not collected by anything and never ran: "
            f"{orphans}. Add each to ISOLATED_SCRIPTS in tests/conftest.py (if it owns "
            "a database) or to python_files in pytest.ini (if it is pure logic)."
        )
    missing = sorted(registered - on_disk)
    if missing:
        raise pytest.UsageError(
            f"These files are registered but do not exist: {missing}."
        )
