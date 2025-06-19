#!/usr/bin/env python3
"""
seeds_dump.py

Pull all URLs from your PostgreSQL crawler database and save them
to seedslistauto.txt, using credentials from config.py.
"""

import sys
import psycopg2
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS

def main():
    # 1) Connect to Postgres
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
    except Exception as e:
        print(f"ERROR: Failed to connect to Postgres: {e}")
        sys.exit(1)

    # 2) Fetch all unique URLs from crawled_urls and pending_urls
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT url FROM crawled_urls
            UNION
            SELECT url FROM pending_urls;
        """)
        rows = cur.fetchall()
    except Exception as e:
        print(f"ERROR: Database query failed: {e}")
        conn.close()
        sys.exit(1)
    finally:
        conn.close()

    # 3) Write to seedslistauto.txt
    if not rows:
        print("No URLs found in database.")
        return

    try:
        with open("seedslistauto.txt", "w") as f:
            for (url,) in rows:
                f.write(f"{url}\n")
    except Exception as e:
        print(f"ERROR: Failed to write seedslistauto.txt: {e}")
        sys.exit(1)

    print(f"Wrote {len(rows)} URLs to seedslistauto.txt")

if __name__ == "__main__":
    main()
