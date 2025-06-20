#!/usr/bin/env python3
"""
crawler.py

A multi-threaded web crawler that indexes pages into PostgreSQL.
Uses psycopg2 with a connection pool and DB credentials from config.py.
"""

import threading
import logging
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import SSLError
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from time import time, sleep
from random import uniform
from queue import Queue, Empty
import urllib.robotparser as robotparser
import urllib3
from psycopg2.pool import ThreadedConnectionPool
from collections import defaultdict

from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
from langdetect import detect, LangDetectException
from utils import extract_links, summarize_content, extract_images, generate_tags, is_xml_content

# Suppress InsecureRequestWarning when verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Configuration ─────────────────────────────────────────────────────────────
logging.basicConfig(filename='crawler.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

USER_AGENT = "DarkNetCrawler@projectkryptos.xyz"
RESPECT_ROBOTS = True
respect_robots = RESPECT_ROBOTS  # Alias for backward compatibility
IGNORE_TOS = False
DOMAIN_DELAY = 1.0  # Seconds between requests to same domain
MAX_DEPTH = 5  # Maximum crawl depth from seed URLs

# ── Globals ───────────────────────────────────────────────────────────────────
shutdown_event = threading.Event()
visited = set()
visited_lock = threading.Lock()
write_queue = Queue()
_SENTINEL = object()
robots_parsers = {}
blocked_domains = set()
tos_checked_domains = set()
domain_last_accessed = defaultdict(float)
domain_lock = threading.Lock()

# Connection pool
db_pool = ThreadedConnectionPool(1, 5, host=DB_HOST, port=DB_PORT, 
                                 dbname=DB_NAME, user=DB_USER, password=DB_PASS)

# Global requests session
global_session = requests.Session()
retry_args = dict(total=2, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503, 504])
try:
    retry = Retry(**retry_args, allowed_methods=["GET"])
except TypeError:
    retry = Retry(**retry_args, method_whitelist=["GET"])
adapter = HTTPAdapter(max_retries=retry)
global_session.mount("http://", adapter)
global_session.mount("https://", adapter)
global_session.headers.update({"User-Agent": USER_AGENT})

def get_pg_connection():
    """Return a connection from the pool."""
    return db_pool.getconn()

def release_pg_connection(conn):
    """Return a connection to the pool."""
    db_pool.putconn(conn)

class DBWorker(threading.Thread):
    """Background thread that serializes all DB writes to Postgres."""
    def __init__(self):
        super().__init__(daemon=True)

    def run(self):
        conn = get_pg_connection()
        try:
            while True:
                try:
                    req = write_queue.get(timeout=1)
                except Empty:
                    if shutdown_event.is_set() and write_queue.empty():
                        break
                    continue

                if req is _SENTINEL:
                    break

                action, payload = req
                cur = conn.cursor()
                try:
                    if action == "record_visited":
                        self._record_visited(cur, payload)
                    elif action == "enqueue_pending":
                        self._enqueue_pending(cur, payload)
                    elif action == "dequeue_pending":
                        self._dequeue_pending(cur, payload)
                    elif action == "save_page":
                        self._save_page(cur, payload)
                    elif action == "record_language":
                        self._record_language(cur, payload)
                    conn.commit()
                except Exception as e:
                    logger.error(f"DB error in {action}: {e}")
                    conn.rollback()
                finally:
                    cur.close()
                    write_queue.task_done()
        except Exception as e:
            logger.error(f"DBWorker crashed: {e}")
        finally:
            release_pg_connection(conn)

    def _record_visited(self, cur, url):
        cur.execute(
            "INSERT INTO crawled_urls(url) VALUES (%s) ON CONFLICT DO NOTHING;",
            (url,)
        )

    def _enqueue_pending(self, cur, payload):
        url, depth = payload
        cur.execute(
            "INSERT INTO pending_urls(url, depth) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
            (url, depth)
        )

    def _dequeue_pending(self, cur, url):
        cur.execute("DELETE FROM pending_urls WHERE url = %s;", (url,))

    def _save_page(self, cur, payload):
        title, url, summary, tags, images = payload
        cur.execute(
            """
            INSERT INTO webpages (title, url, summary, timestamp)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (url) DO NOTHING;
            """,
            (title, url, summary)
        )
        for tag in tags:
            cur.execute(
                """
                INSERT INTO tags (url, tag) VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (url, tag)
            )
        for image in images:
            cur.execute(
                """
                INSERT INTO images (url, image_url) VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (url, image)
            )

    def _record_language(self, cur, payload):
        url, lang = payload
        cur.execute(
            """
            INSERT INTO language (url, language)
            VALUES (%s, %s)
            ON CONFLICT (url) DO UPDATE SET language = EXCLUDED.language;
            """,
            (url, lang)
        )

def get_robot_parser(domain):
    if domain in robots_parsers:
        return robots_parsers[domain]
    rp = robotparser.RobotFileParser()
    try:
        rp.set_url(f"https://{domain}/robots.txt")
        rp.read()
    except Exception:
        rp = None
    robots_parsers[domain] = rp
    return rp

def is_allowed_by_robots(url):
    if not RESPECT_ROBOTS:
        return True
    parsed = urlparse(url)
    rp = get_robot_parser(parsed.netloc)
    return rp is None or rp.can_fetch(USER_AGENT, url)

def check_tos_for_domain(domain):
    if domain in tos_checked_domains or IGNORE_TOS:
        return
    tos_checked_domains.add(domain)
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM blocked_domains WHERE domain = %s;", (domain,))
        if cur.fetchone():
            blocked_domains.add(domain)
            return
        for path in ("/terms", "/terms-of-service", "/tos", "/legal/terms"):
            try:
                r = global_session.get(
                    f"https://{domain}{path}", timeout=5
                )
                text = r.text.lower()
                if r.status_code == 200 and any(
                    kw in text for kw in
                    ("automated", "robot", "scrap", "crawl", "not allowed", "disallow", "unauthorized")
                ):
                    blocked_domains.add(domain)
                    cur.execute("INSERT INTO blocked_domains(domain) VALUES (%s);", (domain,))
                    conn.commit()
                    logger.info(f"Disallowed by ToS: {domain}")
                    return
            except Exception:
                continue
        conn.commit()
    except Exception as e:
        logger.error(f"ToS check error for {domain}: {e}")
        conn.rollback()
    finally:
        cur.close()
        release_pg_connection(conn)

def ignore_robots_and_tos():
    """Disable robots.txt and ToS checks on the fly."""
    global RESPECT_ROBOTS, IGNORE_TOS, blocked_domains, tos_checked_domains, robots_parsers, respect_robots
    RESPECT_ROBOTS = False
    respect_robots = RESPECT_ROBOTS  # Update alias
    IGNORE_TOS = True
    blocked_domains.clear()
    tos_checked_domains.clear()
    robots_parsers.clear()
    logger.info("Robots.txt and ToS checks disabled.")

def crawl_url(url, depth):
    """Fetch a single URL, extract data, detect language, and enqueue new links."""
    if shutdown_event.is_set() or depth > MAX_DEPTH:
        return set()

    dom = urlparse(url).netloc
    if not is_allowed_by_robots(url):
        logger.info(f"Blocked by robots.txt: {url}")
        return set()

    if not IGNORE_TOS and dom not in blocked_domains:
        check_tos_for_domain(dom)
        if dom in blocked_domains:
            return set()

    with visited_lock:
        if url in visited:
            return set()
        visited.add(url)

    with domain_lock:
        now = time()
        last = domain_last_accessed[dom]
        if now - last < DOMAIN_DELAY:
            sleep(DOMAIN_DELAY - (now - last))
        domain_last_accessed[dom] = now

    try:
        r = global_session.get(url, timeout=10)
    except SSLError:
        r = global_session.get(url, timeout=10, verify=False)
    except Exception as e:
        logger.error(f"Request error for {url}: {e}")
        write_queue.put(("dequeue_pending", url))
        return set()

    if r.status_code != 200:
        write_queue.put(("dequeue_pending", url))
        return set()

    write_queue.put(("record_visited", url))
    write_queue.put(("dequeue_pending", url))

    html = r.text
    if is_xml_content(html):
        logger.info(f"Skipping XML content for storage: {url}")
        soup = BeautifulSoup(html, 'xml')
        links = extract_links(url, html)
        new_links = set()
        for link in links:
            write_queue.put(("enqueue_pending", (link, depth + 1)))
            new_links.add(link)
        return new_links

    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.string.strip() if soup.title else url
    summary = summarize_content(html)
    tags = generate_tags(soup.get_text(" ", strip=True), title=title, url=url)
    images = extract_images(html)
    write_queue.put(("save_page", (title, url, summary, tags, images)))

    try:
        lang = detect(soup.get_text(" ", strip=True))
        write_queue.put(("record_language", (url, lang)))
    except LangDetectException:
        write_queue.put(("record_language", (url, "unknown")))

    links = extract_links(url, html)
    new_links = set()
    for link in links:
        write_queue.put(("enqueue_pending", (link, depth + 1)))
        new_links.add(link)

    return new_links

def run_crawler(seed_urls, max_threads=2):
    """Main entry point: ensure schema, seed URLs, and crawl until done."""
    # Ensure tables exist and migrate schema
    conn = get_pg_connection()
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
                title TEXT, url TEXT PRIMARY KEY, summary TEXT,
                timestamp TIMESTAMP DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tags(
                url TEXT REFERENCES webpages(url), tag TEXT,
                PRIMARY KEY (url, tag)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS images(
                url TEXT REFERENCES webpages(url), image_url TEXT,
                PRIMARY KEY (url, image_url)
            );
        """)
        cur.execute("CREATE TABLE IF NOT EXISTS language(url TEXT PRIMARY KEY, language TEXT);")
        cur.execute("CREATE TABLE IF NOT EXISTS blocked_domains(domain TEXT PRIMARY KEY);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_webpages_timestamp ON webpages(timestamp);")
        conn.commit()
    except Exception as e:
        logger.error(f"Schema creation/migration error: {e}")
        conn.rollback()
    finally:
        cur.close()
        release_pg_connection(conn)

    # Start DB worker
    dbw = DBWorker()
    dbw.start()

    # Preload visited URLs and blocked domains
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT url FROM crawled_urls;")
        for (u,) in cur.fetchall():
            visited.add(u)
        cur.execute("SELECT domain FROM blocked_domains;")
        for (d,) in cur.fetchall():
            blocked_domains.add(d)
        conn.commit()
    finally:
        cur.close()
        release_pg_connection(conn)

    # Seed pending if empty
    conn = get_pg_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM pending_urls;")
        count = cur.fetchone()[0]
        if count == 0:
            for s in seed_urls:
                cur.execute(
                    "INSERT INTO pending_urls(url, depth) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                    (s, 0)
                )
            conn.commit()
            logger.info(f"Seeded {len(seed_urls)} initial URLs.")
    finally:
        cur.close()
        release_pg_connection(conn)

    batch = 1
    while not shutdown_event.is_set():
        # Fetch and delete batch
        conn = get_pg_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT url, depth FROM pending_urls LIMIT %s;", (max_threads,))
            rows = cur.fetchall()
            if not rows:
                logger.info("Pending queue empty. Crawl complete.")
                break

            urls = [(u, d) for (u, d) in rows]
            for u, _ in urls:
                cur.execute("DELETE FROM pending_urls WHERE url = %s;", (u,))
            conn.commit()
        finally:
            cur.close()
            release_pg_connection(conn)

        logger.info(f"Batch {batch}: {len(urls)} URLs")
        for u, _ in urls:
            logger.info(f"    → {u}")
        batch += 1

        # Crawl in parallel
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = {executor.submit(crawl_url, u, d): u for u, d in urls}
            for fut in futures:
                u = futures[fut]
                try:
                    fut.result()
                except Exception as e:
                    logger.error(f"Error on {u}: {e}")

    # Shutdown
    write_queue.put(_SENTINEL)
    dbw.join(timeout=30)
    global_session.close()
    db_pool.closeall()
    logger.info("DBWorker done, exiting.")
