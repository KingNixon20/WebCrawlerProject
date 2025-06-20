import os
import sys
import psycopg2
from psycopg2 import extras
from psycopg2.pool import SimpleConnectionPool
from flask import Flask, jsonify, request
from flask_cors import CORS
import jwt
import datetime
from functools import wraps
import traceback
import threading
import time
import logging
from crawler_config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS, JWT_SECRET

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('crawler_server.log')
    ]
)
logger = logging.getLogger(__name__)

# Add parent directory to sys.path
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

app = Flask(__name__)

# CORS configuration
CORS(app, 
     origins=["https://ap.projectkryptos.xyz", "http://localhost:3000", "http://localhost:5173"],
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True)

# JWT Configuration
app.config['JWT_SECRET_KEY'] = JWT_SECRET
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(days=7)

# In-memory storage for blacklisted tokens
blacklisted_tokens = set()

# Database connection pool
db_pool = SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    connect_timeout=10
)

# Deduplication interval (10 minutes in seconds)
DEDUPE_INTERVAL = 600

def get_pg_connection():
    """Return a connection from the pool."""
    try:
        conn = db_pool.getconn()
        return conn
    except psycopg2.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def release_pg_connection(conn):
    """Release connection back to pool."""
    try:
        db_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Error releasing connection: {e}")

def deduplicate_database():
    """Remove duplicate URLs from webpages, keeping the latest row by timestamp."""
    logger.info("Starting periodic deduplication")
    conn = get_pg_connection()
    if not conn:
        logger.error("Skipping deduplication: no database connection")
        return
    
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    WITH duplicates AS (
                        SELECT url, id, timestamp,
                               ROW_NUMBER() OVER (PARTITION BY url ORDER BY timestamp DESC, id DESC) AS rn
                        FROM webpages
                    )
                    DELETE FROM webpages WHERE id IN (
                        SELECT id FROM duplicates WHERE rn > 1
                    )
                """)
                deleted_count = cur.rowcount
                logger.info(f"Deduplicated {deleted_count} rows from webpages")
    except Exception as e:
        logger.error(f"Deduplication error: {e}")
    finally:
        release_pg_connection(conn)
    
    threading.Timer(DEDUPE_INTERVAL, deduplicate_database).start()

def init_crawler_tables():
    """Initialize crawler tables."""
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS webpages (
                id SERIAL PRIMARY KEY,
                url VARCHAR(500) UNIQUE NOT NULL,
                title VARCHAR(255),
                summary TEXT,
                tags TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crawl_queue (
                id SERIAL PRIMARY KEY,
                url VARCHAR(500) UNIQUE NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'pending',
                last_crawled TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_crawl_queue_status ON crawl_queue(status)")
        try:
            with open('seeds.txt', 'r') as f:
                seed_urls = [url.strip() for url in f.readlines() if url.strip()]
            for url in seed_urls:
                cur.execute("""
                    INSERT INTO crawl_queue (url)
                    VALUES (%s)
                    ON CONFLICT (url) DO NOTHING
                """, (url,))
        except FileNotFoundError:
            logger.warning("seeds.txt not found, skipping seed URL initialization")
        conn.commit()
        logger.info("Crawler tables initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing crawler tables: {e}")
        raise
    finally:
        cur.close()
        release_pg_connection(conn)

def token_required(f):
    """Decorator to require JWT token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Access token required'}), 401
        try:
            token = token.split(' ')[1] if token.startswith('Bearer ') else token
            if token in blacklisted_tokens:
                return jsonify({'message': 'Token has been revoked'}), 401
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            conn = get_pg_connection()
            try:
                cur = conn.cursor(cursor_factory=extras.NamedTupleCursor)
                cur.execute("SELECT id, username, email, privilege_level FROM users WHERE id = %s", (data['user_id'],))
                current_user = cur.fetchone()
                cur.close()
                if not current_user:
                    return jsonify({'message': 'User not found'}), 401
            finally:
                release_pg_connection(conn)
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid'}), 401
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return jsonify({'message': 'Token verification failed'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

def godmode_required(f):
    """Decorator to require godmode privileges."""
    @wraps(f)
    @token_required
    def decorated(current_user, *args, **kwargs):
        if current_user.privilege_level != 'godmode':
            return jsonify({'message': 'Godmode privileges required'}), 403
        return f(current_user, *args, **kwargs)
    return decorated

@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    return jsonify({'message': 'Internal server error'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        return jsonify({
            'status': 'healthy',
            'message': 'Crawler API is running and database is accessible',
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': f'Database connection failed: {str(e)}',
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 500
    finally:
        release_pg_connection(conn)

@app.route('/api/crawler/urls', methods=['GET', 'OPTIONS'])
def get_urls_to_crawl():
    """Get URLs for worker nodes to crawl."""
    if request.method == 'OPTIONS':
        return '', 200
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT url FROM crawl_queue 
            WHERE status = 'pending' 
            ORDER BY added_at ASC 
            LIMIT 10
        """)
        urls = [row[0] for row in cur.fetchall()]
        if urls:
            cur.execute("""
                UPDATE crawl_queue 
                SET status = 'processing' 
                WHERE url IN %s
            """, (tuple(urls),))
        else:
            logger.warning("No pending URLs; attempting to reseed")
            try:
                with open('seeds.txt', 'r') as f:
                    seed_urls = [url.strip() for url in f.readlines() if url.strip()]
                for url in seed_urls:
                    cur.execute("""
                        INSERT INTO crawl_queue (url)
                        VALUES (%s)
                        ON CONFLICT (url) DO NOTHING
                    """, (url,))
                conn.commit()
                cur.execute("""
                    SELECT url FROM crawl_queue 
                    WHERE status = 'pending' 
                    ORDER BY added_at ASC 
                    LIMIT 10
                """)
                urls = [row[0] for row in cur.fetchall()]
                if urls:
                    cur.execute("""
                        UPDATE crawl_queue 
                        SET status = 'processing' 
                        WHERE url IN %s
                    """, (tuple(urls),))
            except FileNotFoundError:
                logger.error("seeds.txt not found during reseed")
        conn.commit()
        logger.info(f"Returning {len(urls)} URLs to crawl")
        return jsonify({'urls': urls}), 200
    except Exception as e:
        logger.error(f"Error fetching URLs: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        release_pg_connection(conn)

@app.route('/api/crawler/submit', methods=['POST', 'OPTIONS'])
def submit_crawl_data():
    """Submit crawl data from worker nodes."""
    if request.method == 'OPTIONS':
        return '', 200
    conn = get_pg_connection()
    try:
        data = request.get_json()
        url = data.get('url')
        title = data.get('title')
        summary = data.get('summary')
        tags = data.get('tags')
        new_urls = data.get('new_urls', [])
        tag_count = len(tags.split(',')) if tags else 0
        if tag_count < 20:
            logger.error(f"URL {url} has only {tag_count} tags; rejecting")
            return jsonify({'message': f'Insufficient tags ({tag_count} < 20)'}), 400
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO webpages (url, title, summary, tags)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (url) DO UPDATE 
            SET title = EXCLUDED.title,
                summary = EXCLUDED.summary,
                tags = EXCLUDED.tags,
                timestamp = CURRENT_TIMESTAMP
            RETURNING id
        """, (url, title, summary, tags))
        webpage_id = cur.fetchone()[0]
        logger.info(f"{'Updated' if cur.rowcount else 'Inserted'} webpage record for {url} (id: {webpage_id})")
        cur.execute("""
            UPDATE crawl_queue 
            SET status = 'completed', 
                last_crawled = CURRENT_TIMESTAMP 
            WHERE url = %s
        """, (url,))
        for new_url in new_urls:
            cur.execute("""
                INSERT INTO crawl_queue (url)
                VALUES (%s)
                ON CONFLICT (url) DO NOTHING
            """, (new_url,))
        conn.commit()
        logger.info(f"Processed {url} with {len(new_urls)} new URLs")
        return jsonify({'message': 'Data saved successfully'}), 200
    except Exception as e:
        logger.error(f"Error submitting crawl data: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cur' in locals():
            cur.close()
        release_pg_connection(conn)

@app.route('/api/crawler/status', methods=['GET', 'OPTIONS'])
def get_crawler_status():
    """Get current crawler status and statistics."""
    if request.method == 'OPTIONS':
        return '', 200
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM crawl_queue WHERE status = 'pending'")
        pending = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM crawl_queue WHERE status = 'processing'")
        processing = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM webpages")
        crawled = cur.fetchone()[0]
        cur.close()
        return jsonify({
            'pending_urls': pending,
            'processing_urls': processing,
            'crawled_urls': crawled,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error getting crawler status: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        release_pg_connection(conn)

@app.route('/api/crawler/resume', methods=['POST', 'OPTIONS'])
@godmode_required
def resume_crawler(current_user):
    """Resume crawling from last 10 URLs."""
    if request.method == 'OPTIONS':
        return '', 200
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT url FROM webpages 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        recent_urls = [row[0] for row in cur.fetchall()]
        for url in recent_urls:
            cur.execute("""
                INSERT INTO crawl_queue (url)
                VALUES (%s)
                ON CONFLICT (url) DO NOTHING
            """, (url,))
        conn.commit()
        logger.info(f"Crawler resumed with {len(recent_urls)} URLs")
        return jsonify({'message': 'Crawler resumed with last 10 URLs', 'urls': recent_urls}), 200
    except Exception as e:
        logger.error(f"Error resuming crawler: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        release_pg_connection(conn)

@app.route('/api/crawler/reset', methods=['POST', 'OPTIONS'])
@godmode_required
def reset_crawler(current_user):
    """Reset crawler with seed URLs."""
    if request.method == 'OPTIONS':
        return '', 200
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM crawl_queue")
        try:
            with open('seeds.txt', 'r') as f:
                seed_urls = [url.strip() for url in f.readlines() if url.strip()]
        except FileNotFoundError:
            cur.close()
            return jsonify({'error': 'seeds.txt not found'}), 400
        for url in seed_urls:
            cur.execute("""
                INSERT INTO crawl_queue (url)
                VALUES (%s)
                ON CONFLICT (url) DO NOTHING
            """, (url,))
        conn.commit()
        logger.info("Crawler reset with seed URLs")
        return jsonify({'message': 'Crawler reset with seed URLs'}), 200
    except Exception as e:
        logger.error(f"Error resetting crawler: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        release_pg_connection(conn)

if __name__ == '__main__':
    init_crawler_tables()
    deduplicate_database()
    app.run(host='0.0.0.0', port=5001, debug=False)