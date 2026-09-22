"""
database.py - SQLite storage (Task 8)

Tables:
  pages : one row per crawled URL (including failed ones with status_code)
  links : one row per extracted hyperlink (source -> target)
"""

import os
import sqlite3

import config


class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or config.DB_PATH
        folder = os.path.dirname(self.db_path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    # ----------------------------------------------------------
    def create_tables(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT UNIQUE,
                domain      TEXT,
                title       TEXT,
                content     TEXT,
                depth       INTEGER,
                status_code INTEGER,
                crawled_at  TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url  TEXT,
                target_url  TEXT
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_url)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_url)")
        self.conn.commit()

    def reset(self):
        """Delete all data (used to start a fresh crawl)."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM links")
        cur.execute("DELETE FROM pages")
        cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('pages','links')")
        self.conn.commit()

    # ----------------------------------------------------------
    def save_page(self, page):
        """Insert (or replace) a page record (dict)."""
        self.conn.execute(
            """
            INSERT OR REPLACE INTO pages
                (url, domain, title, content, depth, status_code, crawled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                page["url"],
                page["domain"],
                page["title"],
                page["content"],
                page["depth"],
                page["status_code"],
                page["crawled_at"],
            ),
        )
        self.conn.commit()

    def save_links(self, source_url, target_urls):
        """Insert all links found on a page."""
        self.conn.executemany(
            "INSERT INTO links (source_url, target_url) VALUES (?, ?)",
            [(source_url, t) for t in target_urls],
        )
        self.conn.commit()

    # ----------------------------------------------------------
    # Statistics (computed from the database, not typed by hand)
    # ----------------------------------------------------------
    def count_pages(self):
        return self.conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]

    def count_links(self):
        return self.conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]

    def pages_per_depth(self):
        rows = self.conn.execute(
            "SELECT depth, COUNT(*) AS n FROM pages GROUP BY depth ORDER BY depth"
        ).fetchall()
        return {r["depth"]: r["n"] for r in rows}

    def pages_per_status(self):
        rows = self.conn.execute(
            "SELECT status_code, COUNT(*) AS n FROM pages "
            "GROUP BY status_code ORDER BY status_code"
        ).fetchall()
        return {r["status_code"]: r["n"] for r in rows}

    def pages_per_domain(self):
        rows = self.conn.execute(
            "SELECT domain, COUNT(*) AS n FROM pages GROUP BY domain ORDER BY n DESC"
        ).fetchall()
        return {r["domain"]: r["n"] for r in rows}

    def close(self):
        self.conn.close()
