Web Crawler System README
This README provides instructions for setting up and operating the web crawler system, which consists of a Flask-based server (crawler_server.py), a worker script (crawler_worker.py), and a GUI control panel (crawler_gui.py). The system crawls websites, extracts data (title, summary, tags, and links), and stores it in a PostgreSQL database, with the server accessible at https://crawler.projectkryptos.xyz.
System Overview
The web crawler system is designed to:

Store URLs: Maintains a queue of URLs to crawl in a PostgreSQL database (crawl_queue table).
Crawl Websites: Workers fetch URLs, extract data using BeautifulSoup, and submit results to the server.
Manage Operations: A Tkinter GUI allows starting/stopping workers and setting the number of threads.
Secure Access: Godmode-privileged routes (/api/crawler/resume, /api/crawler/reset) require JWT authentication.

Components

Server (crawler_server.py): Runs a Flask API at https://crawler.projectkryptos.xyz/api/crawler with endpoints:
/api/health: Check server status.
/api/crawler/urls: Provide URLs for workers to crawl.
/api/crawler/submit: Accept crawled data.
/api/crawler/status: Show crawling statistics.
/api/crawler/resume: Re-queue recent URLs (godmode only).
/api/crawler/reset: Reset queue with seed URLs (godmode only).


Worker (crawler_worker.py): Fetches URLs, crawls pages, and submits data to the server.
GUI (crawler_gui.py): Controls workers, allowing users to set thread count and view logs.
Config (crawler_config.py): Stores database and JWT settings.
Seeds (seeds.txt): Initial URLs to crawl.

Prerequisites

Python 3.8+: Installed with Tkinter (included in standard Python for Windows/macOS; on Linux, install python3-tk).
PostgreSQL: Running with a database (e.g., kryptos) and valid credentials.
Dependencies: Install required Python packages:pip install flask flask-cors psycopg2-binary pyjwt requests beautifulsoup4


Directory Structure:X:\WebCrawlerProject\
  ├── crawler_server.py
  ├── crawler_config.py
  ├── crawler_worker.py
  ├── crawler_gui.py
  ├── seeds.txt



Setup

Create Configuration:

Create crawler_config.py in X:\WebCrawlerProject with:# crawler_config.py
DB_HOST = 'localhost'  # PostgreSQL host
DB_PORT = 5432         # PostgreSQL port
DB_NAME = 'kryptos'    # Database name
DB_USER = 'postgres'   # Database username
DB_PASS = 'your_password'  # Database password
JWT_SECRET = 'your_secure_random_string_32_chars'  # Generate with: python -c "import os; print(os.urandom(16).hex())"


Ensure JWT_SECRET matches your main app’s config.py for godmode token compatibility.


Set Up Seed URLs:

Create seeds.txt in X:\WebCrawlerProject with initial URLs, e.g.:https://example.com
https://wikipedia.org




Start PostgreSQL:

Ensure your PostgreSQL server is running and accessible with the credentials in crawler_config.py.
The users table (for godmode authentication) should exist, created by your main app (app.py).



Operating the Server

Navigate to Project Directory:
cd X:\WebCrawlerProject


Run the Server:
python crawler_server.py


The server starts at https://crawler.projectkryptos.xyz (assumes a reverse proxy like Nginx for HTTPS on port 443).
For local testing, it runs on http://localhost:5001. Update app.run(port=5001) if needed.
On startup, it creates webpages and crawl_queue tables and loads seeds.txt.


Verify Server:
curl https://crawler.projectkryptos.xyz/api/health

Expected output:
{"status": "healthy", "message": "Crawler API is running and database is accessible", "timestamp": "..."}



Starting the Crawler

Launch the GUI:
python crawler_gui.py


A window opens with:
Thread Count: Enter the number of worker threads (1–20, default: 2).
Start Crawler: Begins crawling with the specified threads.
Stop Crawler: Stops all workers.
Log Area: Displays real-time crawling logs.


Enter a thread count (e.g., 4), click “Start Crawler”, and monitor logs.
Click “Stop Crawler” to pause; close the window to exit.


Alternative: Run Workers Directly:
python crawler_worker.py


Starts 2 worker threads by default (edit start_workers(2, ...) to change).
Press Ctrl+C to stop.
Logs are saved to crawler_worker.log.


Monitor Progress:

Check server status:curl https://crawler.projectkryptos.xyz/api/crawler/status

Output: {"pending_urls": N, "processing_urls": M, "crawled_urls": P, ...}
View logs in crawler_worker.log or crawler_gui.log.
Query the database:SELECT COUNT(*) FROM webpages;
SELECT COUNT(*) FROM crawl_queue WHERE status = 'pending';





How It Works

Initialization:

The server (crawler_server.py) creates webpages (stores crawled data) and crawl_queue (manages URLs to crawl) tables.
Seed URLs from seeds.txt are loaded into crawl_queue with status = 'pending'.


Worker Operation:

Workers (crawler_worker.py) fetch up to 10 URLs from /api/crawler/urls, which marks them as processing.
For each URL, the worker:
Sends an HTTP request with a browser-like User-Agent.
Parses the page with BeautifulSoup.
Extracts title, summary (meta description or truncated body text), tags (from meta keywords), and links.
Submits data to /api/crawler/submit, which updates webpages and crawl_queue (sets status = 'completed').
Adds new links to crawl_queue.


Workers run in parallel threads, with delays (1–3s between crawls, 10–20s when no URLs) to avoid overload.


GUI Control:

The GUI (crawler_gui.py) lets you specify the number of worker threads.
Clicking “Start Crawler” launches threads via crawler_worker.py’s start_workers function.
Logs (e.g., “Crawling URL: https://example.com”) appear in the GUI and crawler_worker.log.
“Stop Crawler” halts all threads.


Godmode Routes:

/api/crawler/resume: Re-queues the last 10 crawled URLs (requires godmode JWT).
/api/crawler/reset: Clears crawl_queue and reloads seeds.txt (requires godmode JWT).
Get a godmode token from your main app’s /api/auth/login or /api/admin/users/<user_id>/privileges.



Troubleshooting

Server Not Responding:

Verify crawler_server.py is running and accessible:curl https://crawler.projectkryptos.xyz/api/health


Check SSL certificates for HTTPS. For testing, edit crawler_worker.py to use verify=False in requests.get/post (insecure).
Ensure crawler_config.py has correct database credentials.


No URLs to Crawl:

Check seeds.txt exists and contains valid URLs.
Reset the queue (requires godmode token):curl -X POST -H "Authorization: Bearer <godmode_token>" https://crawler.projectkryptos.xyz/api/crawler/reset




GUI Issues:

Ensure Tkinter is installed (python3-tk on Linux).
Check crawler_gui.log for errors.
If frozen, increase the log update interval in crawler_gui.py (root.after(100, ...) to 200).


Worker Errors:

Review crawler_worker.log for HTTP errors (e.g., 403, 429).
Update HEADERS in crawler_worker.py if sites block the User-Agent.
Share tracebacks for debugging.



Scaling

More Workers: Increase threads in the GUI or edit crawler_worker.py’s start_workers call.
Multiple Machines: Run crawler_gui.py or crawler_worker.py on different machines, pointing to https://crawler.projectkryptos.xyz.
Production: Use gunicorn for the server:pip install gunicorn
gunicorn --workers 4 --bind 0.0.0.0:443 crawler_server:app

Configure Nginx for HTTPS.

Contact
For issues, contact the project administrator or submit a ticket with:

Error tracebacks.
Contents of crawler_worker.log or crawler_gui.log.
Server responses (e.g., curl output).

