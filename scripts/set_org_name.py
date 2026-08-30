import sys, os
sys.path.insert(0, os.path.abspath("."))
from backend.database import SessionLocal
from backend.models import Organization, User, Screen

def main():
    db = SessionLocal()
    org = db.query(Organization).filter(Organization.id == 1).first()
    if org:
        org.name = "captab221's Org"
        org.slug = "captab221-org"
        db.commit()
        db.refresh(org)
        print(f"Updated Organization ID={org.id}: Name='{org.name}', Slug='{org.slug}'")
    else:
        print("Organization not found!")
    
    users = db.query(User).filter(User.organization_id == 1).all()
    print("Users in Org:")
    for u in users:
        print(f" - {u.username} ({u.email}) Role: {u.role}")

    screens = db.query(Screen).filter(Screen.organization_id == 1).all()
    print("Screens in Org:")
    for s in screens:
        print(f" - Screen ID {s.id}: '{s.name}' (Device: {s.device_id}, Status: {s.status})")
    
    db.close()

if __name__ == "__main__":
    main()
