import argparse
import getpass

from . import database, models
from .routers.auth import get_or_create_default_organization, get_password_hash


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the first OLRAC owner account")
    parser.add_argument("username")
    args = parser.parse_args()
    password = getpass.getpass("Password (minimum 8 characters): ")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters")

    models.Base.metadata.create_all(bind=database.engine)
    db = database.SessionLocal()
    try:
        if db.query(models.User).filter(models.User.username == args.username).first():
            raise SystemExit("That username already exists")
        organization = get_or_create_default_organization(db)
        user = models.User(
            organization_id=organization.id,
            username=args.username,
            hashed_password=get_password_hash(password),
            role="owner",
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"Created owner account: {args.username}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
