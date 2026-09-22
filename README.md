# Focused Web Crawler - Topic: Music

Assignment 1 - SEG301 (Crawls and Feeds)

A focused web crawler written in Python. It starts from seed URLs, discovers pages
by following hyperlinks with Breadth-First Search (BFS), stores the collected data in
SQLite, and prints crawling statistics.

## 1. Selected topic

**Topic:** Music (approved by the lecturer)

**Domain:** Nhac.vn (`nhac.vn`)

> Note: the assignment recommends at least 2 domains. Other Music domains were
> tested but could not be crawled: nhaccuatui.com renders content with
> JavaScript (only 4 static links found), and chiasenhac.vn could not be
> reached (connection failed). The lecturer approved using nhac.vn only.
 
## 2. Seed URLs

1. https://nhac.vn/

## 3. Crawling configuration

| Parameter        | Value      |
|------------------|------------|
| Maximum pages    | 300        |
| Maximum depth    | 3          |
| Request timeout  | 10 seconds |
| Crawl delay      | 1 second   |

**Why a 1-second delay?** Sending requests continuously can overload a website and
gets the crawler blocked. One second between requests is a polite rate for a small
educational crawl, while still finishing 300 pages in about 10 minutes.

All parameters are defined in `config.py`.

## 4. Crawling strategy

**Why BFS?** BFS visits all pages of depth *d* before any page of depth *d+1*.
For a focused crawl this gives a broad and balanced coverage of each website
(the home page, category pages, then song/artist pages) instead of going deep into a single
branch. It also makes the depth limit easy to enforce.

**How the URL Frontier works** (`url_frontier.py`):
- The frontier stores `(url, depth)` pairs in FIFO queues (`collections.deque`).
- `append` adds newly discovered URLs, `popleft` selects the next URL, so the
  oldest URL (lowest depth) is always crawled first: this is BFS.
- There is one queue per domain, and `next()` picks domains in round-robin order.
  This prevents one large domain from filling the whole frontier when several
  domains are crawled together. With a single domain (`nhac.vn`) it behaves exactly
  like one plain BFS queue.
- Seeds enter with depth 0; links found on a page of depth *d* get depth *d+1*.
- Links are added only if `depth + 1 <= MAX_DEPTH`.
- Three collections avoid duplicates: `in_frontier` (URLs waiting), `visited`
  (URLs already taken to be crawled) and `discovered` (all unique URLs ever accepted).
- URLs are normalized first (see below).

**Stopping conditions:** the crawl stops when `MAX_PAGES` is reached or the frontier
is empty.

**robots.txt:** for each domain, `robots.txt` is downloaded once (cached) and parsed
with `urllib.robotparser`. URLs disallowed for our User-Agent are skipped.

## 5. URL filtering rules

A discovered link is accepted only if **all** rules pass:

1. Relative URLs are converted to absolute URLs with `urljoin`.
2. Ignored schemes: `mailto:`, `javascript:`, `tel:`, `ftp:`, `sms:`, `data:`.
   Only `http` and `https` are accepted.
3. Ignored file types: images (`.jpg .png .gif .svg ...`), `.css`, `.js`,
   archives (`.zip ...`), documents (`.pdf ...`), audio/video, fonts.
4. **Domain rule:** the host must equal an allowed domain or be one of its subdomains
   (`www.example.com` and `sub.example.com` both match `example.com`).
   `facebook.com` and other external sites are rejected.
5. **Normalization:** the `#fragment` is removed, scheme/host are lowercased and the
   trailing slash is removed, so `/news/1`, `/news/1/` and `/news/1#top` are one URL.
6. **Duplicates:** URLs already visited or already waiting in the frontier are skipped.
7. **Depth:** links beyond `MAX_DEPTH` are not added.
8. **robots.txt:** disallowed URLs are skipped.

Only responses with status 200 and an HTML content type are parsed. Other responses
(404, 403, 500, ...) and failed requests (timeout, connection error) are recorded in
the database and the crawler continues.

## 6. Database design

File: `data/crawler.db` (SQLite)

**Table `pages`** - one row per crawled URL.

| Column        | Description                                              |
|---------------|----------------------------------------------------------|
| id            | Primary key                                              |
| url           | Page URL (UNIQUE)                                        |
| domain        | Website domain                                           |
| title         | Page title                                               |
| content       | Extracted visible text (no preprocessing yet)            |
| depth         | Crawl depth                                              |
| status_code   | HTTP status code (0 = no response: timeout/connection)   |
| crawled_at    | Crawl timestamp                                          |

**Table `links`** - one row per hyperlink (source -> target).

| Column      | Description                    |
|-------------|--------------------------------|
| id          | Primary key                    |
| source_url  | URL of the page with the link  |
| target_url  | Extracted target URL           |

`pages` holds the content that will be indexed in the next assignment. `links` stores
the web graph (which page links to which), useful for link analysis and for measuring
how many URLs were discovered.

## 7. Crawling results



```
========== CRAWLING SUMMARY ==========
Topic                  : Music
Seed URLs              : 1
Stop reason            : MAX_PAGES reached
Pages Crawled          : 300
Unique URLs Discovered : 3784
Skipped URLs           : 27344
Blocked by robots.txt  : 0
Failed Requests        : 0
Links stored           : 31127
Maximum Depth (config) : 3
Pages per depth:
  Depth 0 : 1 pages
  Depth 1 : 162 pages
  Depth 2 : 137 pages
Pages per domain:
  nhac.vn : 300
HTTP status:
  HTTP 200 : 300
=======================================
```

## 8. Analysis of the results (nhac.vn)

All numbers below come from `data/crawler.db` (SQL queries), not typed by hand.

**1. No page at depth 3.** `MAX_DEPTH` is 3, but the crawl stopped at depth 2.
The home page links to many category, chart and song pages, so depth 1 alone
contains 162 pages. Because BFS finishes one level before starting the next,
`MAX_PAGES = 300` was reached in the middle of depth 2 (137 pages), before any
depth-3 page was taken from the frontier.

**2. Very high duplicate rate.** 31,127 links were stored, but only 3,784 unique
URLs were discovered, and 27,344 links were skipped as duplicates. On average each
page contains about 104 links, and most of them are the same menu, header and
footer links. For example, `https://nhac.vn/` and `https://nhac.vn/album` appear on
298 different pages. Without the `visited` / `in_frontier` sets the crawler would
download the same pages again and again.

**3. What kind of pages were collected.** Crawled pages by URL section:
album 114, hot-list 60, bai-hat (songs) 48, nghe-si (artists) 37, video 18, and
a few chart pages (bang-xep-hang). The 3,784 discovered URLs have a similar mix
(nghe-si 1,056, album 902, bai-hat 855, video 559). So the content is on topic
(Music), and the site structure is: home -> category / chart -> album / song /
artist.

**4. The site is crawler-friendly.** All 300 pages returned HTTP 200, with no
failed request and nothing blocked by robots.txt. The HTML is rendered on the
server, so the links can be read directly with BeautifulSoup (no JavaScript needed).
The 300 pages took about 10 minutes (13:21 -> 13:32), about 2 seconds per page
including the 1-second delay, so the average response time was about 1 second.

**5. Page content.** Average extracted text length is about 3,400 characters per
page. Full song lyrics are removed before saving (copyright), so `content` keeps
titles, artist names, album descriptions and other page text.

**Problems encountered**

- **Choosing the domains:** nhaccuatui.com loads its content with JavaScript
  (only 4 static links found with `check_domain.py`), and chiasenhac.vn could not be
  reached (connection failed). This is why nhac.vn was used.
- **Some pages are not real music content:** a few crawled URLs are technical or
  account pages (`/auth`, `/xhrUser/...`, terms of use). They pass the domain rule
  because they are on nhac.vn. A path blacklist could remove them.
- **Query strings:** 425 discovered URLs contain `?` parameters (e.g. paging or
  sorting). They are kept because they can point to different content, but some of
  them may be near-duplicates of the same page.
- **Generic titles:** 12 pages have only the title "Nhac.vn", so the title alone is
  not always enough to describe a page; the `content` field is needed.

## How to run

```bash
pip install -r requirements.txt
python main.py
```

The database is created at `data/crawler.db`. Open it with "DB Browser for SQLite"
to inspect the `pages` and `links` tables.

## Project structure

```
assiment1/
├── main.py          # entry point
├── crawler.py       # BFS crawler, robots.txt, HTTP requests, statistics
├── url_frontier.py  # URL frontier, normalization, duplicate detection
├── parser.py        # page info extraction, link extraction and filtering
├── database.py      # SQLite tables and queries
├── config.py        # all crawling parameters
├── check_domain.py  # helper: check robots.txt and accessibility
├── data/crawler.db  # output database
├── requirements.txt
└── README.md
```
