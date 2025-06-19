import sqlite3
import os
from datetime import datetime
import time
from simhash import Simhash
from urllib.parse import urlparse

# ── Path to your DB file (now named database.db) ───────────────────────────────
DB_PATH = os.path.abspath(os.path.join(os.getcwd(), "database.db"))


def get_connection(timeout_ms: int = 5000):
    """
    Returns a new SQLite connection to DB_PATH (database.db), with:
      - PRAGMA journal_mode=WAL
      - PRAGMA synchronous=FULL
      - PRAGMA busy_timeout = timeout_ms
    """
    conn = sqlite3.connect(DB_PATH, timeout=timeout_ms / 1000.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=FULL;")
    conn.execute(f"PRAGMA busy_timeout = {timeout_ms};")
    return conn


def save_page(conn, title: str, url: str, summary: str, tags: str, images: str):
    """
    Inserts a page into the `webpages` table, skipping duplicates based on simhash
    """
    timestamp = datetime.utcnow().isoformat() + 'Z'
    content_hash = Simhash(summary)
    # Skip duplicate pages with same path and similar content
    def normalize_url_path(u):
        parsed = urlparse(u)
        return parsed.path.rstrip('/')

    # Check existing pages
    retries = 3
    delay = 0.1
    for _ in range(retries):
        try:
            c = conn.cursor()
            c.execute("SELECT url, content_hash FROM webpages")
            for existing_url, existing_hash in c.fetchall():
                if existing_hash:
                    distance = Simhash(existing_hash).distance(content_hash)
                    if normalize_url_path(existing_url) == normalize_url_path(url) and distance <= 3:
                        return
            break
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                time.sleep(delay)
            else:
                raise
    # Insert new page
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO webpages(
            title, url, summary, timestamp, tags, content_hash, images
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (title, url, summary, timestamp, tags, str(content_hash), images)
    )
    conn.commit()


def page_exists(conn, url: str) -> bool:
    """
    Returns True if the given URL has already been crawled.
    """
    c = conn.cursor()
    c.execute("SELECT 1 FROM crawled_urls WHERE url = ?;", (url,))
    return c.fetchone() is not None


def setup_schema():
    """
    Creates necessary tables if they don't already exist:
      - webpages: stores content of each page
      - webpages_fts: FTS5 virtual table for full-text search
      - triggers to keep webpages_fts in sync
      - crawled_urls: stores every URL we've processed
      - pending_urls: URLs awaiting crawl
      - Language: stores detected language per URL
    """
    conn = get_connection()
    c = conn.cursor()

    # 1) Create the main 'webpages' table
    c.execute("""
    CREATE TABLE IF NOT EXISTS webpages (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        title         TEXT,
        url           TEXT UNIQUE,
        summary       TEXT,
        timestamp     TEXT,
        tags          TEXT,
        content_hash  TEXT,
        images        TEXT
    );
    """
    )

    # 2) Create FTS virtual table
    c.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS webpages_fts USING fts5(
        title, summary, tags, content='webpages', content_rowid='id'
    );
    """
    )
    # Triggers to keep FTS in sync
    c.execute("""
    CREATE TRIGGER IF NOT EXISTS webpages_ai AFTER INSERT ON webpages BEGIN
      INSERT INTO webpages_fts(rowid, title, summary, tags)
      VALUES (new.id, new.title, new.summary, new.tags);
    END;
    """
    )
    c.execute("""
    CREATE TRIGGER IF NOT EXISTS webpages_ad AFTER DELETE ON webpages BEGIN
      INSERT INTO webpages_fts(webpages_fts, rowid, title, summary, tags)
      VALUES('delete', old.id, old.title, old.summary, old.tags);
    END;
    """
    )
    c.execute("""
    CREATE TRIGGER IF NOT EXISTS webpages_au AFTER UPDATE ON webpages BEGIN
      INSERT INTO webpages_fts(webpages_fts, rowid, title, summary, tags)
      VALUES('delete', old.id, old.title, old.summary, old.tags);
      INSERT INTO webpages_fts(rowid, title, summary, tags)
      VALUES (new.id, new.title, new.summary, new.tags);
    END;
    """
    )

    # 3) Create 'crawled_urls' table
    c.execute("""
    CREATE TABLE IF NOT EXISTS crawled_urls (
        url TEXT PRIMARY KEY
    );
    """
    )

    # 4) Create 'pending_urls' table
    c.execute("""
    CREATE TABLE IF NOT EXISTS pending_urls (
        url TEXT PRIMARY KEY
    );
    """
    )

    # 5) Create table to store page-language mapping
    c.execute("""
    CREATE TABLE IF NOT EXISTS Language (
        url      TEXT PRIMARY KEY,
        language TEXT
    );
    """
    )

    conn.commit()
    conn.close()
