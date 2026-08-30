import sys, os
sys.path.insert(0, os.path.abspath("."))
from backend.database import SessionLocal
from backend.models import Organization, User, Plan
from backend.routers.auth import get_password_hash

def main():
    db = SessionLocal()
    
    # 1. Update Organization 1 to captab221's Org
    org = db.query(Organization).filter(Organization.id == 1).first()
    if org:
        org.name = "captab221's Org"
        org.slug = "captab221-org"
        org.plan_id = 3  # Business plan (50+ screens)
        org.storage_quota_bytes = 50 * 1024 * 1024 * 1024
        db.commit()
        db.refresh(org)
        print(f"Updated Organization: '{org.name}' (ID: {org.id}, Slug: '{org.slug}')")
        
    # 3. Create or update Owner User
    user = db.query(User).filter(User.username == "juug22btech48491@gmail.com").first()
    if not user:
        user = User(
            organization_id=org.id,
            username="juug22btech48491@gmail.com",
            email="juug22btech48491@gmail.com",
            full_name="Roshan Raj",
            role="owner",
            is_active=True,
            hashed_password=get_password_hash("Roshan@1100")
        )
        db.add(user)
        print("Created User: juug22btech48491@gmail.com with password 'Roshan@1100'")
    else:
        user.organization_id = org.id
        user.email = "juug22btech48491@gmail.com"
        user.hashed_password = get_password_hash("Roshan@1100")
        user.role = "owner"
        user.is_active = True
        print("Updated User: juug22btech48491@gmail.com with password 'Roshan@1100'")
        
    # 4. Also add admin fallback
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        admin_user = User(
            organization_id=org.id,
            username="admin",
            email="admin@olrac.com",
            full_name="Admin",
            role="owner",
            is_active=True,
            hashed_password=get_password_hash("Admin12345")
        )
        db.add(admin_user)
        print("Created User: admin with password 'Admin12345'")

    db.commit()
    print("Database seeding completed successfully on new Supabase account!")
    db.close()

if __name__ == "__main__":
    main()
