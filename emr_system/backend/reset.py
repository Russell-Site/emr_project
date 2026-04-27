# ============================================================
# reset_admin_password.py
# I-run ito ONCE para i-update ang admin password hash
# sa database na compatible sa Python 3.14 + bcrypt
#
# Paano gamitin:
#   python reset_admin_password.py
# ============================================================

import sys
import os

# I-load ang .env
from dotenv import load_dotenv
load_dotenv()

# I-import ang database at models
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.models import User
from utils.security import hash_password, verify_password

def reset_admin_password():
    """
    I-update ang admin password hash sa database.
    Gagamitin ang bagong bcrypt hashing na compatible sa Python 3.14.
    """
    db = SessionLocal()

    try:
        # Hanapin ang admin account
        admin = db.query(User).filter(User.email == "admin@vienterreales.gov.ph").first()

        if not admin:
            print("❌ Admin account not found!")
            print("   Siguraduhing na-run na ang schema.sql sa database.")
            return False

        # I-set ang bagong password hash para sa "Admin@123"
        new_password   = "Admin@123"
        new_hash       = hash_password(new_password)

        admin.password_hash     = new_hash
        admin.failed_attempts   = 0
        admin.locked_until      = None
        admin.status            = "active"

        db.commit()

        # I-verify na gumagana ang bagong hash
        if verify_password(new_password, new_hash):
            print("✅ Admin password reset successfully!")
            print(f"   Email:    admin@district1.gov.ph")
            print(f"   Password: Admin@123")
            print()
            print("⚠️  PALITAN ANG PASSWORD AGAD PAGKATAPOS NG LOGIN!")
            return True
        else:
            print("❌ Password verification failed after reset!")
            return False

    except Exception as e:
        db.rollback()
        print(f"❌ Error resetting admin password: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("  EMR System — Admin Password Reset Tool")
    print("=" * 50)
    print()
    reset_admin_password()
    print()
    print("Done. You can now restart the server and login.")