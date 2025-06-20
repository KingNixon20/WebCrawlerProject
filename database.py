#!/usr/bin/env python3
"""
database.py

PostgreSQL database utilities for the DarkNetCrawler.
Handles schema setup, page saving, and deduplication.
"""

import logging
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from simhash import Simhash
from urllib.parse import urlparse
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS

# Logger setup
logging.basicConfig(filename='crawler.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Connection pool
db_pool = ThreadedConnectionPool(1, 5, host=DB_HOST, port=DB_PORT,
                                 dbname=DB_NAME, user=DB_USER, password=DB_PASS)

def get_connection():
    """Return a connection from the pool."""
    return db_pool.getconn()

def release_connection(conn):
    """Return a connection to the pool."""
    db_pool.putconn(conn)

def close_pool():
    """Close all connections in the pool."""
    db_pool.closeall()

def normalize_url_path(url):
    """Normalize URL path for deduplication."""
    parsed = urlparse(url)
    return parsed.path.rstrip('/')

def save_page(conn, title: str, url: str, summary: str, tags: list, images: list):
    """
    Inserts a page into webpages, tags, and images tables, skipping duplicates
    based on Simhash and URL path.
    """
    content_hash = str(Simhash(summary))
    cur = conn.cursor()
    try:
        # Check for duplicates
        cur.execute("SELECT url, content_hash FROM webpages WHERE content_hash IS NOT NULL;")
        for existing_url, existing_hash in cur.fetchall():
            if existing_hash and normalize_url_path(existing_url) == normalize_url_path(url):
                distance = Simhash(existing_hash).distance(Simhash(content_hash))
                if distance <= 3:
                    logger.info(f"Skipped duplicate page: {url} (hash distance {distance})")
                    return

        # Insert page
        cur.execute(
            """
            INSERT INTO webpages (title, url, summary, content_hash, timestamp)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (url) DO NOTHING
            RETURNING url;
            """,
            (title, url, summary, content_hash)
        )
        if cur.fetchone():  # Insert succeeded
            logger.info(f"Stored page: {url} ({title})")
        else:
            logger.info(f"Skipped page due to URL conflict: {url}")

        # Insert tags
        for tag in tags:
            cur.execute(
                """
                INSERT INTO tags (url, tag) VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (url, tag)
            )
        # Insert images
        for image in images:
            cur.execute(
                """
                INSERT INTO images (url, image_url) VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (url, image)
            )
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving page {url}: {e}")
        conn.rollback()
    finally:
        cur.close()

def page_exists(conn, url: str) -> bool:
    """Returns True if the URL is in crawled_urls."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM crawled_urls WHERE url = %s;", (url,))
        return cur.fetchone() is not None
    finally:
        cur.close()

def setup_schema():
    """Creates and migrates PostgreSQL tables for the crawler."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Create tables
        cur.execute("CREATE TABLE IF NOT EXISTS crawled_urls(url TEXT PRIMARY KEY);")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pending_urls(
                url TEXT PRIMARY KEY,
                depth INTEGER DEFAULT 0
            );
        """)
        # Migrate pending_urls to add depth if missing
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'pending_urls' AND column_name = 'depth';
        """)
        if not cur.fetchone():
            logger.info("Adding depth column to pending_urls")
            cur.execute("ALTER TABLE pending_urls ADD COLUMN depth INTEGER DEFAULT 0;")
            cur.execute("UPDATE pending_urls SET depth = 0 WHERE depth IS NULL;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS webpages(
                title TEXT,
                url TEXT PRIMARY KEY,
                summary TEXT,
                content_hash TEXT,
                timestamp TIMESTAMP DEFAULT NOW(),
                tsv TSVECTOR GENERATED ALWAYS AS (
                    to_tsvector('english', coalesce(title, '') || ' ' || coalesce(summary, ''))
                ) STORED
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tags(
                url TEXT REFERENCES webpages(url),
                tag TEXT,
                PRIMARY KEY (url, tag)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS images(
                url TEXT REFERENCES webpages(url),
                image_url TEXT,
                PRIMARY KEY (url, image_url)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS language(
                url TEXT PRIMARY KEY,
                language TEXT
            );
        """)
        cur.execute("CREATE TABLE IF NOT EXISTS blocked_domains(domain TEXT PRIMARY KEY);")
        # Indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_webpages_timestamp ON webpages(timestamp);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_webpages_tsv ON webpages USING GIN(tsv);")
        conn.commit()
    except Exception as e:
        logger.error(f"Schema creation/migration error: {e}")
        conn.rollback()
    finally:
        cur.close()
        release_connection(conn)