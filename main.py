
#!/usr/bin/env python3
"""
main.py

GUI control for the DarkNetCrawler, using PostgreSQL and Tkinter.
"""

import os
import sys
import threading
import signal
import tkinter as tk
from queue import Queue, Empty
import builtins
import psycopg2
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS, THREADS
from crawler import run_crawler, shutdown_event, ignore_robots_and_tos
from database import setup_schema
import Crawled_Urls  # runs verify_or_rotate() on import

# ─── Override built-in print to also push logs into the GUI queue ────────────
log_queue = Queue()
original_print = builtins.print

def print(*args, **kwargs):
    text = " ".join(str(a) for a in args)
    original_print(text, **kwargs)
    log_queue.put(text)

# ─── Postgres connection helper ──────────────────────────────────────────────
def get_pg_connection():
    """Return a new psycopg2 connection to Postgres."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

# ─── GUI helper functions ─────────────────────────────────────────────────────
def load_seeds(seed_path="seeds.txt"):
    seeds = []
    try:
        with open(seed_path, "r") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                seeds.append(line)
        # Deduplicate seeds
        seeds = list(dict.fromkeys(seeds))
    except FileNotFoundError:
        print(f"[WARN] {seed_path} not found. No seeds loaded.")
    return seeds

# ─── GUI CALLBACKS ─────────────────────────────────────────────────────────────
crawler_thread = None

def on_start_button():
    global crawler_thread
    start_btn.config(state=tk.DISABLED)
    stop_btn.config(state=tk.NORMAL)

    print("[GUI] Starting crawler…")
    shutdown_event.clear()

    def target():
        # Test Postgres connectivity
        try:
            pg = get_pg_connection()
            print(f"[✔] Successfully connected to PostgreSQL at {DB_HOST}:{DB_PORT}")
            pg.close()
        except Exception as e:
            print(f"[✖] Failed to connect to PostgreSQL: {e}")
            sys.exit(1)

        print(f"[*] Using {THREADS} threads (from config.py)")
        initial_seeds = load_seeds(seed_path="seeds.txt")
        if not initial_seeds:
            print("[ERROR] No seeds found in seeds.txt. Exiting crawl.")
            return

        print("[*] Starting crawler with seeds:")
        for s in initial_seeds:
            print(f"    {s}")

        # Kick off the crawl
        run_crawler(initial_seeds, max_threads=THREADS)
        print("[GUI] Crawler thread has finished.")
        start_btn.config(state=tk.NORMAL)
        stop_btn.config(state=tk.DISABLED)

    crawler_thread = threading.Thread(target=target, daemon=True)
    crawler_thread.start()

def on_stop_button():
    stop_btn.config(state=tk.DISABLED)
    print("[GUI] Stop requested. Waiting for crawler to finish current batch...")
    shutdown_event.set()

def toggle_robots():
    if robots_var.get() == 1:
        print("[GUI] Now respecting robots.txt")
    else:
        ignore_robots_and_tos()
        print("[GUI] Now IGNORING robots.txt")

def poll_log_queue():
    while True:
        try:
            line = log_queue.get(block=False)
        except Empty:
            break
        text_widget.configure(state=tk.NORMAL)
        text_widget.insert(tk.END, line + "\n")
        text_widget.configure(state=tk.DISABLED)
        text_widget.yview(tk.END)
    root.after(200, poll_log_queue)

# ─── Signal Handling ──────────────────────────────────────────────────────────
def handle_shutdown(signum, frame):
    print("[*] Shutting down gracefully...")
    shutdown_event.set()
    root.quit()

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

# ─── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Ensure PostgreSQL schema
    setup_schema()

    # Build and start the GUI
    root = tk.Tk()
    root.title("DarkNetCrawler Control")
    root.geometry("800x600")

    controls_frame = tk.Frame(root)
    controls_frame.pack(fill=tk.X, padx=10, pady=5)

    start_btn = tk.Button(
        controls_frame, text="START", fg="white", bg="green",
        width=10, command=on_start_button
    )
    start_btn.pack(side=tk.LEFT, padx=(0, 10))

    stop_btn = tk.Button(
        controls_frame, text="STOP", fg="white", bg="red",
        width=10, command=on_stop_button, state=tk.DISABLED
    )
    stop_btn.pack(side=tk.LEFT)

    robots_var = tk.IntVar(value=1)
    robots_check = tk.Checkbutton(
        controls_frame,
        text="Respect robots.txt",
        variable=robots_var,
        command=toggle_robots
    )
    robots_check.pack(side=tk.LEFT, padx=(20, 0))

    log_frame = tk.Frame(root)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    text_widget = tk.Text(log_frame, wrap=tk.WORD, state=tk.DISABLED)
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(log_frame, command=text_widget.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    text_widget.config(yscrollcommand=scrollbar.set)

    root.after(200, poll_log_queue)
    root.mainloop()

    print("[*] Program exit.")
