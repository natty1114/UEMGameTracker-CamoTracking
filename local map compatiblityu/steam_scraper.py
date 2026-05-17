import re
import requests
from urllib.parse import urlparse, parse_qs

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}


def extract_steam_id(url):
    """Extract the Steam file ID from a workshop URL."""
    m = re.search(r'[?&]id=(\d+)', url)
    return m.group(1) if m else None


def fetch_workshop_page(url):
    """Fetch a Steam Workshop page HTML."""
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def extract_map_name(html):
    """Extract the map name from the workshop page (og:title or <title>)."""
    m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
    if m:
        return m.group(1).strip()
    m = re.search(r'<title>(.*?)</title>', html)
    if m:
        title = m.group(1).strip()
        title = re.sub(r'\s*::\s*Steam\s*Community\s*$', '', title, flags=re.IGNORECASE)
        return title.strip()
    return ''


def extract_authors(html):
    """Extract author names and profile URLs from the workshop page.

    Returns a list of dicts: [{'name': 'AuthorName', 'profile_url': 'https://...'}, ...]
    """
    authors = []
    # Match friendBlock entries: link overlay + name inside friendBlockContent
    pattern = re.compile(
        r'<a class="friendBlockLinkOverlay"\s*href="(https://steamcommunity\.com/(?:id|profiles)/[^"]+)"\s*>'
        r'\s*</a>.*?'
        r'<div class="friendBlockContent">\s*(.*?)\s*<br',
        re.DOTALL
    )
    for m in pattern.finditer(html):
        name = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if name:
            authors.append({'name': name, 'profile_url': m.group(1)})
    return authors


def get_workshop_info(url):
    """Fetch a Steam Workshop page and return map name + authors.

    Returns dict with keys: steam_id, map_name, authors, error
    """
    steam_id = extract_steam_id(url)
    try:
        html = fetch_workshop_page(url)
        map_name = extract_map_name(html)
        authors = extract_authors(html)
        return {
            'steam_id': steam_id,
            'map_name': map_name,
            'authors': authors,
            'author_str': ', '.join(a['name'] for a in authors),
            'error': None
        }
    except Exception as e:
        return {
            'steam_id': steam_id,
            'map_name': '',
            'authors': [],
            'author_str': '',
            'error': str(e)
        }
