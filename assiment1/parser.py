"""
parser.py - HTML parsing, page information and link extraction (Tasks 4, 5)
"""

from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

import config
from url_frontier import normalize_url, get_domain


# ---------------------------------------------------------------
# Task 4 - Extract page information
# ---------------------------------------------------------------
LYRIC_CONTAINER_HINTS = (
    "lyric", "lyrics", "loi-bai-hat", "loibaihat", "song-lyric",
)


def _remove_lyric_blocks(soup):
    """Remove elements whose class/id suggests they hold full song lyrics."""
    targets = []
    for tag in soup.find_all(["div", "section", "article", "p", "pre"]):
        class_list = tag.get("class") or []
        tag_id = tag.get("id") or ""
        attr_text = (" ".join(class_list) + " " + tag_id).lower()
        if any(hint in attr_text for hint in LYRIC_CONTAINER_HINTS):
            targets.append(tag)

    for tag in targets:
        if tag.parent is not None:  # skip if an ancestor was already removed
            tag.decompose()


def extract_page_info(soup, url, depth, status_code):
    """
    Build a structured page record from a parsed HTML page.
    No text preprocessing (tokenization, stopwords, ...) is done here.

    Copyright note: full song lyrics are not stored. Any element that
    looks like a lyrics block (by class/id) is removed before the page
    text is extracted, so 'content' only keeps titles, artist names,
    descriptions and other surrounding page text.
    """
    # Title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.get_text(strip=True)
    elif soup.find("h1"):
        title = soup.find("h1").get_text(strip=True)

    # Remove script/style/noscript and any lyrics container
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    _remove_lyric_blocks(soup)

    content = soup.get_text(separator=" ", strip=True)
    content = content[: config.MAX_CONTENT_LENGTH]

    return {
        "url": url,
        "domain": get_domain(url),
        "title": title,
        "content": content,
        "depth": depth,
        "status_code": status_code,
        "crawled_at": datetime.now().isoformat(timespec="seconds"),
    }


# ---------------------------------------------------------------
# Task 5 - URL filtering
# ---------------------------------------------------------------
def is_allowed_domain(url):
    """
    Domain rule:
      host == allowed_domain  OR  host ends with '.' + allowed_domain
    So www.example.com and sub.example.com are accepted for 'example.com'.
    """
    host = urlparse(url).netloc.lower().split(":")[0]
    for domain in config.ALLOWED_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return True
    return False


def has_ignored_extension(url):
    path = urlparse(url).path.lower()
    return path.endswith(config.IGNORED_EXTENSIONS)


def is_valid_url(url):
    """Return True if the URL should be considered for crawling."""
    parsed = urlparse(url)

    # protocol must be http / https
    if parsed.scheme not in ("http", "https"):
        return False

    # must have a host
    if not parsed.netloc:
        return False

    # non-web resources (images, css, js, zip ...)
    if has_ignored_extension(url):
        return False

    # must belong to the allowed domains
    if not is_allowed_domain(url):
        return False

    return True


def extract_links(soup, current_url):
    """
    Extract all <a href> links, convert relative URLs to absolute URLs,
    and keep only valid ones. Returns a list of unique normalized URLs.
    """
    valid_links = []
    seen = set()

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith("#"):
            continue

        # ignore mailto:, javascript:, tel: ...
        lowered = href.lower()
        if lowered.startswith(tuple(s + ":" for s in config.IGNORED_SCHEMES)):
            continue

        absolute_url = urljoin(current_url, href)

        if not is_valid_url(absolute_url):
            continue

        normalized = normalize_url(absolute_url)
        if normalized not in seen:
            seen.add(normalized)
            valid_links.append(normalized)

    return valid_links
