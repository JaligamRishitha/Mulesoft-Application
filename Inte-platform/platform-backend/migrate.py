#!/usr/bin/env python3
"""
Database migration script to create user_creation_approvals table
"""
from app.database import engine, Base
from app.models import UserCreationApproval

def run_migration():
    print("Starting database migration...")
    print(f"Database URL: {engine.url}")

    try:
        # Create all tables defined in models
        Base.metadata.create_all(bind=engine)
        print("✓ Successfully created user_creation_approvals table")
        print("✓ Migration completed successfully")
        return True
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False

if __name__ == "__main__":
    run_migration()
