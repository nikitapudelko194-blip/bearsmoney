#!/usr/bin/env python3
"""Diagnostic script to check if everything is set up correctly."""
import sys
import os
from pathlib import Path

print("""
╔════════════════════════════════════════════════════════╗
║  🐻 БеарсМани - Diagnostic Check                      ║
╚════════════════════════════════════════════════════════╝
""")

errors = []
warnings = []

# 1. Check Python version
print("\n1️⃣ Checking Python version...")
if sys.version_info < (3, 11):
    errors.append(f"Python 3.11+ required, but you have {sys.version_info.major}.{sys.version_info.minor}")
else:
    print(f"   ✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

# 2. Check .env file
print("\n2️⃣ Checking .env file...")
env_file = Path(".env")
if not env_file.exists():
    errors.append(".env file not found")
else:
    print("   ✅ .env file exists")
    
    # Check required variables
    with open(".env") as f:
        env_content = f.read()
    
    if "BOT_TOKEN=" in env_content:
        if "BOT_TOKEN=" in env_content and "YOUR_" not in env_content.split("BOT_TOKEN=")[1].split("\n")[0]:
            print("   ✅ BOT_TOKEN is set")
        else:
            errors.append("BOT_TOKEN is not properly configured")
    else:
        errors.append("BOT_TOKEN not found in .env")
    
    if "ADMIN_ID=" in env_content:
        admin_id = env_content.split("ADMIN_ID=")[1].split("\n")[0].strip()
        if admin_id.isdigit():
            print(f"   ✅ ADMIN_ID is set ({admin_id})")
        else:
            errors.append(f"ADMIN_ID must be a number, got: {admin_id}")
    else:
        errors.append("ADMIN_ID not found in .env")
    
    if "DATABASE_URL=" in env_content:
        print("   ✅ DATABASE_URL is set")
    else:
        warnings.append("DATABASE_URL not found (will use default)")

# 3. Check project structure
print("\n3️⃣ Checking project structure...")
required_dirs = ["app", "app/database", "app/handlers", "app/services", "app/keyboards", "app/texts", "app/utils", "app/state", "logs"]
for dir_name in required_dirs:
    dir_path = Path(dir_name)
    if dir_path.exists():
        print(f"   ✅ {dir_name}/")
    else:
        if dir_name == "logs":
            print(f"   ⚠️  {dir_name}/ (will be created automatically)")
        else:
            errors.append(f"Directory {dir_name}/ not found")

# 4. Check required files
print("\n4️⃣ Checking required files...")
required_files = [
    "main.py",
    "config.py",
    "requirements.txt",
    "app/__init__.py",
    "app/bot.py",
    "app/database/models.py",
    "app/database/db.py",
    "app/handlers/start.py",
    "app/services/economy.py"
]
for file_name in required_files:
    file_path = Path(file_name)
    if file_path.exists():
        print(f"   ✅ {file_name}")
    else:
        errors.append(f"File {file_name} not found")

# 5. Check Python modules
print("\n5️⃣ Checking Python modules...")
modules_to_check = [
    ("aiogram", "aiogram"),
    ("sqlalchemy", "sqlalchemy"),
    ("aiosqlite", "aiosqlite"),
    ("dotenv", "python-dotenv"),
    ("asyncio", "asyncio (built-in)"),
]

for import_name, package_name in modules_to_check:
    try:
        __import__(import_name)
        print(f"   ✅ {package_name}")
    except ImportError:
        warnings.append(f"Missing module: {package_name} (install with: pip install {package_name})")

# 6. Print results
print("\n" + "="*60)
print("\n📊 RESULTS:")

if errors:
    print(f"\n❌ ERRORS ({len(errors)}):")
    for i, error in enumerate(errors, 1):
        print(f"   {i}. {error}")

if warnings:
    print(f"\n⚠️  WARNINGS ({len(warnings)}):")
    for i, warning in enumerate(warnings, 1):
        print(f"   {i}. {warning}")

if not errors and not warnings:
    print("\n✅ Everything looks good! You can run: python main.py")
elif not errors:
    print("\n😜 Some warnings found, but bot might work. Run: python main.py")
else:
    print("\n❌ Please fix the errors above before running the bot")
    print("\n📋 Run: pip install -r requirements.txt")

print("\n" + "="*60 + "\n")

sys.exit(0 if not errors else 1)
