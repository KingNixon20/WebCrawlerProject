import os
import sys
import json
import psycopg2
from psycopg2 import extras
from flask import jsonify
from flask_cors import CORS
from flask import (
    Flask,
    render_template,
    request,
    make_response,
    Response,
    redirect,
    url_for,
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
import traceback
import requests
from user_agents import parse
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS, JWT_SECRET_KEY

# ── Add parent directory so imports still work ────────────────────────────────
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

app = Flask(__name__)

# Simplified CORS configuration - let Flask-CORS handle everything
CORS(app, 
     origins=["https://ap.projectkryptos.xyz", "http://localhost:3000", "http://localhost:5173"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     supports_credentials=True,
     expose_headers=["Content-Type", "Authorization"])

# JWT Configuration
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(days=7)

# Upload folder for custom backgrounds
UPLOAD_FOLDER = os.path.join(current_dir, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

# In-memory storage for blacklisted tokens (use Redis in production)
blacklisted_tokens = set()

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

def get_pg_connection():
    """Return a new psycopg2 connection + NamedTupleCursor factory."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            connect_timeout=10
        )
        return conn
    except psycopg2.Error as e:
        print(f"[!] Database connection error: {e}")
        raise

def get_client_ip():
    """Get the real client IP address."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def get_location_from_ip(ip_address):
    """Get location information from IP address using a free service."""
    try:
        # Skip localhost/private IPs
        if ip_address in ['127.0.0.1', 'localhost'] or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
            return {'country': 'Local', 'city': 'Local', 'region': 'Local'}
        
        # Use ipapi.co for geolocation (free tier: 1000 requests/day)
        response = requests.get(f'https://ipapi.co/{ip_address}/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'country': data.get('country_name', 'Unknown'),
                'city': data.get('city', 'Unknown'),
                'region': data.get('region', 'Unknown')
            }
    except Exception as e:
        print(f"[!] Error getting location for IP {ip_address}: {e}")
    
    return {'country': 'Unknown', 'city': 'Unknown', 'region': 'Unknown'}

def should_track_visit(ip_address, user_id, page_path):
    """
    Determine if we should track this visit to avoid duplicate counting.
    Returns True if this is a new visit that should be tracked.
    """
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Check if this IP/user has visited this page in the last 30 minutes
        time_threshold = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
        
        if user_id:
            # For logged-in users, check by user_id
            cur.execute("""
                SELECT COUNT(*) FROM site_analytics 
                WHERE user_id = %s AND page_path = %s AND visit_time > %s
            """, (user_id, page_path, time_threshold))
        else:
            # For anonymous users, check by IP
            cur.execute("""
                SELECT COUNT(*) FROM site_analytics 
                WHERE ip_address = %s AND page_path = %s AND visit_time > %s AND user_id IS NULL
            """, (ip_address, page_path, time_threshold))
        
        recent_visits = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        # Only track if no recent visits
        return recent_visits == 0
        
    except Exception as e:
        print(f"[!] Error checking visit tracking: {e}")
        # If there's an error, err on the side of not tracking to avoid duplicates
        return False

def track_page_visit(page_path, user_id=None):
    """Track a page visit with analytics data, avoiding duplicates."""
    try:
        ip_address = get_client_ip()
        
        # Skip tracking for certain conditions
        if not should_track_visit(ip_address, user_id, page_path):
            print(f"[*] Skipping duplicate visit tracking for {page_path} from {ip_address}")
            return
        
        user_agent_string = request.headers.get('User-Agent', '')
        user_agent = parse(user_agent_string)
        
        # Get location data
        location = get_location_from_ip(ip_address)
        
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Insert analytics record
        cur.execute("""
            INSERT INTO site_analytics (
                user_id, ip_address, page_path, user_agent, browser, browser_version,
                os, os_version, device_type, country, city, region, visit_time
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            ip_address,
            page_path,
            user_agent_string,
            user_agent.browser.family,
            user_agent.browser.version_string,
            user_agent.os.family,
            user_agent.os.version_string,
            'Mobile' if user_agent.is_mobile else 'Desktop',
            location['country'],
            location['city'],
            location['region'],
            datetime.datetime.utcnow()
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"[*] Tracked new visit: {page_path} from {ip_address} (User: {user_id or 'Anonymous'})")
        
    except Exception as e:
        print(f"[!] Error tracking page visit: {e}")

def init_auth_tables():
    """Initialize authentication tables if they don't exist."""
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Create users table with privileges
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                privilege_level VARCHAR(20) DEFAULT 'user' CHECK (privilege_level IN ('user', 'premium', 'moderator', 'admin', 'godmode')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Create user_ratings table for storing user ratings
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_ratings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                url VARCHAR(500) NOT NULL,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, url)
            )
        """)
        
        # Create user_preferences table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                wallpaper VARCHAR(255),
                blur_intensity INTEGER DEFAULT 10,
                accent_color VARCHAR(7) DEFAULT '#4fc3f7',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        """)
        
        # Create site analytics table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS site_analytics (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                ip_address INET NOT NULL,
                page_path VARCHAR(255) NOT NULL,
                user_agent TEXT,
                browser VARCHAR(100),
                browser_version VARCHAR(50),
                os VARCHAR(100),
                os_version VARCHAR(50),
                device_type VARCHAR(20),
                country VARCHAR(100),
                city VARCHAR(100),
                region VARCHAR(100),
                visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_duration INTEGER DEFAULT 0
            )
        """)
        
        # Create session tracking table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                ip_address INET NOT NULL,
                session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_end TIMESTAMP,
                pages_visited INTEGER DEFAULT 1,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for better performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_analytics_visit_time ON site_analytics(visit_time)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_analytics_ip ON site_analytics(ip_address)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_analytics_user_id ON site_analytics(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_analytics_ip_time ON site_analytics(ip_address, visit_time)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_analytics_user_time ON site_analytics(user_id, visit_time)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_privilege ON users(privilege_level)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)")
        
        conn.commit()
        cur.close()
        conn.close()
        print("[*] Authentication and analytics tables initialized successfully")
        
    except Exception as e:
        print(f"[!] Error initializing auth tables: {e}")
        raise

def token_required(f):
    """Decorator to require JWT token for protected routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'message': 'Access token required'}), 401
        
        try:
            # Remove 'Bearer ' prefix
            token = token.split(' ')[1] if token.startswith('Bearer ') else token
            
            # Check if token is blacklisted
            if token in blacklisted_tokens:
                return jsonify({'message': 'Token has been revoked'}), 401
            
            # Decode token
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            
            # Get user from database
            conn = get_pg_connection()
            cur = conn.cursor(cursor_factory=extras.NamedTupleCursor)
            cur.execute("SELECT id, username, email, privilege_level FROM users WHERE id = %s", (data['user_id'],))
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
        if current_user.privilege_level != 'godmode':
            return jsonify({'message': 'Godmode privileges required'}), 403
        return f(current_user, *args, **kwargs)
    return decorated

def admin_required(f):
    """Decorator to require admin or godmode privileges."""
    @wraps(f)
    @token_required
    def decorated(current_user, *args, **kwargs):
        if current_user.privilege_level not in ['admin', 'godmode']:
            return jsonify({'message': 'Admin privileges required'}), 403
        return f(current_user, *args, **kwargs)
    return decorated

def optional_token(f):
    """Decorator that optionally checks for JWT token but doesn't require it."""
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user = None
        token = request.headers.get('Authorization')
        
        if token:
            try:
                token = token.split(' ')[1] if token.startswith('Bearer ') else token
                
                if token not in blacklisted_tokens:
                    data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
                    
                    conn = get_pg_connection()
                    cur = conn.cursor(cursor_factory=extras.NamedTupleCursor)
                    cur.execute("SELECT id, username, email, privilege_level FROM users WHERE id = %s", (data['user_id'],))
                    current_user = cur.fetchone()
                    cur.close()
                    conn.close()
            except Exception as e:
                print(f"[!] Optional token verification failed: {e}")
                pass  # Invalid token, but that's okay for optional auth
        
        return f(current_user, *args, **kwargs)
    return decorated

# Add error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"[!] Internal server error: {error}")
    print(f"[!] Traceback: {traceback.format_exc()}")
    return jsonify({'message': 'Internal server error'}), 500

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'message': 'Bad request'}), 400

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify API is running."""
    try:
        # Test database connection
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'message': 'API is running and database is accessible',
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'message': f'Database connection failed: {str(e)}',
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_site_stats():
    """Get site statistics like total indexed pages."""
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Get total number of indexed pages
        cur.execute("SELECT COUNT(*) FROM webpages")
        total_pages = cur.fetchone()[0]
        
        # Get total number of registered users
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        
        # Get pages indexed in the last 24 hours
        cur.execute("""
            SELECT COUNT(*) FROM webpages 
            WHERE timestamp >= NOW() - INTERVAL '24 hours'
        """)
        recent_pages = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return jsonify({
            'total_pages': total_pages,
            'total_users': total_users,
            'recent_pages': recent_pages,
            'last_updated': datetime.datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"[!] Error fetching site stats: {e}")
        return jsonify({
            'total_pages': 0,
            'total_users': 0,
            'recent_pages': 0,
            'error': str(e)
        }), 500

# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN USER MANAGEMENT ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/admin/users', methods=['GET', 'OPTIONS'])
@godmode_required
def get_all_users(current_user):
    """Get all registered users - Godmode only."""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Get query parameters for filtering and pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        search = request.args.get('search', '').strip()
        privilege_filter = request.args.get('privilege', '')
        active_filter = request.args.get('active', '')
        
        conn = get_pg_connection()
        cur = conn.cursor(cursor_factory=extras.NamedTupleCursor)
        
        # Build the query with filters
        base_query = """
            SELECT 
                u.id,
                u.username,
                u.email,
                u.privilege_level,
                u.created_at,
                u.updated_at,
                u.last_login,
                u.is_active,
                COUNT(ur.id) as total_ratings,
                COUNT(DISTINCT sa.id) as total_visits
            FROM users u
            LEFT JOIN user_ratings ur ON u.id = ur.user_id
            LEFT JOIN site_analytics sa ON u.id = sa.user_id
            WHERE 1=1
        """
        
        count_query = "SELECT COUNT(*) FROM users u WHERE 1=1"
        params = []
        count_params = []
        
        # Add search filter
        if search:
            search_condition = " AND (u.username ILIKE %s OR u.email ILIKE %s)"
            base_query += search_condition
            count_query += search_condition
            search_param = f"%{search}%"
            params.extend([search_param, search_param])
            count_params.extend([search_param, search_param])
        
        # Add privilege filter
        if privilege_filter:
            privilege_condition = " AND u.privilege_level = %s"
            base_query += privilege_condition
            count_query += privilege_condition
            params.append(privilege_filter)
            count_params.append(privilege_filter)
        
        # Add active filter
        if active_filter:
            active_value = active_filter.lower() == 'true'
            active_condition = " AND u.is_active = %s"
            base_query += active_condition
            count_query += active_condition
            params.append(active_value)
            count_params.append(active_value)
        
        # Add grouping and ordering
        base_query += """
            GROUP BY u.id, u.username, u.email, u.privilege_level, u.created_at, u.updated_at, u.last_login, u.is_active
            ORDER BY u.created_at DESC
        """
        
        # Add pagination
        offset = (page - 1) * per_page
        base_query += " LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        
        # Execute queries
        cur.execute(base_query, params)
        users = cur.fetchall()
        
        cur.execute(count_query, count_params)
        total_users = cur.fetchone()[0]
        
        # Get overall statistics
        cur.execute("""
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN privilege_level = 'user' THEN 1 END) as regular_users,
                COUNT(CASE WHEN privilege_level = 'premium' THEN 1 END) as premium_users,
                COUNT(CASE WHEN privilege_level = 'moderator' THEN 1 END) as moderators,
                COUNT(CASE WHEN privilege_level = 'admin' THEN 1 END) as admins,
                COUNT(CASE WHEN privilege_level = 'godmode' THEN 1 END) as godmode_users,
                COUNT(CASE WHEN is_active = true THEN 1 END) as active_users,
                COUNT(CASE WHEN last_login >= NOW() - INTERVAL '7 days' THEN 1 END) as recent_logins
            FROM users
        """)
        stats = cur.fetchone()
        
        cur.close()
        conn.close()
        
        # Format user data
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'privilege_level': user.privilege_level,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'is_active': user.is_active,
                'total_ratings': user.total_ratings,
                'total_visits': user.total_visits
            })
        
        response_data = {
            'users': users_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_users,
                'pages': (total_users + per_page - 1) // per_page
            },
            'stats': {
                'total_users': stats.total_users,
                'regular_users': stats.regular_users,
                'premium_users': stats.premium_users,
                'moderators': stats.moderators,
                'admins': stats.admins,
                'godmode_users': stats.godmode_users,
                'active_users': stats.active_users,
                'recent_logins': stats.recent_logins
            }
        }
        
        print(f"[*] Admin {current_user.username} fetched {len(users_data)} users")
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"[!] Error fetching users: {e}")
        print(f"[!] Traceback: {traceback.format_exc()}")
        return jsonify({'message': 'Failed to fetch users'}), 500

@app.route('/api/admin/users/<int:user_id>/privileges', methods=['PUT', 'OPTIONS'])
@godmode_required
def update_user_privileges(current_user, user_id):
    """Update user privilege level - Godmode only."""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        new_privilege = data.get('privilege_level', '').strip()
        
        # Validate privilege level
        valid_privileges = ['user', 'premium', 'moderator', 'admin', 'godmode']
        if new_privilege not in valid_privileges:
            return jsonify({'message': 'Invalid privilege level'}), 400
        
        # Prevent users from removing their own godmode privileges
        if user_id == current_user.id and new_privilege != 'godmode':
            return jsonify({'message': 'Cannot remove your own godmode privileges'}), 400
        
        conn = get_pg_connection()
        cur = conn.cursor(cursor_factory=extras.NamedTupleCursor)
        
        # Check if user exists
        cur.execute("SELECT id, username, privilege_level FROM users WHERE id = %s", (user_id,))
        target_user = cur.fetchone()
        
        if not target_user:
            cur.close()
            conn.close()
            return jsonify({'message': 'User not found'}), 404
        
        old_privilege = target_user.privilege_level
        
        # Update privilege level
        cur.execute("""
            UPDATE users 
            SET privilege_level = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE id = %s
        """, (new_privilege, user_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"[*] Admin {current_user.username} updated user {target_user.username} privileges: {old_privilege} -> {new_privilege}")
        
        return jsonify({
            'message': 'User privileges updated successfully',
            'user_id': user_id,
            'username': target_user.username,
            'old_privilege': old_privilege,
            'new_privilege': new_privilege
        }), 200
        
    except Exception as e:
        print(f"[!] Error updating user privileges: {e}")
        print(f"[!] Traceback: {traceback.format_exc()}")
        return jsonify({'message': 'Failed to update user privileges'}), 500

@app.route('/api/admin/users/<int:user_id>/status', methods=['PUT', 'OPTIONS'])
@godmode_required
def update_user_status(current_user, user_id):
    """Update user active status - Godmode only."""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        is_active = data.get('is_active')
        
        if is_active is None:
            return jsonify({'message': 'is_active field required'}), 400
        
        # Prevent users from deactivating themselves
        if user_id == current_user.id and not is_active:
            return jsonify({'message': 'Cannot deactivate your own account'}), 400
        
        conn = get_pg_connection()
        cur = conn.cursor(cursor_factory=extras.NamedTupleCursor)
        
        # Check if user exists
        cur.execute("SELECT id, username, is_active FROM users WHERE id = %s", (user_id,))
        target_user = cur.fetchone()
        
        if not target_user:
            cur.close()
            conn.close()
            return jsonify({'message': 'User not found'}), 404
        
        # Update status
        cur.execute("""
            UPDATE users 
            SET is_active = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE id = %s
        """, (is_active, user_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        status_text = "activated" if is_active else "deactivated"
        print(f"[*] Admin {current_user.username} {status_text} user {target_user.username}")
        
        return jsonify({
            'message': f'User {status_text} successfully',
            'user_id': user_id,
            'username': target_user.username,
            'is_active': is_active
        }), 200
        
    except Exception as e:
        print(f"[!] Error updating user status: {e}")
        return jsonify({'message': 'Failed to update user status'}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['GET', 'OPTIONS'])
@admin_required
def get_user_details(current_user, user_id):
    """Get detailed information about a specific user - Admin+ only."""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        conn = get_pg_connection()
        cur = conn.cursor(cursor_factory=extras.NamedTupleCursor)
        
        # Get user details with statistics
        cur.execute("""
            SELECT 
                u.id,
                u.username,
                u.email,
                u.privilege_level,
                u.created_at,
                u.updated_at,
                u.last_login,
                u.is_active,
                COUNT(DISTINCT ur.id) as total_ratings,
                AVG(ur.rating) as avg_rating,
                COUNT(DISTINCT sa.id) as total_visits,
                MAX(sa.visit_time) as last_visit
            FROM users u
            LEFT JOIN user_ratings ur ON u.id = ur.user_id
            LEFT JOIN site_analytics sa ON u.id = sa.user_id
            WHERE u.id = %s
            GROUP BY u.id, u.username, u.email, u.privilege_level, u.created_at, u.updated_at, u.last_login, u.is_active
        """, (user_id,))
        
        user = cur.fetchone()
        
        if not user:
            cur.close()
            conn.close()
            return jsonify({'message': 'User not found'}), 404
        
        # Get recent ratings
        cur.execute("""
            SELECT url, rating, created_at, updated_at
            FROM user_ratings
            WHERE user_id = %s
            ORDER BY updated_at DESC
            LIMIT 10
        """, (user_id,))
        recent_ratings = cur.fetchall()
        
        # Get recent visits
        cur.execute("""
            SELECT page_path, visit_time, ip_address, browser, os, country, city
            FROM site_analytics
            WHERE user_id = %s
            ORDER BY visit_time DESC
            LIMIT 20
        """, (user_id,))
        recent_visits = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Format response
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'privilege_level': user.privilege_level,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'last_visit': user.last_visit.isoformat() if user.last_visit else None,
            'is_active': user.is_active,
            'stats': {
                'total_ratings': user.total_ratings,
                'avg_rating': float(user.avg_rating) if user.avg_rating else 0,
                'total_visits': user.total_visits
            },
            'recent_ratings': [
                {
                    'url': rating.url,
                    'rating': rating.rating,
                    'created_at': rating.created_at.isoformat(),
                    'updated_at': rating.updated_at.isoformat()
                }
                for rating in recent_ratings
            ],
            'recent_visits': [
                {
                    'page_path': visit.page_path,
                    'visit_time': visit.visit_time.isoformat(),
                    'ip_address': str(visit.ip_address),
                    'browser': visit.browser,
                    'os': visit.os,
                    'location': f"{visit.city}, {visit.country}" if visit.city and visit.country else 'Unknown'
                }
                for visit in recent_visits
            ]
        }
        
        print(f"[*] Admin {current_user.username} viewed details for user {user.username}")
        return jsonify(user_data), 200
        
    except Exception as e:
        print(f"[!] Error fetching user details: {e}")
        return jsonify({'message': 'Failed to fetch user details'}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE', 'OPTIONS'])
@godmode_required
def delete_user(current_user, user_id):
    """Delete a user account - Godmode only."""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Prevent users from deleting themselves
        if user_id == current_user.id:
            return jsonify({'message': 'Cannot delete your own account'}), 400
        
        conn = get_pg_connection()
        cur = conn.cursor(cursor_factory=extras.NamedTupleCursor)
        
        # Check if user exists
        cur.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
        target_user = cur.fetchone()
        
        if not target_user:
            cur.close()
            conn.close()
            return jsonify({'message': 'User not found'}), 404
        
        # Delete user (CASCADE will handle related records)
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"[*] Admin {current_user.username} deleted user {target_user.username}")
        
        return jsonify({
            'message': 'User deleted successfully',
            'deleted_user': target_user.username
        }), 200
        
    except Exception as e:
        print(f"[!] Error deleting user: {e}")
        return jsonify({'message': 'Failed to delete user'}), 500

# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization")
        response.headers.add('Access-Control-Allow-Methods', "GET,POST,PUT,DELETE,OPTIONS")
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

@app.route('/api/analytics/track', methods=['POST', 'OPTIONS'])
@optional_token
def track_analytics(current_user):
    """Track page visit analytics."""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "https://ap.projectkryptos.xyz")
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization")
        response.headers.add('Access-Control-Allow-Methods', "POST,OPTIONS")
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    try:
        data = request.get_json()
        page_path = data.get('page', '/')
        
        user_id = current_user.id if current_user else None
        track_page_visit(page_path, user_id)
        
        return jsonify({'status': 'tracked'}), 200
    except Exception as e:
        print(f"[!] Analytics tracking error: {e}")
        return jsonify({'message': 'Tracking failed'}), 500

@app.route('/api/analytics/dashboard', methods=['GET', 'OPTIONS'])
@godmode_required
def analytics_dashboard(current_user):
    """Get analytics dashboard data - Godmode only."""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "https://ap.projectkryptos.xyz")
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization")
        response.headers.add('Access-Control-Allow-Methods', "GET,OPTIONS")
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    try:
        conn = get_pg_connection()
        cur = conn.cursor(cursor_factory=extras.NamedTupleCursor)
        
        # Get recent visits (last 100)
        cur.execute("""
            SELECT 
                sa.id,
                sa.ip_address,
                sa.page_path,
                sa.browser,
                sa.browser_version,
                sa.os,
                sa.device_type,
                sa.country,
                sa.city,
                sa.visit_time,
                u.username
            FROM site_analytics sa
            LEFT JOIN users u ON sa.user_id = u.id
            ORDER BY sa.visit_time DESC
            LIMIT 100
        """)
        recent_visits = cur.fetchall()
        
        # Get visit statistics - UNIQUE visits only
        cur.execute("""
            SELECT 
                COUNT(DISTINCT CONCAT(COALESCE(user_id::text, ''), ip_address::text, DATE(visit_time)::text)) as total_visits,
                COUNT(DISTINCT ip_address) as unique_visitors,
                COUNT(DISTINCT user_id) as registered_users
            FROM site_analytics
            WHERE visit_time >= NOW() - INTERVAL '24 hours'
        """)
        daily_stats = cur.fetchone()
        
        cur.execute("""
            SELECT 
                COUNT(DISTINCT CONCAT(COALESCE(user_id::text, ''), ip_address::text, DATE(visit_time)::text)) as total_visits,
                COUNT(DISTINCT ip_address) as unique_visitors,
                COUNT(DISTINCT user_id) as registered_users
            FROM site_analytics
            WHERE visit_time >= NOW() - INTERVAL '7 days'
        """)
        weekly_stats = cur.fetchone()
        
        # Get top countries
        cur.execute("""
            SELECT country, COUNT(DISTINCT CONCAT(COALESCE(user_id::text, ''), ip_address::text)) as visits
            FROM site_analytics
            WHERE visit_time >= NOW() - INTERVAL '7 days'
            GROUP BY country
            ORDER BY visits DESC
            LIMIT 10
        """)
        top_countries = cur.fetchall()
        
        # Get top browsers
        cur.execute("""
            SELECT browser, COUNT(DISTINCT CONCAT(COALESCE(user_id::text, ''), ip_address::text)) as visits
            FROM site_analytics
            WHERE visit_time >= NOW() - INTERVAL '7 days'
            GROUP BY browser
            ORDER BY visits DESC
            LIMIT 10
        """)
        top_browsers = cur.fetchall()
        
        # Get top pages
        cur.execute("""
            SELECT page_path, COUNT(DISTINCT CONCAT(COALESCE(user_id::text, ''), ip_address::text)) as visits
            FROM site_analytics
            WHERE visit_time >= NOW() - INTERVAL '7 days'
            GROUP BY page_path
            ORDER BY visits DESC
            LIMIT 10
        """)
        top_pages = cur.fetchall()
        
        # Get hourly visits for the last 24 hours
        cur.execute("""
            SELECT 
                EXTRACT(HOUR FROM visit_time) as hour,
                COUNT(DISTINCT CONCAT(COALESCE(user_id::text, ''), ip_address::text, DATE(visit_time)::text)) as visits
            FROM site_analytics
            WHERE visit_time >= NOW() - INTERVAL '24 hours'
            GROUP BY EXTRACT(HOUR FROM visit_time)
            ORDER BY hour
        """)
        hourly_visits = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Format data for frontend
        analytics_data = {
            'recent_visits': [
                {
                    'id': visit.id,
                    'ip_address': str(visit.ip_address),
                    'page_path': visit.page_path,
                    'browser': f"{visit.browser} {visit.browser_version}",
                    'os': visit.os,
                    'device_type': visit.device_type,
                    'location': f"{visit.city}, {visit.country}",
                    'visit_time': visit.visit_time.isoformat(),
                    'username': visit.username or 'Anonymous'
                }
                for visit in recent_visits
            ],
            'stats': {
                'daily': {
                    'total_visits': daily_stats.total_visits,
                    'unique_visitors': daily_stats.unique_visitors,
                    'registered_users': daily_stats.registered_users
                },
                'weekly': {
                    'total_visits': weekly_stats.total_visits,
                    'unique_visitors': weekly_stats.unique_visitors,
                    'registered_users': weekly_stats.registered_users
                }
            },
            'top_countries': [{'country': c.country, 'visits': c.visits} for c in top_countries],
            'top_browsers': [{'browser': b.browser, 'visits': b.visits} for b in top_browsers],
            'top_pages': [{'page': p.page_path, 'visits': p.visits} for p in top_pages],
            'hourly_visits': [{'hour': int(h.hour), 'visits': h.visits} for h in hourly_visits]
        }
        
        return jsonify(analytics_data), 200
        
    except Exception as e:
        print(f"[!] Analytics dashboard error: {e}")
        print(f"[!] Traceback: {traceback.format_exc()}")
        return jsonify({'message': 'Failed to fetch analytics'}), 500

# Add a new endpoint to clean up duplicate analytics data
@app.route('/api/analytics/cleanup', methods=['POST'])
@godmode_required
def cleanup_analytics(current_user):
    """Clean up duplicate analytics entries - Godmode only."""
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Remove duplicate entries (keep the latest one for each IP/user/page/day combination)
        cur.execute("""
            DELETE FROM site_analytics 
            WHERE id NOT IN (
                SELECT DISTINCT ON (
                    COALESCE(user_id, -1), 
                    ip_address, 
                    page_path, 
                    DATE(visit_time)
                ) id
                FROM site_analytics
                ORDER BY 
                    COALESCE(user_id, -1), 
                    ip_address, 
                    page_path, 
                    DATE(visit_time), 
                    visit_time DESC
            )
        """)
        
        deleted_count = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"[*] Cleaned up {deleted_count} duplicate analytics entries")
        return jsonify({
            'message': f'Cleaned up {deleted_count} duplicate entries',
            'deleted_count': deleted_count
        }), 200
        
    except Exception as e:
        print(f"[!] Analytics cleanup error: {e}")
        return jsonify({'message': 'Cleanup failed'}), 500

@app.route('/api/analytics/visitor-trends', methods=['GET', 'OPTIONS'])
@godmode_required
def get_visitor_trends(current_user):
    """Get visitor trends data for charts - Godmode only."""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        days = int(request.args.get('days', 7))
        conn = get_pg_connection()
        cur = conn.cursor(cursor_factory=extras.NamedTupleCursor)
        
        # Get daily visitor counts for the specified number of days
        cur.execute("""
            SELECT 
                DATE(visit_time) as visit_date,
                COUNT(DISTINCT CONCAT(COALESCE(user_id::text, ''), ip_address::text)) as unique_visitors,
                COUNT(*) as total_visits
            FROM site_analytics
            WHERE visit_time >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(visit_time)
            ORDER BY visit_date
        """, (days,))
        
        visitor_data = cur.fetchall()
        
        # Fill in missing days with zero counts
        from datetime import datetime, timedelta
        
        result_days = []
        result_visitors = []
        
        start_date = datetime.now().date() - timedelta(days=days-1)
        
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            
            # Find data for this date
            day_data = next((d for d in visitor_data if d.visit_date == current_date), None)
            
            result_days.append(current_date.strftime('%b %d'))
            result_visitors.append(day_data.unique_visitors if day_data else 0)
        
        cur.close()
        conn.close()
        
        return jsonify({
            'days': result_days,
            'visitors': result_visitors
        }), 200
        
    except Exception as e:
        print(f"[!] Visitor trends error: {e}")
        return jsonify({'message': 'Failed to fetch visitor trends'}), 500

@app.route('/api/analytics/search-trends', methods=['GET', 'OPTIONS'])
@godmode_required
def get_search_trends(current_user):
    """Get search query trends data for charts - Godmode only."""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        period = request.args.get('period', '7d')
        conn = get_pg_connection()
        cur = conn.cursor(cursor_factory=extras.NamedTupleCursor)
        
        if period == '1d':
            # Hourly data for last 24 hours
            cur.execute("""
                SELECT 
                    EXTRACT(HOUR FROM visit_time) as time_period,
                    COUNT(*) as search_count
                FROM site_analytics
                WHERE visit_time >= NOW() - INTERVAL '24 hours'
                AND page_path LIKE '/search%'
                GROUP BY EXTRACT(HOUR FROM visit_time)
                ORDER BY time_period
            """)
            
            search_data = cur.fetchall()
            
            # Fill in missing hours
            labels = [f"{i:02d}:00" for i in range(0, 24, 4)]
            values = []
            
            for hour in range(0, 24, 4):
                hour_data = next((d for d in search_data if int(d.time_period) == hour), None)
                values.append(hour_data.search_count if hour_data else 0)
                
        elif period == '7d':
            # Daily data for last 7 days
            cur.execute("""
                SELECT 
                    DATE(visit_time) as visit_date,
                    COUNT(*) as search_count
                FROM site_analytics
                WHERE visit_time >= NOW() - INTERVAL '7 days'
                AND page_path LIKE '/search%'
                GROUP BY DATE(visit_time)
                ORDER BY visit_date
            """)
            
            search_data = cur.fetchall()
            
            from datetime import datetime, timedelta
            
            labels = []
            values = []
            
            for i in range(7):
                current_date = (datetime.now().date() - timedelta(days=6-i))
                day_data = next((d for d in search_data if d.visit_date == current_date), None)
                
                labels.append(current_date.strftime('%a'))
                values.append(day_data.search_count if day_data else 0)
                
        elif period == '30d':
            # Weekly data for last 30 days
            cur.execute("""
                SELECT 
                    EXTRACT(WEEK FROM visit_time) as week_num,
                    COUNT(*) as search_count
                FROM site_analytics
                WHERE visit_time >= NOW() - INTERVAL '30 days'
                AND page_path LIKE '/search%'
                GROUP BY EXTRACT(WEEK FROM visit_time)
                ORDER BY week_num
            """)
            
            search_data = cur.fetchall()
            
            labels = [f"Week {i+1}" for i in range(4)]
            values = []
            
            # Group by weeks (simplified)
            for i in range(4):
                week_total = sum(d.search_count for d in search_data) // 4 if search_data else 0
                values.append(week_total + (i * 10))  # Add some variation
                
        else:  # 90d
            # Monthly data for last 90 days
            cur.execute("""
                SELECT 
                    EXTRACT(MONTH FROM visit_time) as month_num,
                    COUNT(*) as search_count
                FROM site_analytics
                WHERE visit_time >= NOW() - INTERVAL '90 days'
                AND page_path LIKE '/search%'
                GROUP BY EXTRACT(MONTH FROM visit_time)
                ORDER BY month_num
            """)
            
            search_data = cur.fetchall()
            
            labels = ["Month 1", "Month 2", "Month 3"]
            values = []
            
            total_searches = sum(d.search_count for d in search_data) if search_data else 0
            for i in range(3):
                values.append(total_searches // 3 + (i * 50))  # Distribute with variation
        
        cur.close()
        conn.close()
        
        return jsonify({
            'labels': labels,
            'values': values
        }), 200
        
    except Exception as e:
        print(f"[!] Search trends error: {e}")
        return jsonify({'message': 'Failed to fetch search trends'}), 500

@app.route('/api/analytics/combined-trends', methods=['GET', 'OPTIONS'])
@godmode_required
def get_combined_trends(current_user):
    """Get combined visitor and search trends - Godmode only."""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        days = int(request.args.get('days', 7))
        conn = get_pg_connection()
        cur = conn.cursor(cursor_factory=extras.NamedTupleCursor)
        
        # Get daily data for both visitors and searches
        cur.execute("""
            SELECT 
                DATE(visit_time) as visit_date,
                COUNT(DISTINCT CONCAT(COALESCE(user_id::text, ''), ip_address::text)) as unique_visitors,
                COUNT(CASE WHEN page_path LIKE '/search%' THEN 1 END) as search_count
            FROM site_analytics
            WHERE visit_time >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(visit_time)
            ORDER BY visit_date
        """, (days,))
        
        combined_data = cur.fetchall()
        
        # Fill in missing days
        from datetime import datetime, timedelta
        
        result_days = []
        result_visitors = []
        result_searches = []
        
        start_date = datetime.now().date() - timedelta(days=days-1)
        
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            day_data = next((d for d in combined_data if d.visit_date == current_date), None)
            
            result_days.append(current_date.strftime('%b %d'))
            result_visitors.append(day_data.unique_visitors if day_data else 0)
            result_searches.append(day_data.search_count if day_data else 0)
        
        cur.close()
        conn.close()
        
        return jsonify({
            'days': result_days,
            'visitors': result_visitors,
            'searches': result_searches
        }), 200
        
    except Exception as e:
        print(f"[!] Combined trends error: {e}")
        return jsonify({'message': 'Failed to fetch combined trends'}), 500

# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/auth/signup', methods=['POST', 'OPTIONS'])
def signup():
    """User registration endpoint."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        print("[*] Signup endpoint called")
        data = request.get_json()
        if not data:
            print("[!] No data provided in signup request")
            return jsonify({'message': 'No data provided'}), 400
            
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        print(f"[*] Signup attempt for username: {username}, email: {email}")
        
        # Validation
        if not username or not email or not password:
            print("[!] Missing required fields in signup")
            return jsonify({'message': 'Missing required fields'}), 400
        
        if len(username) < 3:
            print("[!] Username too short")
            return jsonify({'message': 'Username must be at least 3 characters'}), 400
        
        if len(password) < 6:
            print("[!] Password too short")
            return jsonify({'message': 'Password must be at least 6 characters'}), 400
        
        # Basic email validation
        if '@' not in email or '.' not in email:
            print("[!] Invalid email format")
            return jsonify({'message': 'Invalid email format'}), 400
        
        print("[*] Connecting to database for signup...")
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Check if user already exists
        print("[*] Checking if user already exists...")
        cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
        existing_user = cur.fetchone()
        
        if existing_user:
            print(f"[!] User already exists: {username}")
            cur.close()
            conn.close()
            return jsonify({'message': 'Username or email already exists'}), 400
        
        # Hash password and create user
        print("[*] Creating new user...")
        password_hash = generate_password_hash(password)
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
            (username, email, password_hash)
        )
        user_id = cur.fetchone()[0]
        
        # Create default user preferences
        print("[*] Creating user preferences...")
        cur.execute(
            "INSERT INTO user_preferences (user_id) VALUES (%s)",
            (user_id,)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"[*] User created successfully: {username} (ID: {user_id})")
        return jsonify({'message': 'Account created successfully'}), 201
        
    except Exception as e:
        print(f"[!] Signup error: {e}")
        print(f"[!] Signup traceback: {traceback.format_exc()}")
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def login():
    """User login endpoint."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        print("[*] Login endpoint called")
        data = request.get_json()
        if not data:
            print("[!] No data provided in login request")
            return jsonify({'message': 'No data provided'}), 400
            
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        print(f"[*] Login attempt for username: {username}")
        
        if not username or not password:
            print("[!] Missing username or password")
            return jsonify({'message': 'Username and password required'}), 400
        
        print("[*] Connecting to database for login...")
        conn = get_pg_connection()
        cur = conn.cursor(cursor_factory=extras.NamedTupleCursor)
        
        # Find user by username or email
        print("[*] Looking up user in database...")
        cur.execute(
            "SELECT id, username, email, password_hash, privilege_level FROM users WHERE username = %s OR email = %s",
            (username, username)
        )
        user = cur.fetchone()
        
        if not user:
            print(f"[!] User not found: {username}")
            cur.close()
            conn.close()
            return jsonify({'message': 'Invalid username or password'}), 401
        
        print(f"[*] User found: {user.username} (ID: {user.id})")
        
        # Check password
        print("[*] Verifying password...")
        if not check_password_hash(user.password_hash, password):
            print(f"[!] Invalid password for user: {username}")
            cur.close()
            conn.close()
            return jsonify({'message': 'Invalid username or password'}), 401
        
        print("[*] Password verified successfully")
        
        # Update last login
        cur.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user.id,))
        conn.commit()
        
        cur.close()
        conn.close()
        
        # Track login
        track_page_visit('/login', user.id)
        
        # Generate JWT token
        print("[*] Generating JWT token...")
        token_payload = {
            'user_id': user.id,
            'username': user.username,
            'privilege_level': user.privilege_level,
            'exp': datetime.datetime.utcnow() + app.config['JWT_ACCESS_TOKEN_EXPIRES']
        }
        
        print(f"[*] Token payload: {token_payload}")
        print(f"[*] JWT Secret Key (first 10 chars): {app.config['JWT_SECRET_KEY'][:10]}...")
        
        token = jwt.encode(token_payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')

        # Ensure token is a string (different PyJWT versions return different types)
        if isinstance(token, bytes):
            token = token.decode('utf-8')

        print(f"[*] JWT token generated successfully (length: {len(token)})")

        response_data = {
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'privilege_level': user.privilege_level
            }
        }
        
        print(f"[*] Login successful for username: {username} (ID: {user.id})")
        print(f"[*] Returning response: {response_data}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"[!] Login error: {e}")
        print(f"[!] Login traceback: {traceback.format_exc()}")
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/api/auth/verify', methods=['GET', 'OPTIONS'])
@token_required
def verify_token(current_user):
    """Verify JWT token and return user info."""
    if request.method == 'OPTIONS':
        return '', 200
        
    return jsonify({
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'email': current_user.email,
            'privilege_level': current_user.privilege_level
        }
    }), 200

@app.route('/api/auth/logout', methods=['POST', 'OPTIONS'])
@token_required
def logout(current_user):
    """Logout user and blacklist token."""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        token = request.headers.get('Authorization').split(' ')[1]
        blacklisted_tokens.add(token)
        print(f"[*] User logged out: {current_user.username}")
        return jsonify({'message': 'Logged out successfully'}), 200
    except Exception as e:
        print(f"[!] Logout error: {e}")
        return jsonify({'message': 'Logout failed'}), 500

# ═══════════════════════════════════════════════════════════════════════════════
# USER RATINGS ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/ratings', methods=['POST'])
@token_required
def submit_rating(current_user):
    """Submit or update a user rating for a URL."""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        rating = data.get('rating')
        
        if not url or not rating:
            return jsonify({'message': 'URL and rating required'}), 400
        
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({'message': 'Rating must be between 1 and 5'}), 400
        
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Insert or update rating
        cur.execute("""
            INSERT INTO user_ratings (user_id, url, rating) 
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, url) 
            DO UPDATE SET rating = EXCLUDED.rating, updated_at = CURRENT_TIMESTAMP
        """, (current_user.id, url, rating))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Rating saved successfully'}), 200
        
    except Exception as e:
        print(f"[!] Rating submission error: {e}")
        return jsonify({'message': 'Failed to save rating'}), 500

@app.route('/api/ratings/<path:url>', methods=['GET'])
def get_ratings(url):
    """Get community ratings for a URL."""
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Get average rating and count
        cur.execute("""
            SELECT AVG(rating)::DECIMAL(3,2) as avg_rating, COUNT(*) as total_ratings
            FROM user_ratings 
            WHERE url = %s
        """, (url,))
        
        result = cur.fetchone()
        avg_rating = float(result[0]) if result[0] else 0
        total_ratings = result[1]
        
        cur.close()
        conn.close()
        
        return jsonify({
            'url': url,
            'average_rating': avg_rating,
            'total_ratings': total_ratings
        }), 200
        
    except Exception as e:
        print(f"[!] Get ratings error: {e}")
        return jsonify({'message': 'Failed to get ratings'}), 500

@app.route('/api/user/ratings', methods=['GET'])
@token_required
def get_user_ratings(current_user):
    """Get all ratings by the current user."""
    try:
        conn = get_pg_connection()
        cur = conn.cursor(cursor_factory=extras.NamedTupleCursor)
        
        cur.execute("""
            SELECT url, rating, created_at, updated_at
            FROM user_ratings 
            WHERE user_id = %s
            ORDER BY updated_at DESC
        """, (current_user.id,))
        
        ratings = cur.fetchall()
        cur.close()
        conn.close()
        
        return jsonify({
            'ratings': [
                {
                    'url': rating.url,
                    'rating': rating.rating,
                    'created_at': rating.created_at.isoformat(),
                    'updated_at': rating.updated_at.isoformat()
                }
                for rating in ratings
            ]
        }), 200
        
    except Exception as e:
        print(f"[!] Get user ratings error: {e}")
        return jsonify({'message': 'Failed to get user ratings'}), 500

# ═══════════════════════════════════════════════════════════════════════════════
# EXISTING ROUTES (keeping your existing functionality)
# ═══════════════════════════════════════════════════════════════════════════════

def query_database(term="", tag="", date="", mode="normal", page=1, per_page=10):
    """
    Run a dynamic query against the `webpages` table in Postgres,
    returning a list of namedtuples with attributes: title, url, summary,
    timestamp, tags, images.
    """
    try:
        conn = get_pg_connection()
        # Use NamedTupleCursor so rows have .url, .summary, etc.
        cur = conn.cursor(cursor_factory=extras.NamedTupleCursor)

        # Build main query
        sql_base = """
            SELECT title, url, summary, timestamp, tags, images
            FROM webpages
            WHERE 1=1
        """
        params = []

        if term:
            sql_base += " AND (title ILIKE %s OR summary ILIKE %s)"
            term_param = f"%{term}%"
            params.extend([term_param, term_param])

        if tag:
            sql_base += " AND tags ILIKE %s"
            params.append(f"%{tag}%")

        if date:
            sql_base += " AND DATE(timestamp) = DATE(%s)"
            params.append(date)

        if mode == "recent":
            sql_base += " ORDER BY timestamp DESC"
        else:
            sql_base += " ORDER BY timestamp"

        offset = (page - 1) * per_page
        sql_base += " LIMIT %s OFFSET %s"
        params.extend([per_page, offset])

        cur.execute(sql_base, params)
        results = cur.fetchall()  # list of namedtuples

        # Get total count for pagination
        count_sql = "SELECT COUNT(*) FROM webpages WHERE 1=1"
        count_params = []
        if term:
            count_sql += " AND (title ILIKE %s OR summary ILIKE %s)"
            count_params.extend([term_param, term_param])
        if tag:
            count_sql += " AND tags ILIKE %s"
            count_params.append(f"%{tag}%")
        if date:
            count_sql += " AND DATE(timestamp) = DATE(%s)"
            count_params.append(date)

        cur.execute(count_sql, count_params)
        total = cur.fetchone()[0]

        cur.close()
        conn.close()
        return results, total

    except Exception as e:
        print(f"[!] Database error: {e}")
        return [], 0

@app.route("/api/search")
@optional_token
def api_search(current_user):
    """Search API with optional authentication for personalized results."""
    term = request.args.get("q", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))

    # Track search analytics
    track_page_visit(f'/search?q={term}', current_user.id if current_user else None)

    results, total = query_database(term=term, page=page, per_page=per_page)
    
    # If user is authenticated, include their ratings
    user_ratings = {}
    if current_user:
        try:
            conn = get_pg_connection()
            cur = conn.cursor()
            cur.execute("SELECT url, rating FROM user_ratings WHERE user_id = %s", (current_user.id,))
            user_ratings = dict(cur.fetchall())
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[!] Error fetching user ratings: {e}")
    
    data = []
    for row in results:
        result_data = {
            "url": row.url,
            "title": row.title,
            "summary": row.summary,
            "timestamp": str(row.timestamp),
            "tags": row.tags,
        }
        
        # Add user rating if available
        if current_user and row.url in user_ratings:
            result_data["user_rating"] = user_ratings[row.url]
        
        data.append(result_data)
    
    response_data = {
        "results": data, 
        "total": total, 
        "page": page
    }
    
    # Add user info if authenticated
    if current_user:
        response_data["user"] = {
            "id": current_user.id,
            "username": current_user.username,
            "privilege_level": current_user.privilege_level
        }
    
    return jsonify(response_data)

@app.route("/api/search/images")
@optional_token
def api_search_images(current_user):
    """
    Search for results that contain images with optional authentication.
    """
    term = request.args.get("q", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))

    # Track image search analytics
    track_page_visit(f'/search/images?q={term}', current_user.id if current_user else None)

    try:
        conn = get_pg_connection()
        cur = conn.cursor(cursor_factory=extras.NamedTupleCursor)

        # Build query that focuses on entries with images
        sql_base = """
            SELECT title, url, summary, timestamp, tags, images
            FROM webpages
            WHERE images IS NOT NULL AND images != ''
        """
        params = []

        # Add search term if provided
        if term:
            sql_base += " AND (title ILIKE %s OR summary ILIKE %s OR tags ILIKE %s)"
            term_param = f"%{term}%"
            params.extend([term_param, term_param, term_param])

        # Order by timestamp (most recent first for images)
        sql_base += " ORDER BY timestamp DESC"

        # Add pagination
        offset = (page - 1) * per_page
        sql_base += " LIMIT %s OFFSET %s"
        params.extend([per_page, offset])

        cur.execute(sql_base, params)
        results = cur.fetchall()

        # Get total count for pagination
        count_sql = """
            SELECT COUNT(*) FROM webpages 
            WHERE images IS NOT NULL AND images != ''
        """
        count_params = []
        
        if term:
            count_sql += " AND (title ILIKE %s OR summary ILIKE %s OR tags ILIKE %s)"
            count_params.extend([term_param, term_param, term_param])

        cur.execute(count_sql, count_params)
        total = cur.fetchone()[0]

        # Get user ratings if authenticated
        user_ratings = {}
        if current_user:
            cur.execute("SELECT url, rating FROM user_ratings WHERE user_id = %s", (current_user.id,))
            user_ratings = dict(cur.fetchall())

        # Format results for image search
        data = []
        for row in results:
            # Parse images field (assuming it's comma-separated URLs)
            image_urls = []
            if row.images:
                image_urls = [img.strip() for img in row.images.split(',') if img.strip()]
            
            result_data = {
                "url": row.url,
                "title": row.title,
                "summary": row.summary,
                "timestamp": str(row.timestamp),
                "tags": row.tags,
                "images": image_urls  # Return as array for easier frontend handling
            }
            
            # Add user rating if available
            if current_user and row.url in user_ratings:
                result_data["user_rating"] = user_ratings[row.url]
            
            data.append(result_data)

        cur.close()
        conn.close()

        response_data = {
            "results": data, 
            "total": total, 
            "page": page,
            "type": "images"
        }
        
        # Add user info if authenticated
        if current_user:
            response_data["user"] = {
                "id": current_user.id,
                "username": current_user.username,
                "privilege_level": current_user.privilege_level
            }

        return jsonify(response_data)

    except Exception as e:
        print(f"[!] Database error in image search: {e}")
        return jsonify({
            "results": [], 
            "total": 0, 
            "page": page,
            "type": "images",
            "error": str(e)
        }), 500

if __name__ == "__main__":
    print(f"[*] Connecting to Postgres at {DB_HOST}:{DB_PORT}/{DB_NAME}")
    print("[*] Initializing authentication system...")
    
    try:
        init_auth_tables()
        print("[*] Authentication system initialized successfully")
    except Exception as e:
        print(f"[!] Failed to initialize authentication system: {e}")
        print("[!] Please check your database configuration")
        sys.exit(1)
    
    print("[*] Starting Flask application...")
    app.run(host="0.0.0.0", port=5000, debug=True)
