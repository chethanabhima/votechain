
"""
Vote Chain — Setup Script
Run this once before starting the app.
"""
import os
import sys

print("=" * 50)
print("  VOTE CHAIN — Setup")
print("=" * 50)

os.makedirs("instance", exist_ok=True)

try:
    from database import init_db
    init_db()
    print("✓ Database initialized")
    print("✓ RSA keys generated (instance/keys.txt)")
    print("✓ Genesis block created")
    print("✓ Sample voters loaded")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

print("\nSample voter credentials:")
print("  VC001 / DOB: 1990-03-15  (Arjun Sharma)")
print("  VC002 / DOB: 1985-07-22  (Priya Nair)")
print("  VC003 / DOB: 1998-11-05  (Rohan Mehta)")
print("  VC004 / DOB: 2000-01-30  (Sneha Iyer)")
print("  VC005 / DOB: 1975-09-18  (Vikram Patel)")
print("\nAdmin credentials:")
print("  Email:    admin@votechain.com")
print("  Password: votechain123")
print("\nRun: python app.py")
print("Open: http://localhost:5000")
print("=" * 50)
