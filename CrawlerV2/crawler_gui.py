import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import logging
import requests
from PIL import Image, ImageTk
from crawler_worker import start_workers, log_queue, MAX_THREADS
import time
import json
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('crawler_gui.log')
    ]
)
logger = logging.getLogger(__name__)

# Default API configuration
DEFAULT_API_BASE_URL = 'http://localhost:5001/api/crawler'
CONFIG_FILE = 'crawler_config.json'

class CrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Web Crawler Control Panel")
        self.root.geometry("900x700")
        self.root.configure(bg="#2E2E2E")
        start_time = time.time()
        logger.debug("Initializing CrawlerGUI")
        
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.threads = []
        self.is_running = False
        self.is_paused = False
        self.api_base_url = DEFAULT_API_BASE_URL
        self.jwt_token = None
        self.status_queue = queue.Queue()
        self.log_buffer = []
        self.blacklist_retry_scheduled = False
        
        # Load background image
        try:
            bg_image = Image.open('bg.png')
            self.bg_photo = ImageTk.PhotoImage(bg_image)
            self.bg_label = tk.Label(self.root, image=self.bg_photo)
            self.bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)
            logger.debug("Background image bg.png loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load background image bg.png: {e}")
            messagebox.showwarning("Warning", f"Failed to load background image: {e}")
        
        # Start status update thread
        self.status_thread = threading.Thread(target=self._fetch_status, daemon=True)
        self.status_thread.start()
        
        # GUI Elements
        self.create_widgets()
        
        # Load saved configuration
        self.load_config()
        
        # Start log and status update loops
        self.update_logs()
        self.update_status_display()
        # Schedule blacklist update to avoid blocking
        self.root.after(100, self.update_blacklist_display)
        logger.debug(f"GUI initialization completed in {time.time() - start_time:.2f} seconds")

    def create_widgets(self):
        """Create GUI widgets with themed styling."""
        start_time = time.time()
        logger.debug("Creating GUI widgets")
        bg_color = "#2E2E2E"
        fg_color = "#FFFFFF"
        accent_color = "#4A90E2"
        entry_bg = "#3C3C3C"
        text_bg = "#1E1E1E"

        main_frame = tk.Frame(self.root, bg=bg_color, bd=2, relief="flat")
        main_frame.place(relx=0.05, rely=0.05, relwidth=0.9, relheight=0.9)
        logger.debug("Main frame created")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", background=accent_color, foreground=fg_color, font=("Helvetica", 10, "bold"), padding=5)
        style.map("TButton", background=[("active", "#357ABD")], foreground=[("active", fg_color)])
        style.configure("TSpinbox", background=entry_bg, foreground=fg_color, fieldbackground=entry_bg, font=("Helvetica", 10))
        style.configure("TLabel", background=bg_color, foreground=fg_color, font=("Helvetica", 10))
        style.configure("TEntry", fieldbackground=entry_bg, foreground=fg_color, font=("Helvetica", 10))
        style.configure("TCheckbutton", background=bg_color, foreground=fg_color, font=("Helvetica", 10))
        style.configure("TListbox", background=text_bg, foreground=fg_color, font=("Courier", 9))
        logger.debug("TTK styles configured")

        # Configuration section
        tk.Label(main_frame, text="Configuration:", bg=bg_color, fg=fg_color, font=("Helvetica", 12, "bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        
        # API Base URL
        tk.Label(main_frame, text="API Base URL:", bg=bg_color, fg=fg_color).grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.api_url_entry = ttk.Entry(main_frame, width=40, style="TEntry", state="normal")
        self.api_url_entry.grid(row=1, column=1, columnspan=3, padx=10, pady=5, sticky="w")
        self.api_url_entry.insert(0, DEFAULT_API_BASE_URL)
        logger.debug(f"API URL entry created, state: {self.api_url_entry['state']}")
        
        # JWT Token
        tk.Label(main_frame, text="JWT Token:", bg=bg_color, fg=fg_color).grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.jwt_entry = ttk.Entry(main_frame, width=40, style="TEntry", state="normal")
        self.jwt_entry.grid(row=2, column=1, columnspan=3, padx=10, pady=5, sticky="w")
        logger.debug(f"JWT token entry created, state: {self.jwt_entry['state']}")
        
        # Deduplication toggle
        self.dedupe_var = tk.BooleanVar(value=True)
        self.dedupe_check = ttk.Checkbutton(main_frame, text="Enable Deduplication", variable=self.dedupe_var, style="TCheckbutton")
        self.dedupe_check.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        logger.debug("Deduplication checkbox created")
        
        # Deduplication interval
        tk.Label(main_frame, text="Dedupe Interval (min):", bg=bg_color, fg=fg_color).grid(row=3, column=2, padx=10, pady=5, sticky="e")
        self.dedupe_interval = ttk.Spinbox(main_frame, from_=1, to=60, width=5, style="TSpinbox")
        self.dedupe_interval.grid(row=3, column=3, padx=10, pady=5, sticky="w")
        self.dedupe_interval.delete(0, "end")
        self.dedupe_interval.insert(0, "10")
        logger.debug("Deduplication interval spinbox created")
        
        # Config buttons
        self.apply_config_button = ttk.Button(main_frame, text="Apply Config", command=self.apply_config, style="TButton")
        self.apply_config_button.grid(row=4, column=0, padx=10, pady=10)
        logger.debug("Apply config button created")
        
        self.save_config_button = ttk.Button(main_frame, text="Save Config", command=self.save_config, style="TButton")
        self.save_config_button.grid(row=4, column=1, padx=10, pady=10)
        logger.debug("Save config button created")
        
        self.load_config_button = ttk.Button(main_frame, text="Load Config", command=self.load_config, style="TButton")
        self.load_config_button.grid(row=4, column=2, padx=10, pady=10)
        logger.debug("Load config button created")

        # Control section
        tk.Label(main_frame, text="Crawler Control:", bg=bg_color, fg=fg_color, font=("Helvetica", 12, "bold")).grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        
        # Thread count
        tk.Label(main_frame, text=f"Number of Threads (Max {MAX_THREADS}):", bg=bg_color, fg=fg_color).grid(row=6, column=0, padx=10, pady=5, sticky="e")
        self.thread_count = ttk.Spinbox(main_frame, from_=1, to=MAX_THREADS, width=5, style="TSpinbox")
        self.thread_count.grid(row=6, column=1, padx=10, pady=5, sticky="w")
        self.thread_count.delete(0, "end")
        self.thread_count.insert(0, "2")
        logger.debug("Thread count spinbox created")
        
        # Control buttons
        self.start_button = ttk.Button(main_frame, text="Start Crawler", command=self.start_crawler, style="TButton")
        self.start_button.grid(row=6, column=2, padx=10, pady=5)
        logger.debug("Start button created")
        
        self.stop_button = ttk.Button(main_frame, text="Stop Crawler", command=self.stop_crawler, style="TButton", state="disabled")
        self.stop_button.grid(row=6, column=3, padx=10, pady=5)
        logger.debug("Stop button created")
        
        self.pause_button = ttk.Button(main_frame, text="Pause Crawler", command=self.toggle_pause, style="TButton", state="disabled")
        self.pause_button.grid(row=6, column=4, padx=10, pady=5)
        logger.debug("Pause button created")

        # Domain control section
        tk.Label(main_frame, text="Domain Control:", bg=bg_color, fg=fg_color, font=("Helvetica", 12, "bold")).grid(row=7, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        
        # Skip domain
        self.skip_button = ttk.Button(main_frame, text="Skip Current Domain", command=self.skip_domain, style="TButton", state="disabled")
        self.skip_button.grid(row=8, column=0, padx=10, pady=5)
        logger.debug("Skip domain button created")
        
        # Blacklist domain
        tk.Label(main_frame, text="Blacklist Domain:", bg=bg_color, fg=fg_color).grid(row=8, column=1, padx=10, pady=5, sticky="e")
        self.blacklist_entry = ttk.Entry(main_frame, width=20, style="TEntry", state="normal")
        self.blacklist_entry.grid(row=8, column=2, padx=10, pady=5)
        logger.debug(f"Blacklist domain entry created, state: {self.blacklist_entry['state']}")
        self.blacklist_button = ttk.Button(main_frame, text="Blacklist", command=self.blacklist_domain, style="TButton")
        self.blacklist_button.grid(row=8, column=3, padx=10, pady=5)
        logger.debug("Blacklist domain button created")

        # Blacklist display
        tk.Label(main_frame, text="Blacklisted Domains:", bg=bg_color, fg=fg_color).grid(row=9, column=0, padx=10, pady=5, sticky="nw")
        self.blacklist_listbox = tk.Listbox(main_frame, height=5, width=40, bg=text_bg, fg=fg_color, font=("Courier", 9))
        self.blacklist_listbox.grid(row=10, column=0, columnspan=3, padx=10, pady=5, sticky="w")
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.blacklist_listbox.yview)
        scrollbar.grid(row=10, column=3, sticky="ns")
        self.blacklist_listbox['yscrollcommand'] = scrollbar.set
        logger.debug("Blacklist listbox and scrollbar created")
        
        # Un-blacklist button
        self.unblacklist_button = ttk.Button(main_frame, text="Un-blacklist Selected", command=self.unblacklist_domain, style="TButton")
        self.unblacklist_button.grid(row=10, column=4, padx=10, pady=5)
        logger.debug("Un-blacklist button created")

        # Clear logs
        self.clear_logs_button = ttk.Button(main_frame, text="Clear Logs", command=self.clear_logs, style="TButton")
        self.clear_logs_button.grid(row=8, column=4, padx=10, pady=5)
        logger.debug("Clear logs button created")

        # Status display
        tk.Label(main_frame, text="Crawler Status:", bg=bg_color, fg=fg_color, font=("Helvetica", 12, "bold")).grid(row=11, column=0, padx=10, pady=10, sticky="nw")
        self.status_text = tk.Text(main_frame, height=3, width=90, bg=text_bg, fg=fg_color, font=("Courier", 9), state="disabled", relief="flat", borderwidth=2)
        self.status_text.grid(row=12, column=0, columnspan=5, padx=10, pady=5)
        logger.debug("Status text created")

        # Log display
        tk.Label(main_frame, text="Crawler Logs:", bg=bg_color, fg=fg_color, font=("Helvetica", 12, "bold")).grid(row=13, column=0, padx=10, pady=10, sticky="nw")
        self.log_text = tk.Text(main_frame, height=10, width=90, bg=text_bg, fg=fg_color, font=("Courier", 9), state="disabled", relief="flat", borderwidth=2)
        self.log_text.grid(row=14, column=0, columnspan=5, padx=10, pady=5)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=14, column=5, sticky="ns")
        self.log_text['yscrollcommand'] = scrollbar.set
        logger.debug("Log text and scrollbar created")
        logger.debug(f"Widget creation completed in {time.time() - start_time:.2f} seconds")

    def save_config(self):
        """Save API Base URL and JWT Token to a config file."""
        logger.debug("Saving configuration to file")
        try:
            config = {
                'api_base_url': self.api_url_entry.get().strip(),
                'jwt_token': self.jwt_entry.get().strip()
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            messagebox.showinfo("Success", f"Configuration saved to {CONFIG_FILE}")
            logger.info(f"Configuration saved to {CONFIG_FILE}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {str(e)}")
            logger.error(f"Failed to save config to {CONFIG_FILE}: {e}")

    def load_config(self):
        """Load API Base URL and JWT Token from a config file."""
        logger.debug("Loading configuration from file")
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                self.api_url_entry.delete(0, tk.END)
                self.api_url_entry.insert(0, config.get('api_base_url', DEFAULT_API_BASE_URL))
                self.jwt_entry.delete(0, tk.END)
                self.jwt_entry.insert(0, config.get('jwt_token', ''))
                self.api_base_url = self.api_url_entry.get().strip()
                self.jwt_token = self.jwt_entry.get().strip()
                # Update API endpoints
                global SKIP_DOMAIN_ENDPOINT, BLACKLIST_DOMAIN_ENDPOINT, BLACKLIST_LIST_ENDPOINT
                global UNBLACKLIST_DOMAIN_ENDPOINT, STATUS_ENDPOINT, CONFIG_ENDPOINT
                SKIP_DOMAIN_ENDPOINT = f'{self.api_base_url}/skip_domain'
                BLACKLIST_DOMAIN_ENDPOINT = f'{self.api_base_url}/blacklist_domain'
                BLACKLIST_LIST_ENDPOINT = f'{self.api_base_url}/blacklist'
                UNBLACKLIST_DOMAIN_ENDPOINT = f'{self.api_base_url}/unblacklist_domain'
                STATUS_ENDPOINT = f'{self.api_base_url}/status'
                CONFIG_ENDPOINT = f'{self.api_base_url}/config'
                logger.info(f"Configuration loaded from {CONFIG_FILE}: api_base_url={self.api_base_url}")
            else:
                logger.debug(f"No config file found at {CONFIG_FILE}; using defaults")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {str(e)}")
            logger.error(f"Failed to load config from {CONFIG_FILE}: {e}")

    def _fetch_status(self):
        """Fetch status in a separate thread to avoid blocking GUI."""
        while not self.stop_event.is_set():
            if self.is_running and not self.is_paused:
                try:
                    headers = {"Authorization": f"Bearer {self.jwt_token}"} if self.jwt_token else {}
                    response = requests.get(STATUS_ENDPOINT, headers=headers, timeout=3)
                    response.raise_for_status()
                    data = response.json()
                    status = (
                        f"Pending URLs: {data.get('pending_urls', 0)}\n"
                        f"Processing URLs: {data.get('processing_urls', 0)}\n"
                        f"Crawled URLs: {data.get('crawled_urls', 0)}"
                    )
                    self.status_queue.put(status)
                except requests.exceptions.HTTPError as e:
                    self.status_queue.put(f"Status update failed: HTTP {e.response.status_code}")
                    logger.error(f"Status fetch failed: {e}")
                except Exception as e:
                    self.status_queue.put(f"Status update failed: {str(e)}")
                    logger.error(f"Status fetch failed: {e}")
            else:
                self.status_queue.put("Crawler is stopped.\n")
            threading.Event().wait(10)

    def update_status_display(self):
        """Update status display from status queue."""
        try:
            while not self.status_queue.empty():
                status = self.status_queue.get_nowait()
                self.status_text.config(state="normal")
                self.status_text.delete("1.0", tk.END)
                self.status_text.insert("end", status)
                self.status_text.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(500, self.update_status_display)

    def update_logs(self):
        """Update log display with buffered messages."""
        try:
            while not log_queue.empty():
                msg = log_queue.get_nowait()
                self.log_buffer.append(f"{msg}\n")
            if self.log_buffer:
                self.log_text.config(state="normal")
                self.log_text.insert("end", "".join(self.log_buffer[:100]))
                self.log_buffer = self.log_buffer[100:]
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        except Exception as e:
            logger.error(f"Log update error: {e}")
        self.root.after(500, self.update_logs)

    def update_blacklist_display(self):
        """Update the blacklist listbox with current blacklisted domains."""
        self.blacklist_retry_scheduled = False
        try:
            headers = {"Authorization": f"Bearer {self.jwt_token}"} if self.jwt_token else {}
            response = requests.get(BLACKLIST_LIST_ENDPOINT, headers=headers, timeout=3)
            response.raise_for_status()
            domains = response.json().get('domains', [])
            self.blacklist_listbox.delete(0, tk.END)
            for domain in domains:
                self.blacklist_listbox.insert(tk.END, domain)
            logger.debug("Updated blacklist display")
        except requests.exceptions.HTTPError as e:
            messagebox.showerror("Error", f"Failed to fetch blacklist: HTTP {e.response.status_code}")
            logger.error(f"Blacklist fetch failed: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch blacklist: {str(e)}")
            logger.error(f"Blacklist fetch failed: {e}")
        finally:
            if not self.blacklist_retry_scheduled:
                self.blacklist_retry_scheduled = True
                self.root.after(300000, self.update_blacklist_display)

    def apply_config(self):
        """Apply configuration settings and save to file."""
        logger.debug("Applying configuration")
        try:
            new_api_url = self.api_url_entry.get().strip()
            if not new_api_url:
                messagebox.showerror("Error", "API Base URL cannot be empty")
                return
            self.api_base_url = new_api_url.rstrip('/')
            global SKIP_DOMAIN_ENDPOINT, BLACKLIST_DOMAIN_ENDPOINT, BLACKLIST_LIST_ENDPOINT
            global UNBLACKLIST_DOMAIN_ENDPOINT, STATUS_ENDPOINT, CONFIG_ENDPOINT
            SKIP_DOMAIN_ENDPOINT = f'{self.api_base_url}/skip_domain'
            BLACKLIST_DOMAIN_ENDPOINT = f'{self.api_base_url}/blacklist_domain'
            BLACKLIST_LIST_ENDPOINT = f'{self.api_base_url}/blacklist'
            UNBLACKLIST_DOMAIN_ENDPOINT = f'{self.api_base_url}/unblacklist_domain'
            STATUS_ENDPOINT = f'{self.api_base_url}/status'
            CONFIG_ENDPOINT = f'{self.api_base_url}/config'
            logger.info(f"Updated API endpoints to base URL: {self.api_base_url}")

            self.jwt_token = self.jwt_entry.get().strip()
            if not self.jwt_token:
                messagebox.showwarning("Warning", "No JWT token provided; some features may not work")
                logger.warning("No JWT token provided")

            dedupe_enabled = self.dedupe_var.get()
            dedupe_interval = int(self.dedupe_interval.get()) * 60
            headers = {"Authorization": f"Bearer {self.jwt_token}"} if self.jwt_token else {}
            response = requests.post(
                CONFIG_ENDPOINT,
                json={"dedupe_enabled": dedupe_enabled, "dedupe_interval": dedupe_interval},
                headers=headers,
                timeout=3
            )
            response.raise_for_status()
            self.save_config()  # Save config after successful application
            messagebox.showinfo("Success", "Configuration applied and saved successfully")
            logger.info("Configuration applied: dedupe_enabled=%s, dedupe_interval=%s", dedupe_enabled, dedupe_interval)
        except ValueError:
            messagebox.showerror("Error", "Invalid deduplication interval")
            logger.error("Invalid deduplication interval")
        except requests.exceptions.HTTPError as e:
            messagebox.showerror("Error", f"Failed to apply config: HTTP {e.response.status_code}")
            logger.error(f"Config apply failed: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply config: {str(e)}")
            logger.error(f"Config apply failed: {e}")

    def start_crawler(self):
        """Start the crawler with the specified number of threads."""
        logger.debug("Starting crawler")
        if self.is_running:
            messagebox.showwarning("Warning", "Crawler is already running!")
            return
        
        if not self.jwt_token:
            messagebox.showwarning("Warning", "No JWT token provided. Blacklist checks may fail.")
            logger.warning("Starting crawler without JWT token; blacklist checks may fail.")
        
        try:
            num_threads = int(self.thread_count.get())
            if num_threads < 1 or num_threads > MAX_THREADS:
                messagebox.showerror("Error", f"Number of threads must be between 1 and {MAX_THREADS}")
                return
        except ValueError:
            messagebox.showerror("Error", "Invalid number of threads")
            return
        
        self.is_running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.pause_button.config(state="normal")
        self.skip_button.config(state="normal")
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"Starting crawler with {num_threads} threads using API: {self.api_base_url}\n")
        self.log_text.config(state="disabled")
        
        self.threads = start_workers(num_threads, self.stop_event, self.pause_event, api_base_url=self.api_base_url, jwt_token=self.jwt_token)
        logger.info(f"GUI: Started {num_threads} worker threads with API: {self.api_base_url}")
        self.update_blacklist_display()

    def stop_crawler(self):
        """Stop the crawler."""
        logger.debug("Stopping crawler")
        if not self.is_running:
            messagebox.showwarning("Warning", "Crawler is not running!")
            return
        
        self.is_running = False
        self.is_paused = False
        self.stop_event.set()
        for thread in self.threads:
            thread.join()
        self.threads = []
        self.stop_event.clear()
        self.pause_event.clear()
        
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.pause_button.config(state="disabled")
        self.pause_button.configure(text="Pause Crawler")
        self.skip_button.config(state="disabled")
        self.log_text.config(state="normal")
        self.log_text.insert("end", "Crawler stopped.\n")
        self.log_text.config(state="disabled")
        logger.info("GUI: Stopped crawler")

    def toggle_pause(self):
        """Pause or resume the crawler."""
        logger.debug("Toggling pause state")
        if not self.is_running:
            messagebox.showwarning("Warning", "Crawler is not running!")
            return
        
        if self.is_paused:
            self.is_paused = False
            self.pause_event.clear()
            self.pause_button.configure(text="Pause Crawler")
            self.log_text.config(state="normal")
            self.log_text.insert("end", "Crawler resumed.\n")
            self.log_text.config(state="disabled")
            logger.info("GUI: Crawler resumed")
        else:
            self.is_paused = True
            self.pause_event.set()
            self.pause_button.configure(text="Resume Crawler")
            self.log_text.config(state="normal")
            self.log_text.insert("end", "Crawler paused.\n")
            self.log_text.config(state="disabled")
            logger.info("GUI: Crawler paused")

    def skip_domain(self):
        """Skip the current domain being crawled."""
        logger.debug("Skipping current domain")
        if not self.is_running:
            messagebox.showwarning("Warning", "Crawler is not running!")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.jwt_token}"} if self.jwt_token else {}
            response = requests.post(SKIP_DOMAIN_ENDPOINT, headers=headers, timeout=3)
            response.raise_for_status()
            message = response.json().get('message', 'Domain skipped')
            self.log_text.config(state="normal")
            self.log_text.insert("end", f"{message}\n")
            self.log_text.config(state="disabled")
            logger.info(f"GUI: {message}")
        except requests.exceptions.HTTPError as e:
            messagebox.showerror("Error", f"Failed to skip domain: HTTP {e.response.status_code}")
            logger.error(f"Skip domain failed: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to skip domain: {str(e)}")
            logger.error(f"Skip domain failed: {e}")

    def blacklist_domain(self):
        """Blacklist a domain to prevent crawling."""
        logger.debug("Blacklisting domain")
        domain = self.blacklist_entry.get().strip()
        if not domain:
            messagebox.showwarning("Warning", "Please enter a domain to blacklist!")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.jwt_token}"} if self.jwt_token else {}
            response = requests.post(BLACKLIST_DOMAIN_ENDPOINT, json={'domain': domain}, headers=headers, timeout=3)
            response.raise_for_status()
            message = response.json().get('message', f"Domain {domain} blacklisted")
            self.log_text.config(state="normal")
            self.log_text.insert("end", f"{message}\n")
            self.log_text.config(state="disabled")
            self.blacklist_entry.delete(0, tk.END)
            self.update_blacklist_display()  # Immediate update
            self.clear_blacklisted_urls(domain)  # Clear URLs for the blacklisted domain
            logger.info(f"GUI: {message}")
        except requests.exceptions.HTTPError as e:
            messagebox.showerror("Error", f"Failed to blacklist domain: HTTP {e.response.status_code}")
            logger.error(f"Blacklist domain failed: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to blacklist domain: {str(e)}")
            logger.error(f"Blacklist domain failed: {e}")

    def clear_blacklisted_urls(self, domain):
        """Clear URLs for a blacklisted domain from crawl_queue."""
        logger.debug(f"Clearing blacklisted URLs for {domain}")
        try:
            headers = {"Authorization": f"Bearer {self.jwt_token}"} if self.jwt_token else {}
            response = requests.post(f'{self.api_base_url}/clear_blacklisted_urls', json={'domain': domain}, headers=headers, timeout=3)
            response.raise_for_status()
            message = response.json().get('message', f"Cleared blacklisted URLs for {domain}")
            self.log_text.config(state="normal")
            self.log_text.insert("end", f"{message}\n")
            self.log_text.config(state="disabled")
            logger.info(f"GUI: {message}")
        except requests.exceptions.HTTPError as e:
            messagebox.showerror("Error", f"Failed to clear blacklisted URLs for {domain}: HTTP {e.response.status_code}")
            logger.error(f"Clear blacklisted URLs failed: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear blacklisted URLs for {domain}: {str(e)}")
            logger.error(f"Clear blacklisted URLs failed: {e}")

    def unblacklist_domain(self):
        """Un-blacklist selected domain."""
        logger.debug("Un-blacklisting domain")
        selected = self.blacklist_listbox.curselection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a domain to un-blacklist!")
            return
        
        domain = self.blacklist_listbox.get(selected[0])
        try:
            headers = {"Authorization": f"Bearer {self.jwt_token}"} if self.jwt_token else {}
            response = requests.post(UNBLACKLIST_DOMAIN_ENDPOINT, json={'domain': domain}, headers=headers, timeout=3)
            response.raise_for_status()
            message = response.json().get('message', f"Domain {domain} un-blacklisted")
            self.log_text.config(state="normal")
            self.log_text.insert("end", f"{message}\n")
            self.log_text.config(state="disabled")
            self.update_blacklist_display()
            logger.info(f"GUI: {message}")
        except requests.exceptions.HTTPError as e:
            messagebox.showerror("Error", f"Failed to un-blacklist domain: HTTP {e.response.status_code}")
            logger.error(f"Un-blacklist domain failed: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to un-blacklist domain: {str(e)}")
            logger.error(f"Un-blacklist domain failed: {e}")

    def clear_logs(self):
        """Clear the log display."""
        logger.debug("Clearing logs")
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_buffer = []
        self.log_text.config(state="disabled")
        logger.info("GUI: Cleared logs")

    def on_closing(self):
        """Handle window closing."""
        logger.debug("Closing GUI")
        if self.is_running:
            self.stop_crawler()
        self.root.destroy()

if __name__ == '__main__':
    logger.debug("Starting GUI application")
    try:
        root = tk.Tk()
        app = CrawlerGUI(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
    except Exception as e:
        logger.error(f"GUI startup error: {e}")
        print(f"Failed to start GUI: {str(e)}")