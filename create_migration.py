"""
Create migration for UserProfile model

Usage:
    python create_migration.py
"""
import os
import subprocess
import sys

def main():
    """Generate migration for UserProfile model."""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("Generating migration for UserProfile model...")
    
    result = subprocess.run(
        [sys.executable, "-m", "flask", "db", "migrate", "-m", "Add UserProfile model"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error generating migration: {result.stderr}")
        return False
    
    print("Migration generated successfully!")
    print(result.stdout)
    
    print("\nApplying migration...")
    result = subprocess.run(
        [sys.executable, "-m", "flask", "db", "upgrade"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error applying migration: {result.stderr}")
        return False
    
    print("Migration applied successfully!")
    print(result.stdout)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
