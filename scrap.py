# -*- coding: utf-8 -*-
import sys, io, logging, time, random, traceback, hashlib, re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from contextlib import contextmanager
from datetime import datetime, timedelta

from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

import mysql.connector
from mysql.connector import Error, OperationalError, InterfaceError
from mysql.connector.pooling import MySQLConnectionPool

# ---------- UTF-8 LOGGING ----------
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("betexplorer_scraper.log", encoding="utf-8"),
    ],
)

BASE_URL = "https://www.betexplorer.com/?year=2026&month=01&day=07"

# ---------- SETTINGS ----------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "betexplorer",
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
}

POOL_NAME = "betexplorer_pool"
POOL_SIZE = 6

SCRAPER_CONFIG = {
    "max_retries": 3,
    "retry_delay": 2,
    "page_timeout": 60000,
    "selector_timeout": 20000,
    "scroll_times": 20,
    "scroll_pause": 2,
    "user_agents": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    ],
}

# ---------- DATA CLASSES ----------
@dataclass
class Match:
    home_team: str
    away_team: str
    match_date: Optional[str]
    match_time: Optional[str] 
    odds: Dict[str, str]
    match_url: Optional[str]

# ---------- HELPERS ----------
def safe_text(el) -> str:
    try:
        return el.get_text(strip=True) if el else ""
    except Exception:
        return ""

def _is_valid_odds(odds_str: str) -> bool:
    try:
        float(str(odds_str).replace(",", "."))
        return True
    except Exception:
        return False

def parse_match_datetime(date_element, time_element=None) -> Tuple[Optional[str], Optional[str]]:
    """Extract and normalize match date and time from elements."""
    match_date = None
    match_time = None
    
    if date_element:
        date_text = safe_text(date_element).strip()
        
        # Handle various date formats
        if date_text:
            # Today/Tomorrow/Yesterday patterns
            if date_text.lower() in ['today', 'heute', 'aujourd\'hui']:
                match_date = datetime.now().strftime('%Y-%m-%d')
            elif date_text.lower() in ['tomorrow', 'morgen', 'demain']:
                match_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            elif date_text.lower() in ['yesterday', 'gestern', 'hier']:
                match_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                # Try to parse various date formats
                date_patterns = [
                    r'(\d{1,2})\.(\d{1,2})\.(\d{4})',  # DD.MM.YYYY
                    r'(\d{1,2})/(\d{1,2})/(\d{4})',   # DD/MM/YYYY or MM/DD/YYYY
                    r'(\d{4})-(\d{1,2})-(\d{1,2})',   # YYYY-MM-DD
                    r'(\d{1,2})\s+(\w+)\s+(\d{4})',   # DD Month YYYY
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, date_text)
                    if match:
                        try:
                            if '.' in date_text:  # European format DD.MM.YYYY
                                day, month, year = match.groups()
                                match_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                            elif '/' in date_text:  # Could be DD/MM/YYYY or MM/DD/YYYY
                                # Assume DD/MM/YYYY for European sites
                                day, month, year = match.groups()
                                match_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                            elif '-' in date_text:  # YYYY-MM-DD
                                year, month, day = match.groups()
                                match_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                            break
                        except Exception:
                            continue
    
    # Extract time
    if time_element:
        time_text = safe_text(time_element).strip()
    else:
        # Try to extract time from date text if it contains time
        time_text = safe_text(date_element) if date_element else ""
    
    if time_text:
        # Look for time patterns (HH:MM)
        time_match = re.search(r'(\d{1,2}):(\d{2})', time_text)
        if time_match:
            hours, minutes = time_match.groups()
            match_time = f"{hours.zfill(2)}:{minutes}"
    
    return match_date, match_time

def extract_odds(container) -> Dict[str, str]:
    odds = {"home": "--", "draw": "--", "away": "--"}
    try:
        for sel in [
            ".table-main__oddsLi button",
            ".table-main__odds button",
            ".odds-cell button",
            ".odds-value",
        ]:
            btns = container.select(sel)
            if len(btns) >= 3:
                cand = [safe_text(btns[0]), safe_text(btns[1]), safe_text(btns[2])]
                for k, v in zip(["home", "draw", "away"], cand):
                    odds[k] = v if _is_valid_odds(v) else "--"
                break
    except Exception as e:
        logging.warning(f"Failed to extract odds: {e}")
    return odds

def random_delay(a=0.5, b=1.8):
    time.sleep(random.uniform(a, b))

def sha_key(home: str, away: str, date: str, url: Optional[str]) -> str:
    base = f"{(home or '').lower().strip()}|{(away or '').lower().strip()}|{(date or '').strip()}|{(url or '').lower().strip()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

# ---------- DB POOL & UTIL ----------
_pool: Optional[MySQLConnectionPool] = None

def init_pool():
    global _pool
    if _pool is None:
        _pool = MySQLConnectionPool(
            pool_name=POOL_NAME,
            pool_size=POOL_SIZE,
            **DB_CONFIG
        )
        logging.info("✅ MySQL connection pool initialized")

@contextmanager
def db_conn():
    """Get pooled connection with autocommit off."""
    init_pool()
    conn = None
    try:
        conn = _pool.get_connection()
        conn.autocommit = False
        yield conn
    finally:
        try:
            if conn and conn.is_connected():
                conn.close()
        except Exception:
            pass

def db_retry(fn):
    """Retry wrapper for DB operations; auto-reconnect on dropped connections."""
    def wrapper(*args, **kwargs):
        attempts = SCRAPER_CONFIG["max_retries"]
        delay = SCRAPER_CONFIG["retry_delay"]
        last = None
        for i in range(attempts):
            try:
                return fn(*args, **kwargs)
            except (OperationalError, InterfaceError) as e:
                last = e
                logging.warning(f"DB op failed ({e}); retry {i+1}/{attempts} in {delay*(i+1):.1f}s...")
                time.sleep(delay * (i + 1))
            except Error as e:
                last = e
                logging.error(f"MySQL error: {e}")
                if i == attempts - 1:
                    raise
                time.sleep(delay * (i + 1))
        raise last
    return wrapper

@db_retry
def init_db():
    with db_conn() as conn:
        cur = conn.cursor()
        # Enhanced matches table with date and time fields
        cur.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INT AUTO_INCREMENT PRIMARY KEY,
            match_key CHAR(64) NOT NULL UNIQUE,
            home_team VARCHAR(100) NOT NULL,
            away_team VARCHAR(100) NOT NULL,
            match_date DATE DEFAULT NULL,
            match_time TIME DEFAULT NULL,
            home_odds VARCHAR(10) DEFAULT '--',
            draw_odds VARCHAR(10) DEFAULT '--',
            away_odds VARCHAR(10) DEFAULT '--',
            match_url VARCHAR(255),
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_teams (home_team, away_team),
            INDEX idx_match_date (match_date),
            INDEX idx_match_datetime (match_date, match_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS h2h_matches (
            id INT AUTO_INCREMENT PRIMARY KEY,
            match_id INT NOT NULL,
            date VARCHAR(50),
            home_team VARCHAR(100),
            away_team VARCHAR(100),
            score VARCHAR(20),
            home_odds VARCHAR(10) DEFAULT '--',
            draw_odds VARCHAR(10) DEFAULT '--',
            away_odds VARCHAR(10) DEFAULT '--',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
            INDEX idx_match_id (match_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS standings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            match_id INT NOT NULL,
            team VARCHAR(100) NOT NULL,
            rank VARCHAR(10) DEFAULT '0',
            mp VARCHAR(5) DEFAULT '0',
            wins VARCHAR(5) DEFAULT '0',
            draws VARCHAR(5) DEFAULT '0',
            losses VARCHAR(5) DEFAULT '0',
            goals VARCHAR(10) DEFAULT '0:0',
            gd VARCHAR(5) DEFAULT '0',
            pts VARCHAR(5) DEFAULT '0',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
            INDEX idx_match_id (match_id),
            INDEX idx_team (team)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        conn.commit()
        logging.info("✅ Database schema ready")

@db_retry
def match_exists(conn, home_team: str, away_team: str, match_date: Optional[str], match_url: Optional[str]) -> bool:
    """Check if a match already exists in the database."""
    cur = conn.cursor()
    mkey = sha_key(home_team, away_team, match_date or "", match_url)
    
    cur.execute("SELECT id FROM matches WHERE match_key = %s", (mkey,))
    result = cur.fetchone()
    return result is not None

@db_retry
def upsert_match(conn, match: Dict) -> int:
    """UPSERT match; return match_id (existing or new)."""
    cur = conn.cursor()
    mkey = sha_key(match["home_team"], match["away_team"], match.get("match_date", ""), match.get("match_url"))
    
    # Parse date and time for database storage
    match_date_sql = match.get("match_date") if match.get("match_date") else None
    match_time_sql = match.get("match_time") if match.get("match_time") else None
    
    sql = """
    INSERT INTO matches (match_key, home_team, away_team, match_date, match_time, home_odds, draw_odds, away_odds, match_url)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    ON DUPLICATE KEY UPDATE
        home_team=VALUES(home_team),
        away_team=VALUES(away_team),
        match_date=VALUES(match_date),
        match_time=VALUES(match_time),
        home_odds=VALUES(home_odds),
        draw_odds=VALUES(draw_odds),
        away_odds=VALUES(away_odds),
        match_url=VALUES(match_url),
        scraped_at=CURRENT_TIMESTAMP
    """
    params = (
        mkey,
        match["home_team"][:100],
        match["away_team"][:100],
        match_date_sql,
        match_time_sql,
        (match["odds"].get("home") or "--")[:10],
        (match["odds"].get("draw") or "--")[:10],
        (match["odds"].get("away") or "--")[:10],
        (match.get("match_url") or "")[:255],
    )
    cur.execute(sql, params)
    
    if cur.lastrowid:
        match_id = cur.lastrowid
    else:
        cur.execute("SELECT id FROM matches WHERE match_key=%s", (mkey,))
        row = cur.fetchone()
        match_id = row[0] if row else 0
    conn.commit()
    return match_id

@db_retry
def replace_h2h(conn, match_id: int, h2h: Dict) -> None:
    if not h2h or not h2h.get("matches"):
        return
    cur = conn.cursor()
    cur.execute("DELETE FROM h2h_matches WHERE match_id=%s", (match_id,))
    if h2h["matches"]:
        data = []
        for m in h2h["matches"][:6]:
            data.append((
                match_id,
                (m.get("date") or "")[:50],
                (m.get("home_team") or "")[:100],
                (m.get("away_team") or "")[:100],
                (m.get("score") or "")[:20],
                (m.get("home_odds") or "--")[:10],
                (m.get("draw_odds") or "--")[:10],
                (m.get("away_odds") or "--")[:10],
            ))
        cur.executemany("""
            INSERT INTO h2h_matches
                (match_id, date, home_team, away_team, score, home_odds, draw_odds, away_odds)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, data)
    conn.commit()

@db_retry
def replace_standings(conn, match_id: int, standings: List[Dict]) -> None:
    if not standings:
        return
    cur = conn.cursor()
    cur.execute("DELETE FROM standings WHERE match_id=%s", (match_id,))
    data = []
    for s in standings:
        data.append((
            match_id,
            (s.get("team") or "")[:100],
            (s.get("rank") or "0")[:10],
            (s.get("mp") or "0")[:5],
            (s.get("wins") or "0")[:5],
            (s.get("draws") or "0")[:5],
            (s.get("losses") or "0")[:5],
            (s.get("goals") or "0:0")[:10],
            (s.get("gd") or "0")[:5],
            (s.get("pts") or "0")[:5],
        ))
    cur.executemany("""
        INSERT INTO standings
            (match_id, team, rank, mp, wins, draws, losses, goals, gd, pts)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, data)
    conn.commit()

# ---------- PAGE SETUP & SCROLL ----------
def setup_browser_page(browser):
    page = browser.new_page()
    ua = random.choice(SCRAPER_CONFIG["user_agents"])
    page.set_extra_http_headers({"User-Agent": ua})
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.route("**/*.{png,jpg,jpeg,gif,svg,css,font,woff,woff2}", lambda r: r.abort())
    return page

def scroll_load_more(page, times: int, pause: float):
    """Scroll down multiple times to load more fixtures."""
    last_len = 0
    for i in range(1, times + 1):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(pause)
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        current = len(soup.select("ul.table-main__matchInfo, .match-row, .fixture-row"))
        logging.info(f"🔽 Scroll {i}/{times} — elements: {current}")
        if current <= last_len and i >= 3:
            logging.debug("No new elements detected after scroll")
        last_len = max(last_len, current)

# ---------- DETAIL PARSERS ----------
def parse_h2h(soup) -> Dict:
    h2h_summary = {"home_wins": "0", "draws": "0", "away_wins": "0"}
    h2h_matches = []

    rows = []
    for sel in ["#js-mutual-table .head-to-head__row", ".h2h-table tbody tr", ".mutual-matches tr"]:
        rows = soup.select(sel)
        if rows:
            break

    for row in rows[:6]:
        try:
            date = safe_text(row.select_one(".head-to-head__date, .match-date, .date"))
            score = safe_text(row.select_one(".mainResult, .score, .result"))
            teams = []
            for ts in [".table-main__truncate", ".team-name", ".participant", "td"]:
                t = [safe_text(x) for x in row.select(ts) if safe_text(x)]
                if len(t) >= 2:
                    teams = t
                    break
            odds_nodes = row.select(".table-main__odds, .odds-cell, .odds-value")
            h2h_matches.append({
                "date": date or "N/A",
                "home_team": teams[0] if len(teams) > 0 else "N/A",
                "away_team": teams[1] if len(teams) > 1 else "N/A",
                "score": score or "N/A",
                "home_odds": safe_text(odds_nodes[0]) if len(odds_nodes) > 0 else "--",
                "draw_odds": safe_text(odds_nodes[1]) if len(odds_nodes) > 1 else "--",
                "away_odds": safe_text(odds_nodes[2]) if len(odds_nodes) > 2 else "--",
            })
        except Exception:
            continue

    return {"summary": h2h_summary, "matches": h2h_matches}

def parse_standings(soup, home_team: str, away_team: str) -> List[Dict]:
    target = {home_team.lower(), away_team.lower()}
    rows = []
    for sel in ["#table-type-1 tbody tr", ".standings-table tbody tr", ".league-table tbody tr", "table.standings tr"]:
        rows = soup.select(sel)
        if rows:
            break
    out = []
    for r in rows:
        try:
            team = ""
            for ts in [".team_name_span", ".team-name", ".participant", "td:nth-child(2)"]:
                el = r.select_one(ts)
                if el:
                    team = safe_text(el)
                    break
            if not team or team.lower() not in target:
                continue
            def pick(keys, default="0"):
                for k in keys:
                    el = r.select_one(k)
                    if el and safe_text(el):
                        return safe_text(el)
                return default
            out.append({
                "team": team,
                "rank": pick([".col_rank", ".position", "td:nth-child(1)"]),
                "mp": pick([".matches_played", ".played", ".mp"]),
                "wins": pick([".wins_regular", ".wins", ".w"]),
                "draws": pick([".draws", ".drawn", ".d"]),
                "losses": pick([".losses_regular", ".losses", ".l"]),
                "goals": pick([".goals", ".goals-for-against", ".gf-ga"], "0:0"),
                "gd": pick([".goals_for_against_diff", ".goal-difference", ".gd"]),
                "pts": pick([".points", ".pts", "td:last-child"]),
            })
        except Exception:
            continue
    return out

# ---------- SCRAPER ----------
def setup_and_load_main(browser):
    page = setup_browser_page(browser)
    logging.info(f"📡 Loading {BASE_URL}")
    page.goto(BASE_URL, timeout=SCRAPER_CONFIG["page_timeout"])
    
    loaded = False
    for sel in ["ul.table-main__matchInfo", ".matches-list", ".match-row", ".fixture-row"]:
        try:
            page.wait_for_selector(sel, timeout=SCRAPER_CONFIG["selector_timeout"])
            loaded = True
            break
        except Exception:
            continue
    if not loaded:
        raise RuntimeError("No matches container found on main page")
    
    scroll_load_more(page, SCRAPER_CONFIG["scroll_times"], SCRAPER_CONFIG["scroll_pause"])
    html = page.content()
    return page, BeautifulSoup(html, "html.parser")

def scrape_match_details(browser, url: str, home_team: str, away_team: str) -> Tuple[Dict, List[Dict]]:
    sub = setup_browser_page(browser)
    try:
        sub.goto(url, timeout=SCRAPER_CONFIG["page_timeout"])
        for sel in ["#H2HComponent", ".h2h-section", ".head-to-head"]:
            try:
                sub.wait_for_selector(sel, timeout=SCRAPER_CONFIG["selector_timeout"])
                break
            except Exception:
                continue
        random_delay(1.0, 2.2)
        soup = BeautifulSoup(sub.content(), "html.parser")
        return parse_h2h(soup), parse_standings(soup, home_team, away_team)
    except Exception as e:
        logging.warning(f"⚠️ Detail fetch failed for {home_team} vs {away_team}: {e}")
        return {"summary": {}, "matches": []}, []
    finally:
        sub.close()

def scrape():
    start = time.time()
    logging.info("🚀 Starting scraper...")
    init_db()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-images",
            ],
        )
        main_page = None
        try:
            main_page, soup = setup_and_load_main(browser)

            match_nodes = []
            for sel in ["ul.table-main__matchInfo", ".match-row", ".fixture-row"]:
                match_nodes = soup.select(sel)
                if match_nodes:
                    break
            logging.info(f"📊 Found {len(match_nodes)} match blocks after scrolling")

            success = fail = skipped = 0
            with db_conn() as conn:
                for idx, node in enumerate(match_nodes, 1):
                    try:
                        # Extract team names
                        home = ""
                        for sel in [".participantHomeOrder", ".home-team", ".team-home", ".table-main__participantHome"]:
                            el = node.select_one(sel)
                            if el:
                                home = safe_text(el)
                                break

                        away = ""
                        for sel in [".table-main__participantAway", ".away-team", ".team-away"]:
                            el = node.select_one(sel)
                            if el:
                                away = safe_text(el)
                                break

                        if not home or not away:
                            logging.warning(f"⚠️ Skipping match {idx}: missing team names (home='{home}' away='{away}')")
                            fail += 1
                            continue

                        # Extract date and time 🎯
                        match_date = None
                        match_time = None
                        
                        # First, try to extract from data-dt attribute (most reliable)
                        data_dt = node.get('data-dt')  # Format: "21,9,2025,15,00" (day,month,year,hour,minute)
                        if data_dt:
                            try:
                                parts = data_dt.split(',')
                                if len(parts) >= 5:
                                    day, month, year, hour, minute = parts[:5]
                                    match_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                                    match_time = f"{hour.zfill(2)}:{minute.zfill(2)}"
                            except Exception as e:
                                logging.debug(f"Failed to parse data-dt '{data_dt}': {e}")
                        
                        # If data-dt failed, try the time element directly
                        if not match_time:
                            time_el = node.select_one(".table-main__matchHour, .matchDateStatus, .match-time, .time")
                            if time_el:
                                time_text = safe_text(time_el).strip()
                                # Look for HH:MM pattern
                                import re
                                time_match = re.search(r'(\d{1,2}):(\d{2})', time_text)
                                if time_match:
                                    hours, minutes = time_match.groups()
                                    match_time = f"{hours.zfill(2)}:{minutes}"
                        
                        # Try other selectors for date/time as fallback
                        if not match_date or not match_time:
                            for sel in [".table-main__date", ".match-date", ".date-time", ".datetime"]:
                                date_el = node.select_one(sel)
                                if date_el:
                                    parsed_date, parsed_time = parse_match_datetime(date_el)
                                    if not match_date and parsed_date:
                                        match_date = parsed_date
                                    if not match_time and parsed_time:
                                        match_time = parsed_time
                                    if match_date and match_time:
                                        break

                        link = node.select_one("a")
                        url = None
                        if link and link.get("href"):
                            href = link.get("href")
                        url = href if href.startswith("http") else ("https://www.betexplorer.com" + href)

                        # 🔍 CHECK IF MATCH EXISTS - SKIP IF FOUND
                        if match_exists(conn, home, away, match_date, url):
                            skipped += 1
                            datetime_info = ""
                            if match_date:
                                datetime_info += f" 📅 {match_date}"
                            if match_time:
                                datetime_info += f" 🕐 {match_time}"
                            logging.info(f"⏭️ {idx}/{len(match_nodes)}: {home} vs {away}{datetime_info} (SKIPPED - Already exists)")
                            continue

                        odds = extract_odds(node)

                        # Enhanced logging with date/time info
                        datetime_info = ""
                        if match_date:
                            datetime_info += f" 📅 {match_date}"
                        if match_time:
                            datetime_info += f" 🕐 {match_time}"
                        
                        logging.info(f"🏈 {idx}/{len(match_nodes)}: {home} vs {away}{datetime_info}")

                        h2h, standings = ({}, [])
                        if url:
                            h2h, standings = scrape_match_details(browser, url, home, away)

                        match_id = upsert_match(conn, {
                            "home_team": home,
                            "away_team": away,
                            "match_date": match_date,
                            "match_time": match_time,
                            "odds": odds,
                            "match_url": url,
                        })

                        replace_h2h(conn, match_id, h2h)
                        replace_standings(conn, match_id, standings)

                        success += 1
                        logging.info(f"✅ Saved (id={match_id}) {home} vs {away}{datetime_info}")
                        random_delay(0.4, 1.1)

                    except Exception as e:
                        fail += 1
                        logging.error(f"❌ Failed to process match {idx}: {e}")
                        logging.error("Traceback: " + traceback.format_exc())

            elapsed = time.time() - start
            total = success + fail + skipped
            rate = (success / total * 100) if total else 0.0
            logging.info(f"🎯 Done in {elapsed:.2f}s — OK: {success} / Skipped: {skipped} / Fail: {fail} — Success rate: {rate:.1f}%")

        finally:
            try:
                if main_page:
                    main_page.close()
            except Exception:
                pass
            browser.close()

if __name__ == "__main__":
    try:
        scrape()
    except KeyboardInterrupt:
        logging.info("🛑 Interrupted")
    except Exception as e:
        logging.error(f"💥 Fatal error: {e}")
        sys.exit(1)