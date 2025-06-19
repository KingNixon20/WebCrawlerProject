#!/usr/bin/env python3
"""
crawler.py

A multi‐threaded web crawler that indexes pages into PostgreSQL.
Uses psycopg2 and DB credentials from config.py.
"""

import threading
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import SSLError
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from time import sleep
from random import uniform
from queue import Queue, Empty
import urllib.robotparser as robotparser
import urllib3
import psycopg2

from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
from langdetect import detect
from utils import extract_links, summarize_content, extract_images, generate_tags

# Suppress InsecureRequestWarning when verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Globals ───────────────────────────────────────────────────────────────────
shutdown_event      = threading.Event()
USER_AGENT          = "DarkNetCrawler@projectkryptos.xyz"
respect_robots      = True
ignore_tos          = False

visited             = set()
visited_lock        = threading.Lock()

write_queue         = Queue()
_SENTINEL           = object()

robots_parsers      = {}
blocked_domains     = set()
tos_checked_domains = set()


def get_pg_connection():
    """Return a new psycopg2 connection to Postgres."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )


class DBWorker(threading.Thread):
    """Background thread that serializes all DB writes to Postgres."""
    def __init__(self):
        super().__init__(daemon=True)

    def run(self):
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

            if action == "record_visited":
                self._record_visited(payload)
            elif action == "enqueue_pending":
                self._enqueue_pending(payload)
            elif action == "dequeue_pending":
                self._dequeue_pending(payload)
            elif action == "save_page":
                self._save_page(payload)
            elif action == "record_language":
                self._record_language(payload)

            write_queue.task_done()

    def _record_visited(self, url):
        conn = get_pg_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO crawled_urls(url) VALUES (%s) ON CONFLICT DO NOTHING;",
                (url,)
            )
            conn.commit()
        finally:
            conn.close()

    def _enqueue_pending(self, url):
        conn = get_pg_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO pending_urls(url) VALUES (%s) ON CONFLICT DO NOTHING;",
                (url,)
            )
            conn.commit()
        finally:
            conn.close()

    def _dequeue_pending(self, url):
        conn = get_pg_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM pending_urls WHERE url = %s;",
                (url,)
            )
            conn.commit()
        finally:
            conn.close()

    def _save_page(self, payload):
        title, url, summary, tags, images_str = payload
        conn = get_pg_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO webpages (title, url, summary, timestamp, tags, images)
                VALUES (%s, %s, %s, NOW(), %s, %s)
                ON CONFLICT (url) DO NOTHING;
            """, (title, url, summary, tags, images_str))
            conn.commit()
        finally:
            conn.close()

    def _record_language(self, payload):
        url, lang = payload
        conn = get_pg_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO language (url, language)
                VALUES (%s, %s)
                ON CONFLICT (url) DO UPDATE SET language = EXCLUDED.language;
            """, (url, lang))
            conn.commit()
        finally:
            conn.close()


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
    if not respect_robots:
        return True
    parsed = urlparse(url)
    rp = get_robot_parser(parsed.netloc)
    return rp is None or rp.can_fetch(USER_AGENT, url)


def check_tos_for_domain(domain):
    if domain in tos_checked_domains:
        return
    tos_checked_domains.add(domain)
    for path in ("/terms", "/terms-of-service", "/tos", "/legal/terms"):
        try:
            r = requests.get(
                f"https://{domain}{path}",
                headers={"User-Agent": USER_AGENT},
                timeout=5
            )
            text = r.text.lower()
            if r.status_code == 200 and any(
                kw in text for kw in
                ("automated","robot","scrap","crawl","not allowed","disallow","unauthorized")
            ):
                blocked_domains.add(domain)
                print(f"[INFO] Disallowed by ToS: {domain}")
                return
        except Exception:
            continue


def ignore_robots_and_tos():
    """Disable robots.txt and ToS checks on the fly."""
    global respect_robots, ignore_tos, blocked_domains, tos_checked_domains, robots_parsers
    respect_robots = False
    ignore_tos     = True
    blocked_domains.clear()
    tos_checked_domains.clear()
    robots_parsers.clear()
    print("[INFO] Robots.txt and ToS checks disabled.")


def crawl_url(url):
    """Fetch a single URL, extract data, detect language, and enqueue new links."""
    if shutdown_event.is_set():
        return set()

    dom = urlparse(url).netloc
    if not is_allowed_by_robots(url):
        return set()

    if not ignore_tos and dom not in blocked_domains:
        check_tos_for_domain(dom)
        if dom in blocked_domains:
            return set()

    with visited_lock:
        if url in visited:
            return set()
        visited.add(url)

    sleep(uniform(0.1, 0.3))  # politeness delay

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    retry_args = dict(total=2, backoff_factor=1.0,
                      status_forcelist=[429,500,502,503,504])
    try:
        retry = Retry(**retry_args, allowed_methods=["GET"])
    except TypeError:
        retry = Retry(**retry_args, method_whitelist=["GET"])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    try:
        r = session.get(url, timeout=10)
    except SSLError:
        r = session.get(url, timeout=10, verify=False)

    if r.status_code != 200:
        write_queue.put(("dequeue_pending", url))
        return set()

    write_queue.put(("record_visited", url))
    write_queue.put(("dequeue_pending", url))

    html = r.text
    soup = BeautifulSoup(html, "html.parser")

    title   = soup.title.string.strip() if soup.title else url
    summary = summarize_content(html)
    tags    = ",".join(generate_tags(
                soup.get_text(" ", strip=True),
                title=title, url=url
             ))
    images  = extract_images(html)
    imgs    = ",".join(images)
    write_queue.put(("save_page", (title, url, summary, tags, imgs)))

    try:
        lang = detect(soup.get_text(" ", strip=True))
        write_queue.put(("record_language", (url, lang)))
    except Exception:
        pass

    links = extract_links(url, html)
    for link in links:
        write_queue.put(("enqueue_pending", link))

    return links


def run_crawler(seed_urls, max_threads=2):
    """Main entry point: ensure schema, seed URLs, and crawl until done."""
    # 1) Ensure tables exist
    conn = get_pg_connection()
    cur  = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS crawled_urls(url TEXT PRIMARY KEY);")
    cur.execute("CREATE TABLE IF NOT EXISTS pending_urls(url TEXT PRIMARY KEY);")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS webpages(
          title TEXT, url TEXT PRIMARY KEY, summary TEXT,
          timestamp TIMESTAMP DEFAULT NOW(), tags TEXT, images TEXT
        );
    """)
    cur.execute("CREATE TABLE IF NOT EXISTS language(url TEXT PRIMARY KEY, language TEXT);")
    conn.commit()
    conn.close()

    # 2) Start DB worker
    dbw = DBWorker()
    dbw.start()

    # 3) Preload visited URLs
    conn_v = get_pg_connection()
    cur_v  = conn_v.cursor()
    cur_v.execute("SELECT url FROM crawled_urls;")
    for (u,) in cur_v.fetchall():
        visited.add(u)
    conn_v.close()

    # 4) Seed pending if empty
    conn_p = get_pg_connection()
    cur_p  = conn_p.cursor()
    cur_p.execute("SELECT COUNT(*) FROM pending_urls;")
    count = cur_p.fetchone()[0]
    if count == 0:
        for s in seed_urls:
            cur_p.execute(
                "INSERT INTO pending_urls(url) VALUES (%s) ON CONFLICT DO NOTHING;", (s,)
            )
        conn_p.commit()
        print(f"[*] Seeded {len(seed_urls)} initial URLs.")
    conn_p.close()

    batch = 1
    while not shutdown_event.is_set():
        # --- fetch and eager-delete the batch ---
        conn_b = get_pg_connection()
        cur_b  = conn_b.cursor()
        cur_b.execute("SELECT url FROM pending_urls LIMIT %s;", (max_threads,))
        rows = cur_b.fetchall()
        if not rows:
            conn_b.close()
            print("[*] Pending queue empty. Crawl complete.")
            break

        # build URL list and remove them immediately
        urls = [u for (u,) in rows]
        for u in urls:
            cur_b.execute("DELETE FROM pending_urls WHERE url = %s;", (u,))
        conn_b.commit()
        conn_b.close()

        print(f"[*] Batch {batch}: {len(urls)} URLs")
        for u in urls:
            print(f"    → {u}")
        batch += 1

        # --- crawl them in parallel ---
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = {executor.submit(crawl_url, u): u for u in urls}
            for fut in futures:
                u = futures[fut]
                try:
                    fut.result()
                except Exception as e:
                    print(f"[!] Error on {u}: {e}")

    # 5) Shutdown
    write_queue.put(_SENTINEL)
    dbw.join(timeout=30)
    print("[*] DBWorker done, exiting.")
