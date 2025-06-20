import os
import sys
import sqlite3
from flask import Flask, jsonify, request
from flask_cors import CORS
import jwt
import datetime
from functools import wraps
import traceback
from crawler_config import JWT_SECRET

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

# SQLite database file
DB_FILE = os.path.join(current_dir, 'crawler.db')

# In-memory storage for blacklisted tokens
blacklisted_tokens = set()

def get_db_connection():
    """Return a new SQLite connection."""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row  # For named tuple-like access
        return conn
    except sqlite3.Error as e:
        print(f"[!] Database connection error: {e}")
        raise

def init_crawler_tables():
    """Initialize crawler tables in SQLite."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create webpages table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS webpages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                summary TEXT,
                tags TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create crawl_queue table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crawl_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                last_crawled DATETIME
            )
        """)
        
        # Create users table for godmode authentication
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                privilege_level TEXT DEFAULT 'user'
            )
        """)
        
        # Create indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_crawl_queue_status ON crawl_queue(status)")
        
        # Initialize seed URLs
        try:
            with open('seeds.txt', 'r') as f:
                seed_urls = [url.strip() for url in f.readlines() if url.strip()]
            for url in seed_urls:
                cur.execute("""
                    INSERT OR IGNORE INTO crawl_queue (url)
                    VALUES (?)
                """, (url,))
        except FileNotFoundError:
            print("[!] seeds.txt not found, skipping seed URL initialization")
        
        conn.commit()
        cur.close()
        conn.close()
        print("[*] Crawler tables initialized successfully")
    except Exception as e:
        print(f"[!] Error initializing crawler tables: {e}")
        raise

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
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, username, email, privilege_level FROM users WHERE id = ?", (data['user_id'],))
            current_user = cur.fetchone()
            cur.close()
            conn.close()
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid'}), 401
        except Exception as e:
            print(f"[!] Token verification error: {e}")
            return jsonify({'message': 'Token verification failed'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

def godmode_required(f):
    """Decorator to require godmode privileges."""
    @wraps(f)
    @token_required
    def decorated(current_user, *args, **kwargs):
        if current_user['privilege_level'] != 'godmode':
            return jsonify({'message': 'Godmode privileges required'}), 403
        return f(current_user, *args, **kwargs)
    return decorated

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"[!] Internal server error: {error}")
    print(f"[!] Traceback: {traceback.format_exc()}")
    return jsonify({'message': 'Internal server error'}), 500

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return jsonify({
            'status': 'healthy',
            'message': 'Crawler API is running and database is accessible',
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': f'Database connection failed: {str(e)}',
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 500

# Crawler routes
@app.route('/api/crawler/urls', methods=['GET', 'OPTIONS'])
def get_urls_to_crawl():
    """Get URLs for worker nodes to crawl."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT url FROM crawl_queue 
            WHERE status = 'pending' 
            ORDER BY added_at ASC 
            LIMIT 10
        """)
        urls = [row['url'] for row in cur.fetchall()]
        if urls:
            # SQLite doesn't support IN with parameterized tuples directly, so use a workaround
            placeholders = ','.join(['?'] * len(urls))
            cur.execute(f"""
                UPDATE crawl_queue 
                SET status = 'processing' 
                WHERE url IN ({placeholders})
            """, urls)
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'urls': urls}), 200
    except Exception as e:
        print(f"[!] Error fetching URLs: {e}")
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/crawler/submit', methods=['POST', 'OPTIONS'])
def submit_crawl_data():
    """Submit crawl data from worker nodes."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json()
        url = data.get('url')
        title = data.get('title')
        summary = data.get('summary')
        tags = data.get('tags')
        new_urls = data.get('new_urls', [])
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO webpages (url, title, summary, tags, timestamp)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (url, title, summary, tags))
        cur.execute("""
            UPDATE crawl_queue 
            SET status = 'completed', 
                last_crawled = CURRENT_TIMESTAMP 
            WHERE url = ?
        """, (url,))
        for new_url in new_urls:
            cur.execute("""
                INSERT OR IGNORE INTO crawl_queue (url)
                VALUES (?)
            """, (new_url,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Data saved successfully'}), 200
    except Exception as e:
        print(f"[!] Error submitting crawl data: {e}")
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/crawler/status', methods=['GET', 'OPTIONS'])
def get_crawler_status():
    """Get current crawler status and statistics."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM crawl_queue WHERE status = 'pending'")
        pending = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM crawl_queue WHERE status = 'processing'")
        processing = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM webpages")
        crawled = cur.fetchone()[0]
        cur.close()
        conn.close()
        return jsonify({
            'pending_urls': pending,
            'processing_urls': processing,
            'crawled_urls': crawled,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        print(f"[!] Error getting crawler status: {e}")
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/crawler/resume', methods=['POST', 'OPTIONS'])
@godmode_required
def resume_crawler(current_user):
    """Resume crawling from last 10 URLs."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT url FROM webpages 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        recent_urls = [row['url'] for row in cur.fetchall()]
        for url in recent_urls:
            cur.execute("""
                INSERT OR IGNORE INTO crawl_queue (url)
                VALUES (?)
            """, (url,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Crawler resumed with last 10 URLs', 'urls': recent_urls}), 200
    except Exception as e:
        print(f"[!] Error resuming crawler: {e}")
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/crawler/reset', methods=['POST', 'OPTIONS'])
@godmode_required
def reset_crawler(current_user):
    """Reset crawler with seed URLs."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM crawl_queue")
        try:
            with open('seeds.txt', 'r') as f:
                seed_urls = [url.strip() for url in f.readlines() if url.strip()]
        except FileNotFoundError:
            cur.close()
            conn.close()
            return jsonify({'error': 'seeds.txt not found'}), 400
        for url in seed_urls:
            cur.execute("""
                INSERT OR IGNORE INTO crawl_queue (url)
                VALUES (?)
            """, (url,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Crawler reset with seed URLs'}), 200
    except Exception as e:
        print(f"[!] Error resetting crawler: {e}")
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_crawler_tables()
    app.run(host='0.0.0.0', port=5001, debug=True)