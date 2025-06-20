
#!/usr/bin/env python3
"""
utils.py

Utility functions for the DarkNetCrawler to process web content.
"""

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from urllib.parse import urljoin, urlparse
import re
from collections import Counter
from config import MIN_TAGS, MAX_TAGS
import warnings

# Suppress XMLParsedAsHTMLWarning for HTML parsing
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

def is_xml_content(html):
    """Check if content is likely XML based on common XML tags or DOCTYPE."""
    html = html.strip().lower()[:1000]  # Limit check for performance
    return html.startswith('<?xml') or '<rss' in html or '<sitemap' in html or '<!doctype xml' in html

def extract_links(base_url, html):
    """Extract all valid links from HTML or XML content."""
    try:
        parser = 'xml' if is_xml_content(html) else 'lxml'
        soup = BeautifulSoup(html, parser)
        links = set()
        for tag in soup.find_all('a', href=True):
            href = tag['href']
            full_url = urljoin(base_url, href)
            if urlparse(full_url).scheme in ['http', 'https']:
                links.add(full_url)
        return links
    except Exception as e:
        return set()

def summarize_content(html):
    """Extract a summary from HTML or XML content."""
    try:
        parser = 'xml' if is_xml_content(html) else 'lxml'
        soup = BeautifulSoup(html, parser)
        text = soup.get_text(separator=' ', strip=True)
        return text[:200] or "No content"
    except Exception as e:
        return f"Error summarizing: {e}"

def extract_images(html):
    """Extract image URLs from HTML or XML content."""
    try:
        parser = 'xml' if is_xml_content(html) else 'lxml'
        soup = BeautifulSoup(html, parser)
        imgs = [img['src'] for img in soup.find_all('img', src=True)]
        return imgs[:5]
    except Exception as e:
        return []

def generate_tags(full_text, title=None, url=None):
    """
    Frequency-based tag extraction from the full page text + title + URL.
    Returns a list of between MIN_TAGS and MAX_TAGS tags.
    """
    try:
        combined = f"{title or ''} {full_text} {url or ''}".lower()
        words = re.findall(r'\b[a-z0-9]{4,20}\b', combined)
        blacklist = {
            "https", "http", "index", "about", "home", "search",
            "terms", "title", "www", "html", "com", "page", "site"
        }
        filtered = [w for w in words if w not in blacklist]
        freq = Counter(filtered)
        # Get up to MAX_TAGS most common
        tags = [w for w, _ in freq.most_common(MAX_TAGS)]
        # Return at least MIN_TAGS if available
        return tags[:max(MIN_TAGS, len(tags))]
    except Exception as e:
        return []
