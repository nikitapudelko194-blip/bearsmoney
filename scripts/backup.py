#!/usr/bin/env python3
"""Database backup script."""
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuration
DB_PATH = "app/database/bears_money.db"
BACKUP_DIR = "backups"
MAX_BACKUPS = 7  # Keep last 7 backups


def create_backup():
    """Create database backup."""
    try:
        # Create backup directory
        backup_path = Path(BACKUP_DIR)
        backup_path.mkdir(exist_ok=True)
        
        # Generate backup filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_path / f"bears_money_backup_{timestamp}.db"
        
        # Copy database
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, backup_file)
            logger.info(f"✅ Backup created: {backup_file}")
            
            # Cleanup old backups
            cleanup_old_backups()
            
            return True
        else:
            logger.error(f"❌ Database not found: {DB_PATH}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}", exc_info=True)
        return False


def cleanup_old_backups():
    """Remove old backups, keep only MAX_BACKUPS."""
    try:
        backup_path = Path(BACKUP_DIR)
        backups = sorted(backup_path.glob("bears_money_backup_*.db"))
        
        if len(backups) > MAX_BACKUPS:
            for old_backup in backups[:-MAX_BACKUPS]:
                old_backup.unlink()
                logger.info(f"🗑️ Removed old backup: {old_backup}")
    
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}", exc_info=True)


def restore_backup(backup_file: str):
    """Restore database from backup."""
    try:
        if not os.path.exists(backup_file):
            logger.error(f"❌ Backup file not found: {backup_file}")
            return False
        
        # Create backup of current DB before restoring
        if os.path.exists(DB_PATH):
            current_backup = f"{DB_PATH}.before_restore"
            shutil.copy2(DB_PATH, current_backup)
            logger.info(f"📦 Created safety backup: {current_backup}")
        
        # Restore from backup
        shutil.copy2(backup_file, DB_PATH)
        logger.info(f"✅ Database restored from: {backup_file}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Restore failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🔄 Starting database backup...")
    success = create_backup()
    
    if success:
        print("✅ Backup completed successfully!")
    else:
        print("❌ Backup failed!")
