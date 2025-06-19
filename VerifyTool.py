#!/usr/bin/env python3
import sqlite3
import os
import shutil

# Path to your SQLite database
DB_PATH = os.path.abspath(os.path.join(os.getcwd(), "web_index.db"))
BAK_PATH = os.path.abspath(os.path.join(os.getcwd(), "web_index.bak.db"))

def verify_or_rotate():
    """
    If web_index.db exists, run PRAGMA integrity_check.
    If the result isn’t “ok,” rename web_index.db → web_index.bak.db
    so a fresh DB will be created on next startup.
    """
    if not os.path.exists(DB_PATH):
        # No DB to check
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        res = cursor.fetchone()
        conn.close()

        if res[0].lower() != "ok":
            print(f"[WARN] integrity_check failed: {res[0]}")
            if os.path.exists(BAK_PATH):
                os.remove(BAK_PATH)
            shutil.move(DB_PATH, BAK_PATH)
            print(f"[INFO] Rotated corrupt DB to: {BAK_PATH}")
        else:
            # Integrity OK
            pass
    except sqlite3.DatabaseError as e:
        # If we can’t even do integrity_check, rotate anyway
        print(f"[ERROR] integrity_check error: {e}")
        if os.path.exists(BAK_PATH):
            os.remove(BAK_PATH)
        shutil.move(DB_PATH, BAK_PATH)
        print(f"[INFO] Rotated corrupt DB to: {BAK_PATH}")

if __name__ == "__main__":
    verify_or_rotate()
