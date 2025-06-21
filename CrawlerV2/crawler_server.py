from flask import Flask, jsonify, request
from functools import wraps
import jwt
import logging
from logging.handlers import RotatingFileHandler
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
import time
import threading
import queue
from crawler_config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS, JWT_SECRET

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s',
    handlers=[
        RotatingFileHandler('crawler_server.log', maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global state
blacklisted_domains = set()
db_pool = queue.Queue()
dedupe_enabled = True
dedupe_interval = 10 * 60  # 10 minutes in seconds
last_dedupe_time = 0
current_domain = None

def get_db_config():
    """Return database configuration from crawler_config."""
    return {
        'dbname': DB_NAME,
        'user': DB_USER,
        'password': DB_PASS,
        'host': DB_HOST,
        'port': DB_PORT
    }

def get_pg_connection():
    """Get a PostgreSQL connection from the pool or create a new one."""
    try:
        conn = db_pool.get(block=False)
        if conn.closed:
            conn = psycopg2.connect(**get_db_config())
        return conn
    except queue.Empty:
        return psycopg2.connect(**get_db_config())

def release_pg_connection(conn):
    """Release a connection back to the pool."""
    if not conn.closed:
        db_pool.put(conn)

def init_db():
    """Initialize database tables."""
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crawl_queue (
                id SERIAL PRIMARY KEY,
                url TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'pending',
                last_crawled TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS webpages (
                id SERIAL PRIMARY KEY,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                summary TEXT,
                tags TEXT,
                domain TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
    finally:
        cur.close()
        release_pg_connection(conn)

def godmode_required(f):
    """Decorator to require godmode JWT token."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            logger.warning("Authorization header missing")
            return jsonify({'error': 'Authorization header required'}), 401
        try:
            token_type, token = auth_header.split()
            if token_type.lower() != 'bearer':
                logger.warning("Invalid token type")
                return jsonify({'error': 'Bearer token required'}), 401
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            if not payload.get('godmode'):
                logger.warning("Godmode access required")
                return jsonify({'error': 'Godmode access required'}), 403
            return f(payload, *args, **kwargs)
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid JWT token: {e}")
            return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({'error': str(e)}), 500
    return decorated_function

def deduplicate_urls():
    """Remove duplicate URLs from crawl_queue."""
    global last_dedupe_time
    while True:
        if dedupe_enabled and (time.time() - last_dedupe_time) >= dedupe_interval:
            conn = get_pg_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    WITH duplicates AS (
                        SELECT id, url, ROW_NUMBER() OVER (PARTITION BY url ORDER BY id) AS rn
                        FROM crawl_queue
                        WHERE status = 'pending'
                    )
                    DELETE FROM crawl_queue
                    WHERE id IN (SELECT id FROM duplicates WHERE rn > 1)
                """)
                deleted_count = cur.rowcount
                if deleted_count > 0:
                    logger.info(f"Deduplicated {deleted_count} URLs")
                conn.commit()
                last_dedupe_time = time.time()
            except Exception as e:
                logger.error(f"Deduplication error: {e}")
            finally:
                cur.close()
                release_pg_connection(conn)
        time.sleep(60)

@app.route('/api/crawler/status', methods=['GET', 'OPTIONS'])
@godmode_required
def get_status(current_user):
    """Get crawler status."""
    if request.method == 'OPTIONS':
        return '', 200
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM crawl_queue WHERE status = 'pending'")
        pending_urls = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM crawl_queue WHERE status = 'processing'")
        processing_urls = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM crawl_queue WHERE status = 'completed'")
        crawled_urls = cur.fetchone()[0]
        logger.info(f"Status: {pending_urls} pending, {processing_urls} processing, {crawled_urls} crawled")
        return jsonify({
            'pending_urls': pending_urls,
            'processing_urls': processing_urls,
            'crawled_urls': crawled_urls,
            'current_domain': current_domain
        }), 200
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        release_pg_connection(conn)

@app.route('/api/crawler/config', methods=['POST', 'OPTIONS'])
@godmode_required
def update_config(current_user):
    """Update crawler configuration."""
    if request.method == 'OPTIONS':
        return '', 200
    global dedupe_enabled, dedupe_interval
    data = request.get_json()
    dedupe_enabled = data.get('dedupe_enabled', dedupe_enabled)
    dedupe_interval = data.get('dedupe_interval', dedupe_interval)
    logger.info(f"Updated config: dedupe_enabled={dedupe_enabled}, dedupe_interval={dedupe_interval}")
    return jsonify({'message': 'Configuration updated'}), 200

@app.route('/api/crawler/urls', methods=['GET', 'POST', 'OPTIONS'])
@godmode_required
def manage_urls(current_user):
    """Fetch URLs to crawl or reset the queue."""
    global current_domain  # Declare global at the start
    if request.method == 'OPTIONS':
        return '', 200
    conn = get_pg_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if request.method == 'POST' and request.get_json().get('reset'):
            current_domain = None
            cur.execute("UPDATE crawl_queue SET status = 'pending' WHERE status = 'processing'")
            cur.execute("DELETE FROM crawl_queue WHERE status = 'completed'")
            conn.commit()
            logger.info("Reset crawl queue")
            return jsonify({'message': 'Queue reset'}), 200
        else:
            blacklist_patterns = [f'%://{domain}%' for domain in blacklisted_domains]
            query = """
                SELECT url 
                FROM crawl_queue 
                WHERE status = 'pending'
            """
            if blacklist_patterns:
                query += " AND url NOT LIKE ALL (%s)"
                cur.execute(query, (blacklist_patterns,))
            else:
                cur.execute(query)
            urls = [row['url'] for row in cur.fetchall()]
            if not urls:
                logger.info("No pending URLs available")
                return jsonify({'urls': []}), 200
            domain = urlparse(urls[0]).netloc
            current_domain = domain
            filtered_urls = [url for url in urls if urlparse(url).netloc == domain]
            cur.execute("""
                UPDATE crawl_queue 
                SET status = 'processing' 
                WHERE url = ANY(%s)
            """, (filtered_urls,))
            conn.commit()
            logger.info(f"Returning {len(filtered_urls)} URLs for domain {domain}")
            return jsonify({'urls': filtered_urls}), 200
    except Exception as e:
        logger.error(f"Error managing URLs: {e}")
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
        domain = urlparse(url).netloc
        new_urls = data.get('new_urls', [])
        tag_count = len(tags.split(',')) if tags else 0
        if tag_count < 20:
            logger.error(f"URL {url} has only {tag_count} tags; rejecting")
            return jsonify({'message': f'Insufficient tags ({tag_count} < 20)'}), 400
        if domain in blacklisted_domains:
            logger.info(f"Rejected submission for {url}; domain {domain} is blacklisted")
            return jsonify({'message': f'Domain {domain} is blacklisted'}), 400
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO webpages (url, title, summary, tags, domain)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (url) DO UPDATE 
            SET title = EXCLUDED.title,
                summary = EXCLUDED.summary,
                tags = EXCLUDED.tags,
                timestamp = CURRENT_TIMESTAMP,
                domain = EXCLUDED.domain
            RETURNING id
        """, (url, title, summary, tags, domain))
        webpage_id = cur.fetchone()[0]
        logger.info(f"{'Updated' if cur.rowcount else 'Inserted'} webpage record for {url} (id: {webpage_id})")
        cur.execute("""
            UPDATE crawl_queue 
            SET status = 'completed', 
                last_crawled = CURRENT_TIMESTAMP 
            WHERE url = %s
        """, (url,))
        for new_url in new_urls:
            new_domain = urlparse(new_url).netloc
            if new_domain not in blacklisted_domains:
                cur.execute("""
                    INSERT INTO crawl_queue (url)
                    VALUES (%s)
                    ON CONFLICT (url) DO NOTHING
                """, (new_url,))
                cur.execute("""
                    INSERT INTO webpages (url, domain)
                    VALUES (%s, %s)
                    ON CONFLICT (url) DO NOTHING
                """, (new_url, new_domain))
            else:
                logger.info(f"Skipped adding {new_url} to crawl_queue; domain {new_domain} is blacklisted")
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

@app.route('/api/crawler/skip_domain', methods=['POST', 'OPTIONS'])
@godmode_required
def skip_domain(current_user):
    """Skip the current domain being crawled."""
    if request.method == 'OPTIONS':
        return '', 200
    global current_domain
    if not current_domain:
        logger.info("No current domain to skip")
        return jsonify({'message': 'No current domain'}), 400
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE crawl_queue 
            SET status = 'completed' 
            WHERE url LIKE %s AND status = 'processing'
        """, (f'%://{current_domain}%',))
        skipped_count = cur.rowcount
        conn.commit()
        logger.info(f"Skipped {skipped_count} URLs for domain {current_domain}")
        current_domain = None
        return jsonify({'message': f'Skipped domain {current_domain}'}), 200
    except Exception as e:
        logger.error(f"Error skipping domain {current_domain}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        release_pg_connection(conn)

@app.route('/api/crawler/blacklist', methods=['GET', 'OPTIONS'])
@godmode_required
def get_blacklist(current_user):
    """Get the list of blacklisted domains."""
    if request.method == 'OPTIONS':
        return '', 200
    logger.info("Returning blacklisted domains")
    return jsonify({'domains': list(blacklisted_domains)}), 200

@app.route('/api/crawler/blacklist_domain', methods=['GET', 'POST', 'OPTIONS'])
@godmode_required
def blacklist_domain(current_user):
    """Add a domain to the blacklist or check if a domain is blacklisted."""
    if request.method == 'OPTIONS':
        return '', 200
    if request.method == 'GET':
        domain = request.args.get('domain')
        if not domain:
            logger.warning("Domain parameter missing for blacklist check")
            return jsonify({'message': 'Domain is required'}), 400
        is_blacklisted = domain in blacklisted_domains
        logger.info(f"Returning blacklist status for domain: {domain} - {is_blacklisted}")
        return jsonify({'blacklisted': is_blacklisted}), 200
    data = request.get_json()
    domain = data.get('domain')
    if not domain:
        logger.warning("Domain is required for blacklisting")
        return jsonify({'message': 'Domain is required'}), 400
    conn = get_pg_connection()
    try:
        blacklisted_domains.add(domain)
        cur = conn.cursor()
        cur.execute("""
            UPDATE crawl_queue 
            SET status = 'blacklisted' 
            WHERE url LIKE %s
        """, (f'%://{domain}%',))
        updated_rows = cur.rowcount
        cur.execute("""
            DELETE FROM crawl_queue 
            WHERE url LIKE %s
        """, (f'%://{domain}%',))
        deleted_rows = cur.rowcount
        cur.execute("""
            DELETE FROM webpages 
            WHERE domain = %s
        """, (domain,))
        deleted_webpages = cur.rowcount
        conn.commit()
        logger.info(f"Blacklisted domain {domain}: marked {updated_rows} URLs, deleted {deleted_rows} from crawl_queue, {deleted_webpages} from webpages")
        return jsonify({'message': f'Domain {domain} blacklisted'}), 200
    except Exception as e:
        logger.error(f"Error blacklisting domain {domain}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        release_pg_connection(conn)

@app.route('/api/crawler/unblacklist_domain', methods=['POST', 'OPTIONS'])
@godmode_required
def unblacklist_domain(current_user):
    """Remove a domain from the blacklist."""
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json()
    domain = data.get('domain')
    if not domain:
        logger.warning("Domain is required for unblacklisting")
        return jsonify({'message': 'Domain is required'}), 400
    if domain in blacklisted_domains:
        blacklisted_domains.remove(domain)
        logger.info(f"Unblacklisted domain {domain}")
        return jsonify({'message': f'Domain {domain} unblacklisted'}), 200
    logger.info(f"Domain {domain} not in blacklist")
    return jsonify({'message': f'Domain {domain} not in blacklist'}), 200

@app.route('/api/crawler/clear_blacklisted_urls', methods=['POST', 'OPTIONS'])
@godmode_required
def clear_blacklisted_urls(current_user):
    """Clear URLs for a blacklisted domain from crawl_queue."""
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json()
    domain = data.get('domain')
    if not domain:
        logger.warning("Domain is required for clearing blacklisted URLs")
        return jsonify({'message': 'Domain is required'}), 400
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM crawl_queue 
            WHERE url LIKE %s
        """, (f'%://{domain}%',))
        deleted_rows = cur.rowcount
        conn.commit()
        logger.info(f"Deleted {deleted_rows} URLs for domain {domain} from crawl_queue")
        return jsonify({'message': f'Cleared {deleted_rows} URLs for domain {domain}'}), 200
    except Exception as e:
        logger.error(f"Error clearing blacklisted URLs for {domain}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        release_pg_connection(conn)

if __name__ == '__main__':
    init_db()
    threading.Thread(target=deduplicate_urls, daemon=True).start()
    app.run(host='0.0.0.0', port=5001, threaded=True)