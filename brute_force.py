import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import summarize_content, generate_tags
from database import save_page, init_db
from config import THREADS

TLDs = ['.com', '.net', '.org', '.us', '.xyz', '.io', '.co']
PROTOCOLS = ['http://', 'https://']
WWW_PREFIXES = ['', 'www.']
tried_urls = set()

def run_bruteforcer(dummy_conn=None, wordlist_file="wordlist.txt"):
    with open(wordlist_file, "r") as f:
        words = [line.strip().lower() for line in f if line.strip()]

    domain_variants = []
    for word in words:
        for tld in TLDs:
            base = f"{word}{tld}"
            for protocol in PROTOCOLS:
                for prefix in WWW_PREFIXES:
                    url = protocol + prefix + base
                    if url not in tried_urls:
                        tried_urls.add(url)
                        domain_variants.append(url)

    print(f"[*] Generated {len(domain_variants)} combinations for brute-forcing...")

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = [executor.submit(test_domain, url) for url in domain_variants]
        for future in as_completed(futures):
            _ = future.result()

def test_domain(url):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200 or "text/html" not in r.headers.get("Content-Type", ""):
            return

        html = r.text
        soup = BeautifulSoup(html, 'lxml')

        # Extract real <title>
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else urlparse(url).netloc
        if title.lower() in ("home", "index", "untitled"):
            title = urlparse(url).netloc

        summary = summarize_content(html)
        tags = generate_tags(summary, title=title, url=url)

        print(f"[+] Found site: {url}")
        conn = init_db()
        save_page(conn, title, url, summary, tags)
        conn.close()

    except Exception:
        pass
