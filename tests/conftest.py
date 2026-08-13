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

import subprocess
import sys

import pytest

ISOLATED_SCRIPTS = {
    "test_feature_parity.py",
    "test_tenant_isolation.py",
    "test_quotas.py",
    "test_datetime_aware.py",
    "test_sqlite_utc.py",
    "test_proof_of_play.py",
    "test_analytics.py",
    "test_p6_websockets.py",
    "test_media_selection.py",
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
