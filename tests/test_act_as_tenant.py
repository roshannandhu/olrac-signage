"""A platform operator can step into ONE workspace, and only a platform operator can.

Admin is a control plane, so an operator has to be able to run a tenant's workspace --
book an advert, repair a playlist -- through the ordinary tenant endpoints. That is the
X-Act-As-Org header, and it is impersonation: everything here is about it being narrow.

It also closes a hazard that predates it. A super_admin had `query()` with the organisation
filter DROPPED (every tenant's rows at once) while `organization_id` still returned their
own org -- so the dashboard showed a soup of all workspaces and anything created was filed
under the operator's own organisation.

Throwaway Postgres database. Run directly:  python tests/test_act_as_tenant.py
"""
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SCRATCH = f"olrac_actas_{uuid.uuid4().hex[:8]}"
os.environ["DATABASE_URL"] = f"postgresql://olrac:olrac_password@localhost:5432/{SCRATCH}"
os.environ["SECRET_KEY"] = "act-as-test-secret"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"
os.environ["AWS_SECRET_ACCESS_KEY"] = "mock"

import psycopg2  # noqa: E402
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT  # noqa: E402

admin_conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
admin_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
admin_conn.cursor().execute(f'CREATE DATABASE "{SCRATCH}" OWNER olrac')

db = None
try:
    from fastapi.testclient import TestClient  # noqa: E402
    from backend import models  # noqa: E402
    from backend.database import SessionLocal, engine  # noqa: E402
    from backend.main import app  # noqa: E402
    from backend.routers.auth import create_access_token, get_password_hash  # noqa: E402

    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Two customer workspaces plus the operator's own.
    alpha = models.Organization(name="Alpha", slug="alpha", status="active")
    beta = models.Organization(name="Beta", slug="beta", status="active")
    platform = models.Organization(name="Platform", slug="platform", status="active")
    db.add_all([alpha, beta, platform]); db.commit()

    operator = models.User(organization_id=platform.id, username="ops@olrac.test",
                           hashed_password=get_password_hash("x"), role="super_admin",
                           is_active=True)
    alpha_owner = models.User(organization_id=alpha.id, username="owner@alpha.test",
                              hashed_password=get_password_hash("x"), role="owner",
                              is_active=True)
    db.add_all([operator, alpha_owner]); db.commit()

    db.add_all([
        models.Screen(organization_id=alpha.id, name="Alpha Lobby", status="online"),
        models.Screen(organization_id=alpha.id, name="Alpha Cafe", status="online"),
        models.Screen(organization_id=beta.id, name="Beta Foyer", status="online"),
    ])
    db.commit()

    http = TestClient(app)
    ops = {"Authorization": f"Bearer {create_access_token(data={'sub': operator.username})}"}
    tenant = {"Authorization": f"Bearer {create_access_token(data={'sub': alpha_owner.username})}"}

    def screen_names(headers):
        r = http.get("/api/screens/", headers=headers)
        assert r.status_code == 200, r.text
        return sorted(s["name"] for s in r.json())

    # --- without the header, nothing about the operator changes ---------------------------
    assert screen_names(ops) == ["Alpha Cafe", "Alpha Lobby", "Beta Foyer"], (
        "an operator with no workspace chosen should still see across the platform"
    )
    print("  ok  an operator with no workspace chosen sees the platform as before")

    # --- inside a workspace the operator sees that workspace ONLY --------------------------
    inside_alpha = {**ops, "X-Act-As-Org": str(alpha.id)}
    assert screen_names(inside_alpha) == ["Alpha Cafe", "Alpha Lobby"], (
        "acting inside Alpha must not show Beta's screens"
    )
    inside_beta = {**ops, "X-Act-As-Org": str(beta.id)}
    assert screen_names(inside_beta) == ["Beta Foyer"], "Alpha's rows leaked into Beta"
    print("  ok  inside a workspace the operator sees that workspace only, both ways round")

    # --- what the operator creates belongs to the TENANT, not to the operator -------------
    made = http.post("/api/groups/", headers=inside_alpha, json={"name": "Made by ops"})
    assert made.status_code == 201, made.text
    db.expire_all()
    group = db.query(models.ScreenGroup).filter(models.ScreenGroup.name == "Made by ops").one()
    assert group.organization_id == alpha.id, (
        f"a group created inside Alpha was filed under organisation {group.organization_id}, "
        f"not Alpha ({alpha.id}) -- this is the bug that put tenant data in the operator's org"
    )
    # And the tenant can see it, because it really is theirs.
    listed = http.get("/api/groups/", headers=tenant)
    assert any(g["name"] == "Made by ops" for g in listed.json()), listed.text
    print("  ok  what an operator creates inside a workspace belongs to that workspace")

    # --- the header is an operator capability, not a user-supplied one ---------------------
    # A tenant sending it is ignored outright rather than told the mechanism exists.
    smuggled = {**tenant, "X-Act-As-Org": str(beta.id)}
    assert screen_names(smuggled) == ["Alpha Cafe", "Alpha Lobby"], (
        "a tenant set the header and reached another workspace"
    )
    print("  ok  a tenant sending the header is ignored and stays in its own workspace")

    # --- bad input -------------------------------------------------------------------------
    assert http.get("/api/screens/", headers={**ops, "X-Act-As-Org": "999999"}).status_code == 404
    assert http.get("/api/screens/", headers={**ops, "X-Act-As-Org": "not-a-number"}).status_code == 422
    # An empty header is "not acting", not an error -- it is what the dashboard sends when
    # the operator has left the workspace.
    assert http.get("/api/screens/", headers={**ops, "X-Act-As-Org": ""}).status_code == 200
    print("  ok  unknown workspace 404s, a malformed header 422s, an empty one just means 'not acting'")

    # --- a tenant is unaffected throughout -------------------------------------------------
    assert screen_names(tenant) == ["Alpha Cafe", "Alpha Lobby"], (
        "ordinary tenant scoping changed"
    )
    print("  ok  ordinary tenant scoping is untouched")

    print("act as tenant: all checks passed")
finally:
    try:
        if db: db.close()
    except Exception:
        pass
    try:
        engine.dispose()
    except Exception:
        pass
    try:
        admin_conn.cursor().execute(f'DROP DATABASE IF EXISTS "{SCRATCH}" WITH (FORCE)')
    except Exception:
        pass
    admin_conn.close()
