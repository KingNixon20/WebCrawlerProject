import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
import random
import threading
import queue
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
from urllib.robotparser import RobotFileParser
import multiprocessing
import psutil

# Check NLTK resources
try:
    nltk.data.find('tokenizers/punkt_tab')
    nltk.data.find('corpora/stopwords')
except LookupError:
    print("[!] NLTK resources missing. Downloading punkt_tab and stopwords...")
    try:
        nltk.download('punkt_tab', quiet=True)
        nltk.download('stopwords', quiet=True)
    except Exception as e:
        print(f"[!] Failed to download NLTK resources: {e}")
        raise SystemExit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('crawler_worker.log')
    ]
)
logger = logging.getLogger(__name__)

# Cache stop words
STOP_WORDS = set(stopwords.words('english'))

# Maximum threads based on CPU count
MAX_THREADS = multiprocessing.cpu_count()
logger.info(f"Detected {MAX_THREADS} CPU cores; maximum thread count set to {MAX_THREADS}")

# Crawler server API configuration
API_BASE_URL = 'https://crawler.projectkryptos.xyz/api/crawler'
FETCH_URLS_ENDPOINT = f'{API_BASE_URL}/urls'
SUBMIT_DATA_ENDPOINT = f'{API_BASE_URL}/submit'
RESET_ENDPOINT = f'{API_BASE_URL}/reset'

# Request headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Shared queue for GUI communication
log_queue = queue.Queue()

# HTTP session with retries
session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retries)
session.mount('http://', adapter)
session.mount('https://', adapter)

# Rate limit tracking
domain_delays = {}

def get_crawl_delay(url):
    """Get crawl delay from robots.txt."""
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        delay = rp.crawl_delay(HEADERS['User-Agent']) or 1.0
        logger.debug(f"Crawl delay for {url}: {delay}s")
        return delay
    except Exception as e:
        logger.warning(f"Error checking robots.txt for {url}: {e}")
        return 1.0

def can_crawl(url):
    """Check if URL is allowed by robots.txt."""
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        can_fetch = rp.can_fetch(HEADERS['User-Agent'], url)
        logger.debug(f"robots.txt check for {url}: {'Allowed' if can_fetch else 'Disallowed'}")
        return can_fetch
    except Exception as e:
        logger.warning(f"Error checking robots.txt for {url}: {e}")
        log_queue.put(f"Error checking robots.txt for {url}: {e}")
        return True

def respect_rate_limit(url):
    """Enforce crawl delay for the domain."""
    domain = urlparse(url).netloc
    delay = get_crawl_delay(url)
    last_crawled = domain_delays.get(domain, 0)
    current_time = time.time()
    if current_time - last_crawled < delay:
        sleep_time = delay - (current_time - last_crawled)
        time.sleep(sleep_time)
    domain_delays[domain] = time.time()

def generate_summary(text, max_length=200):
    """Generate a summary for page content."""
    words = text.split()[:max_length]
    summary = ' '.join(words)
    if len(text.split()) > max_length:
        summary += '...'
    return summary

def score_tag(tag, soup):
    """Score tag based on relevance."""
    score = 0
    tag_lower = tag.lower()
    meta_tags = soup.find_all('meta', {'name': ['keywords', 'tags']})
    for meta in meta_tags:
        if meta.get('content') and tag_lower in meta.get('content').lower():
            score += 5
    headers = soup.find_all(['h1', 'h2'])
    for header in headers:
        if tag_lower in header.get_text(strip=True).lower():
            score += 3
    body_text = soup.get_text(strip=True).lower()
    score += body_text.count(tag_lower)
    return score

def generate_tags(soup, max_tags=40, min_tags=20):
    """Extract 20–40 tags using NLTK, with quality scoring."""
    start_time = time.time()
    tags = []
    meta_tags = soup.find_all('meta', {'name': ['keywords', 'tags']})
    for tag in meta_tags:
        if tag.get('content'):
            tags.extend([t.strip().lower() for t in tag.get('content').split(',') if t.strip()])
    header_tags = soup.find_all(['h1', 'h2'])
    for tag in header_tags:
        text = tag.get_text(strip=True)
        tokens = word_tokenize(text.lower())
        tags.extend([t for t in tokens if t.isalnum() and len(t) > 2])
    body_text = soup.get_text(separator=' ', strip=True)
    tokens = word_tokenize(body_text.lower())
    keywords = [t for t in tokens if t.isalnum() and t not in STOP_WORDS and len(t) > 2]
    tag_scores = {tag: score_tag(tag, soup) for tag in set(tags + keywords)}
    sorted_tags = sorted(tag_scores.items(), key=lambda x: x[1], reverse=True)
    selected_tags = [tag for tag, _ in sorted_tags[:max_tags]]
    if len(selected_tags) < min_tags:
        additional_keywords = [t for t in keywords if t not in selected_tags][:min_tags - len(selected_tags)]
        selected_tags.extend(additional_keywords)
    if len(selected_tags) < min_tags:
        generic_keywords = [t for t in tokens if t.isalnum() and len(t) > 2][:min_tags - len(selected_tags)]
        selected_tags.extend(generic_keywords)
    selected_tags = list(dict.fromkeys(selected_tags))[:max_tags]
    logger.info(f"Generated {len(selected_tags)} tags in {time.time() - start_time:.2f}s")
    if len(selected_tags) < min_tags:
        logger.warning(f"Failed to generate {min_tags} tags; only {len(selected_tags)} generated")
    return ','.join(selected_tags[:max_tags])

def extract_urls(soup, base_url):
    """Extract URLs from the page."""
    urls = set()
    for link in soup.find_all('a', href=True):
        href = link['href']
        absolute_url = urljoin(base_url, href)
        parsed = urlparse(absolute_url)
        if parsed.scheme in ['http', 'https']:
            urls.add(absolute_url)
    return list(urls)

def crawl_url(url):
    """Crawl a single URL and extract data."""
    start_time = time.time()
    logger.info(f"Starting crawl for {url}")
    if not can_crawl(url):
        logger.warning(f"URL {url} disallowed by robots.txt")
        log_queue.put(f"URL {url} disallowed by robots.txt")
        return None
    
    respect_rate_limit(url)
    
    try:
        response = session.get(url, headers=HEADERS, timeout=10, verify=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('title')
        title = title_tag.text.strip() if title_tag else ''
        summary = ''
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            summary = meta_desc.get('content').strip()
        else:
            body_text = soup.get_text(separator=' ', strip=True)
            summary = generate_summary(body_text)
        tags = generate_tags(soup)
        tag_count = len(tags.split(',')) if tags else 0
        if tag_count < 20:
            logger.warning(f"URL {url} generated only {tag_count} tags, expected at least 20")
        new_urls = extract_urls(soup, url)
        logger.info(f"Completed crawl for {url}: {tag_count} tags, {len(new_urls)} new URLs in {time.time() - start_time:.2f}s")
        return {
            'url': url,
            'title': title,
            'summary': summary,
            'tags': tags,
            'new_urls': new_urls
        }
    except (requests.exceptions.SSLError, ssl.SSLError) as e:
        logger.warning(f"SSL/TLS error for {url}: {e}")
        log_queue.put(f"SSL/TLS error for {url}: {e}")
        try:
            response = session.get(url, headers=HEADERS, timeout=10, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            title_tag = soup.find('title')
            title = title_tag.text.strip() if title_tag else ''
            summary = ''
            meta_desc = soup.find('meta', {'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                summary = meta_desc.get('content').strip()
            else:
                body_text = soup.get_text(separator=' ', strip=True)
                summary = generate_summary(body_text)
            tags = generate_tags(soup)
            tag_count = len(tags.split(',')) if tags else 0
            if tag_count < 20:
                logger.warning(f"URL {url} generated only {tag_count} tags in fallback, expected at least 20")
            new_urls = extract_urls(soup, url)
            logger.info(f"Completed fallback crawl for {url}: {tag_count} tags, {len(new_urls)} new URLs in {time.time() - start_time:.2f}s")
            return {
                'url': url,
                'title': title,
                'summary': summary,
                'tags': tags,
                'new_urls': new_urls
            }
        except Exception as e:
            logger.error(f"Fallback crawl failed for {url}: {e}")
            log_queue.put(f"Fallback crawl failed for {url}: {e}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {url}: {e}")
        log_queue.put(f"Request error for {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error crawling {url}: {e}")
        log_queue.put(f"Unexpected error crawling {url}: {e}")
        return None

def fetch_urls(max_retries=3):
    """Fetch URLs to crawl from the server."""
    start_time = time.time()
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching URLs (attempt {attempt+1}/{max_retries})")
            response = session.get(FETCH_URLS_ENDPOINT, timeout=10, verify=True)
            response.raise_for_status()
            data = response.json()
            urls = data.get('urls', [])
            logger.info(f"Fetched {len(urls)} URLs in {time.time() - start_time:.2f}s")
            if not urls and attempt == max_retries - 1:
                logger.warning("No URLs available after retries; requesting reset")
                try:
                    session.post(RESET_ENDPOINT, timeout=10)
                    logger.info("Requested crawler reset")
                except Exception as e:
                    logger.error(f"Failed to request reset: {e}")
            return urls
        except (requests.exceptions.SSLError, ssl.SSLError) as e:
            logger.warning(f"SSL/TLS error fetching URLs: {e}")
            log_queue.put(f"SSL/TLS error fetching URLs: {e}")
            try:
                response = session.get(FETCH_URLS_ENDPOINT, timeout=10, verify=False)
                response.raise_for_status()
                data = response.json()
                urls = data.get('urls', [])
                logger.info(f"Fetched {len(urls)} URLs in fallback in {time.time() - start_time:.2f}s")
                return urls
            except Exception as e:
                logger.error(f"Fallback fetch failed: {e}")
                log_queue.put(f"Fallback fetch failed: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching URLs: {e}")
            log_queue.put(f"Error fetching URLs: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching URLs: {e}")
            log_queue.put(f"Unexpected error fetching URLs: {e}")
        time.sleep(2 ** attempt)
    logger.error(f"Failed to fetch URLs after retries in {time.time() - start_time:.2f}s")
    return []

def submit_crawl_data(data, max_retries=3):
    """Submit crawled data to the server."""
    start_time = time.time()
    for attempt in range(max_retries):
        try:
            logger.info(f"Submitting data for {data['url']} (attempt {attempt+1}/{max_retries})")
            tag_count = len(data['tags'].split(',')) if data['tags'] else 0
            if tag_count < 20:
                logger.error(f"Data for {data['url']} has only {tag_count} tags; not submitting")
                log_queue.put(f"Data for {data['url']} has only {tag_count} tags; not submitting")
                return False
            response = session.post(SUBMIT_DATA_ENDPOINT, json=data, timeout=10, verify=True)
            response.raise_for_status()
            logger.info(f"Submitted data for {data['url']} in {time.time() - start_time:.2f}s: {response.json().get('message')}")
            log_queue.put(f"Submitted data for {data['url']}")
            return True
        except (requests.exceptions.SSLError, ssl.SSLError) as e:
            logger.warning(f"SSL/TLS error submitting data for {data['url']}: {e}")
            log_queue.put(f"SSL/TLS error submitting data for {data['url']}: {e}")
            try:
                response = session.post(SUBMIT_DATA_ENDPOINT, json=data, timeout=10, verify=False)
                response.raise_for_status()
                logger.info(f"Submitted data for {data['url']} in fallback in {time.time() - start_time:.2f}s")
                log_queue.put(f"Submitted data for {data['url']} in fallback")
                return True
            except Exception as e:
                logger.error(f"Fallback submit failed for {data['url']}: {e}")
                log_queue.put(f"Fallback submit failed for {data['url']}: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error submitting data for {data['url']}: {e}")
            log_queue.put(f"Error submitting data for {data['url']}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error submitting data for {data['url']}: {e}")
            log_queue.put(f"Unexpected error submitting data for {data['url']}: {e}")
        time.sleep(2 ** attempt)
    logger.error(f"Failed to submit data for {data['url']} after retries in {time.time() - start_time:.2f}s")
    return False

def worker_thread(stop_event):
    """Worker thread function."""
    process = psutil.Process()
    while not stop_event.is_set():
        try:
            start_time = time.time()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            logger.info(f"Worker memory usage: {memory_mb:.2f} MB")
            urls = fetch_urls()
            if not urls:
                logger.info(f"No URLs to crawl, waiting... (worker cycle: {time.time() - start_time:.2f}s)")
                log_queue.put("No URLs to crawl, waiting...")
                time.sleep(random.uniform(5, 10))
                continue
            
            for url in urls:
                if stop_event.is_set():
                    break
                data = crawl_url(url)
                if data:
                    if submit_crawl_data(data):
                        logger.info(f"Successfully processed {url} in {time.time() - start_time:.2f}s")
                    else:
                        logger.error(f"Failed to submit data for {url}")
                else:
                    logger.error(f"Failed to crawl {url}")
                time.sleep(random.uniform(0.5, 2))
            
        except Exception as e:
            logger.error(f"Worker error: {e}")
            log_queue.put(f"Worker error: {e}")
            time.sleep(5)

def start_workers(num_threads, stop_event):
    """Start the specified number of worker threads."""
    num_threads = min(num_threads, MAX_THREADS)
    logger.info(f"Starting {num_threads} crawler worker threads (capped at {MAX_THREADS})")
    log_queue.put(f"Starting {num_threads} crawler worker threads (capped at {MAX_THREADS})")
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=worker_thread, args=(stop_event,), name=f"Worker-{i+1}")
        thread.daemon = True
        thread.start()
        threads.append(thread)
    return threads

if __name__ == '__main__':
    stop_event = threading.Event()
    threads = start_workers(4, stop_event)  # Fallback default
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down workers")
        stop_event.set()
        for thread in threads:
            thread.join()
    finally:
        session.close()