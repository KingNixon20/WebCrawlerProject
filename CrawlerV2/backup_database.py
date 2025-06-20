import os
import subprocess
import datetime
import logging
from crawler_config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backup_database.log')
    ]
)
logger = logging.getLogger(__name__)

def create_backup():
    """Create a PostgreSQL database backup using pg_dump."""
    try:
        # Generate timestamped filename in current directory
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M')
        backup_file = os.path.join(os.getcwd(), f'backup_{timestamp}.sql')
        
        # Set environment variable for PostgreSQL password
        os.environ['PGPASSWORD'] = DB_PASS
        
        # Construct pg_dump command
        pg_dump_cmd = [
            'pg_dump',
            '-h', DB_HOST,
            '-p', str(DB_PORT),
            '-U', DB_USER,
            '-d', DB_NAME,
            '-F', 'p',  # Plain SQL format
            '-f', backup_file
        ]
        
        logger.info(f"Starting database backup to {backup_file}")
        
        # Run pg_dump
        result = subprocess.run(
            pg_dump_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            logger.info(f"Backup successfully created at {backup_file}")
            file_size = os.path.getsize(backup_file) / (1024 * 1024)  # Size in MB
            logger.info(f"Backup file size: {file_size:.2f} MB")
        else:
            logger.error(f"Backup failed: {result.stderr}")
            raise Exception(f"pg_dump failed: {result.stderr}")
        
        return backup_file
    
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise
    finally:
        # Clear PGPASSWORD from environment
        os.environ.pop('PGPASSWORD', None)

if __name__ == '__main__':
    try:
        backup_file = create_backup()
        print(f"Backup completed: {backup_file}")
    except Exception as e:
        print(f"Backup failed: {e}")