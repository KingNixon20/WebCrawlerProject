#!/usr/bin/env python3
import sqlite3
import os
from database import get_connection

def load_seeds(seed_path="seeds.txt"):
    """
    Reads seeds.txt (one URL per line, ignoring blank lines and comments).
    Returns a list of seed URLs.
    """
    seeds = []
    try:
        with open(seed_path, "r") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                seeds.append(line)
    except FileNotFoundError:
        print(f"[WARN] {seed_path} not found. No seeds loaded.")
    return seeds

if __name__ == "__main__":
    seeds = load_seeds("seeds.txt")
    if not seeds:
        print("No seeds found in seeds.txt. Nothing to delete.")
        exit(0)

    conn = get_connection()
    c = conn.cursor()

    # Build a parameter list for the SQL IN clause
    placeholders = ",".join("?" for _ in seeds)
    sql = f"DELETE FROM crawled_urls WHERE url IN ({placeholders});"
    c.execute(sql, seeds)

    deleted = c.rowcount
    conn.commit()
    conn.close()

    print(f"✅ Removed {deleted} seed URL(s) from crawled_urls. Next crawl will re‐enqueue those seeds.")
