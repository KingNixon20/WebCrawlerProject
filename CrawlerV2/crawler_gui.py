import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import logging
from crawler_worker import start_workers, log_queue, worker_thread, MAX_THREADS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('crawler_gui.log')
    ]
)
logger = logging.getLogger(__name__)

class CrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Web Crawler Control Panel")
        self.root.geometry("800x600")
        
        self.stop_event = threading.Event()
        self.threads = []
        self.is_running = False
        
        # GUI Elements
        self.create_widgets()
        
        # Start log update loop
        self.update_logs()

    def create_widgets(self):
        """Create GUI widgets."""
        # Thread count input
        tk.Label(self.root, text=f"Number of Threads (Max {MAX_THREADS}):").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.thread_count = tk.Spinbox(self.root, from_=1, to=MAX_THREADS, width=5)
        self.thread_count.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.thread_count.delete(0, "end")
        self.thread_count.insert(0, "2")  # Default to 2 threads
        
        # Control buttons
        self.start_button = tk.Button(self.root, text="Start Crawler", command=self.start_crawler)
        self.start_button.grid(row=0, column=2, padx=5, pady=5)
        
        self.stop_button = tk.Button(self.root, text="Stop Crawler", command=self.stop_crawler, state="disabled")
        self.stop_button.grid(row=0, column=3, padx=5, pady=5)
        
        # Log display
        tk.Label(self.root, text="Crawler Logs:").grid(row=1, column=0, padx=5, pady=5, sticky="nw")
        self.log_text = tk.Text(self.root, height=25, width=90, state="disabled")
        self.log_text.grid(row=2, column=0, columnspan=4, padx=5, pady=5)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=2, column=4, sticky="ns")
        self.log_text['yscrollcommand'] = scrollbar.set

    def start_crawler(self):
        """Start the crawler with the specified number of threads."""
        if self.is_running:
            messagebox.showwarning("Warning", "Crawler is already running!")
            return
        
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
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"Starting crawler with {num_threads} threads...\n")
        self.log_text.config(state="disabled")
        
        self.threads = start_workers(num_threads, self.stop_event)
        logger.info(f"GUI: Started {num_threads} worker threads")

    def stop_crawler(self):
        """Stop the crawler."""
        if not self.is_running:
            messagebox.showwarning("Warning", "Crawler is not running!")
            return
        
        self.is_running = False
        self.stop_event.set()
        for thread in self.threads:
            thread.join()
        self.threads = []
        self.stop_event.clear()
        
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.log_text.config(state="normal")
        self.log_text.insert("end", "Crawler stopped.\n")
        self.log_text.config(state="disabled")
        logger.info("GUI: Stopped crawler")

    def update_logs(self):
        """Update the log display with messages from the queue."""
        try:
            while not log_queue.empty():
                msg = log_queue.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert("end", f"{msg}\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self.update_logs)

    def on_closing(self):
        """Handle window closing."""
        if self.is_running:
            self.stop_crawler()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = CrawlerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()