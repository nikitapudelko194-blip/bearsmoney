"""Database backup automation script."""
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Backup settings
BACKUP_DIR = Path("backups")
DB_FILE = Path("bearsmoney.db")
MAX_BACKUPS = 7  # Keep last 7 backups


def create_backup() -> bool:
    """
    Create database backup.
    """
    try:
        # Create backup directory if not exists
        BACKUP_DIR.mkdir(exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"bearsmoney_backup_{timestamp}.db"
        
        # Copy database file
        if DB_FILE.exists():
            shutil.copy2(DB_FILE, backup_file)
            logger.info(f"✅ Backup created: {backup_file}")
            
            # Cleanup old backups
            cleanup_old_backups()
            
            return True
        else:
            logger.error(f"❌ Database file not found: {DB_FILE}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Error creating backup: {e}", exc_info=True)
        return False


def cleanup_old_backups():
    """
    Remove old backups, keeping only MAX_BACKUPS most recent.
    """
    try:
        # Get all backup files
        backups = sorted(
            BACKUP_DIR.glob("bearsmoney_backup_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        # Remove old backups
        for backup in backups[MAX_BACKUPS:]:
            backup.unlink()
            logger.info(f"🗑️ Removed old backup: {backup}")
    
    except Exception as e:
        logger.error(f"❌ Error cleaning up backups: {e}", exc_info=True)


def restore_backup(backup_file: Path) -> bool:
    """
    Restore database from backup.
    """
    try:
        if not backup_file.exists():
            logger.error(f"❌ Backup file not found: {backup_file}")
            return False
        
        # Create backup of current DB before restore
        if DB_FILE.exists():
            current_backup = BACKUP_DIR / f"bearsmoney_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(DB_FILE, current_backup)
            logger.info(f"💾 Created backup of current DB: {current_backup}")
        
        # Restore from backup
        shutil.copy2(backup_file, DB_FILE)
        logger.info(f"✅ Database restored from: {backup_file}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Error restoring backup: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create backup
    success = create_backup()
    
    if success:
        print("✅ Backup completed successfully!")
    else:
        print("❌ Backup failed!")
