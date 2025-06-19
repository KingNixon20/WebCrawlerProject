#!/usr/bin/env python3
import sqlite3
import os

def remove_exact_duplicates(db_path="web_index.db"):
    """
    Connects to the SQLite database at db_path, finds exact duplicate rows
    in `webpages` (rows where title, url, summary, timestamp, tags, and images
    are all identical), and deletes all but the one with the lowest id.

    Returns the number of rows deleted.
    """
    if not os.path.isfile(db_path):
        print(f"Database file not found at '{db_path}'.")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # First, count how many total rows we have
    c.execute("SELECT COUNT(*) FROM webpages;")
    total_before = c.fetchone()[0]

    # Delete duplicates: keep only the row with the smallest id for each unique
    # combination of (title, url, summary, timestamp, tags, images).
    delete_sql = """
    DELETE FROM webpages
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM webpages
        GROUP BY title, url, summary, timestamp, tags, images
    );
    """
    c.execute(delete_sql)
    deleted = c.rowcount  # number of rows deleted

    conn.commit()

    # Count how many rows remain
    c.execute("SELECT COUNT(*) FROM webpages;")
    total_after = c.fetchone()[0]

    conn.close()

    print(f"Total rows before: {total_before}")
    print(f"Total rows after:  {total_after}")
    print(f"Rows deleted:      {deleted}")

if __name__ == "__main__":
    # Adjust db_path if your web_index.db is in a different location
    db_path = os.path.join(os.path.dirname(__file__), "web_index.db")
    remove_exact_duplicates(db_path)
