#!/usr/bin/env python3
"""Local administrator utilities. Run inside the API container."""
import getpass, re, sys
from server import connect, password_hash

def reset_password(email):
    email=email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email):raise SystemExit("Invalid email address")
    password=getpass.getpass("New password (minimum 12 characters): ")
    confirm=getpass.getpass("Confirm password: ")
    if len(password)<12 or len(password)>256:raise SystemExit("Password must be 12–256 characters")
    if password!=confirm:raise SystemExit("Passwords do not match")
    with connect() as db:
        cur=db.execute("UPDATE users SET password_hash=? WHERE email=?",(password_hash(password),email))
        if cur.rowcount!=1:raise SystemExit("Account not found")
        db.execute("DELETE FROM sessions WHERE user_id=(SELECT id FROM users WHERE email=?)",(email,))
    print("Password updated; all existing sessions revoked.")

if __name__=="__main__":
    if len(sys.argv)!=3 or sys.argv[1]!="reset-password":
        raise SystemExit("Usage: python local_backend/admin.py reset-password user@example.com")
    reset_password(sys.argv[2])
