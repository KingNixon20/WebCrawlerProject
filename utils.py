# utils.py
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from collections import Counter
from config import MIN_TAGS, MAX_TAGS

def extract_links(base_url, html):
    soup = BeautifulSoup(html, 'lxml')
    links = set()
    for tag in soup.find_all('a', href=True):
        href = tag['href']
        full_url = urljoin(base_url, href)
        if urlparse(full_url).scheme in ['http', 'https']:
            links.add(full_url)
    return links

def summarize_content(html):
    soup = BeautifulSoup(html, 'lxml')
    text = soup.get_text(separator=' ', strip=True)
    return text[:200]

def extract_images(html):
    soup = BeautifulSoup(html, 'lxml')
    imgs = [img['src'] for img in soup.find_all('img', src=True)]
    return imgs[:5]

def generate_tags(full_text, title=None, url=None):
    """
    Frequency-based tag extraction from the full page text + title + URL.
    Returns a list of between MIN_TAGS and MAX_TAGS tags.
    """
    combined = f"{title or ''} {full_text} {url or ''}".lower()
    words = re.findall(r'\b[a-z0-9]{4,20}\b', combined)
    blacklist = {
        "https", "http", "index", "about", "home", "search",
        "terms", "title", "www", "html", "com", "page", "site"
    }
    filtered = [w for w in words if w not in blacklist]
    freq = Counter(filtered)

    # get up to MAX_TAGS most common
    tags = [w for w, _ in freq.most_common(MAX_TAGS)]
    # if we have fewer than MIN_TAGS, we just return what we have
    return tags[:max(MIN_TAGS, len(tags))]
