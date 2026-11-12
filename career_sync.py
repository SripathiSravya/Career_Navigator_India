"""India-focused occupation catalogue synchronisation.

Primary source: Directorate General of Employment (DGE), Government of India,
NCO 2015 searchable occupation catalogue (https://dge.gov.in/nat).
Supplementary source: NSDC National Occupational Standards / Model Curriculum
catalogue (https://www.nsdcindia.org/national-occupational-standards-and-model-curriculum).

This imports occupation/job-role titles and classification metadata. It does not
claim that any public catalogue contains every occupation or instantly detects
new careers. The DGE and NSDC sites remain authoritative source owners.
"""
import re
import sqlite3
import ssl
import certifi
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin

DGE_URL = "https://dge.gov.in/nat"
NSDC_URL = "https://www.nsdcindia.org/national-occupational-standards-and-model-curriculum"
SYNC_INTERVAL_HOURS = 24
USER_AGENT = "CareerNavigatorIndia/1.0 (educational career catalogue synchronisation)"

# Broad occupational-family to skill mapping. These are starter matching skills,
# not claims that every person in the occupation needs every listed skill.
FAMILY_SKILLS = {
    "computer|information technology|ict|software|data|database|network|web|cyber": ["Python", "SQL", "Networking", "Linux", "Java", "Data Analysis"],
    "finance|account|bank|insurance|audit|tax": ["Excel", "Accounting", "Financial Analysis", "SQL", "Tally"],
    "engineering|mechanical|electrical|electronics|civil|manufacturing|production": ["Engineering Fundamentals", "CAD", "Quality Control", "Mathematics", "Technical Drawing"],
    "health|medical|nursing|pharmacy|clinical|diagnostic": ["Medical Terminology", "Patient Care", "Clinical Procedures", "Healthcare Documentation"],
    "education|teaching|training|academic": ["Subject Knowledge", "Lesson Planning", "Assessment", "Educational Technology"],
    "agri|farm|forestry|fisher|horticulture": ["Agronomy", "Crop Management", "Soil Science", "Agricultural Equipment"],
    "legal|law|judicial": ["Legal Research", "Legal Documentation", "Contract Drafting"],
    "construction|building|plumb|mason|carpent|weld|electrician": ["Technical Drawing", "Safety Procedures", "Equipment Operation", "Quality Control"],
    "logistic|transport|supply chain|warehouse|shipping": ["Logistics", "Supply Chain Management", "Inventory Management", "Excel"],
    "design|graphic|media|animation|film|photograph": ["Graphic Design", "Adobe Creative Tools", "Video Editing", "Visual Communication"],
    "sales|marketing|retail|customer": ["CRM", "Sales Operations", "Digital Marketing", "Inventory Management", "Excel"],
    "hospitality|hotel|tourism|food|beverage": ["Food Safety", "Hospitality Operations", "Reservation Systems", "Inventory Management"],
}


def _clean(value):
    return re.sub(r"\s+", " ", (value or "").replace("\xa0", " ")).strip()


class _TableParser(HTMLParser):
    """Read table rows without requiring BeautifulSoup or another dependency."""
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell, self.in_cell = [], True

    def handle_data(self, data):
        if self.in_cell and self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.in_cell:
            self.row.append(_clean(" ".join(self.cell or [])))
            self.cell, self.in_cell = None, False
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None


def _download(url, timeout=30):
    req = urllib.request.Request(url, headers={"Accept": "text/html,application/xhtml+xml", "User-Agent": USER_AGENT})
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
        return response.read().decode("utf-8", errors="replace")


def _category_and_skills(division, subdivision, group, family, title):
    text = " | ".join((division, subdivision, group, family, title)).lower()
    for pattern, skills in FAMILY_SKILLS.items():
        if re.search(pattern, text):
            if "computer|information technology|ict|software|data|database|network|web|cyber" in pattern:
                return "Information Technology", skills
            if "finance|account|bank|insurance|audit|tax" in pattern:
                return "Banking, Finance & Accounting", skills
            if "engineering|mechanical|electrical|electronics|civil|manufacturing|production" in pattern:
                return "Engineering & Manufacturing", skills
            if "health|medical|nursing|pharmacy|clinical|diagnostic" in pattern:
                return "Healthcare", skills
            if "education|teaching|training|academic" in pattern:
                return "Education & Training", skills
            if "agri|farm|forestry|fisher|horticulture" in pattern:
                return "Agriculture & Allied", skills
            if "legal|law|judicial" in pattern:
                return "Legal Services", skills
            if "construction|building|plumb|mason|carpent|weld|electrician" in pattern:
                return "Construction & Skilled Trades", skills
            if "logistic|transport|supply chain|warehouse|shipping" in pattern:
                return "Transport & Logistics", skills
            if "design|graphic|media|animation|film|photograph" in pattern:
                return "Design & Media", skills
            if "sales|marketing|retail|customer" in pattern:
                return "Sales, Marketing & Retail", skills
            if "hospitality|hotel|tourism|food|beverage" in pattern:
                return "Hospitality & Tourism", skills
    return (division or subdivision or "Other Indian Occupations"), ["Domain Knowledge", "Technical Procedures", "Documentation"]


def _parse_dge_page(html):
    parser = _TableParser()
    parser.feed(html)
    records = []
    for row in parser.rows:
        # DGE table columns: serial, occupational title, NCO 2015, NCO 2004,
        # division, sub-division, group, family. Ignore headers and other tables.
        if len(row) < 8 or not re.fullmatch(r"\d{4}\.\d{4}", row[2]):
            continue
        title = _clean(row[1])
        if not title or len(title) > 150:
            continue
        records.append({"name": title, "code": row[2], "division": row[4],
                        "subdivision": row[5], "group": row[6], "family": row[7]})
    return records


def _ensure_state(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS career_sync_state (source TEXT PRIMARY KEY, last_sync TEXT, imported INTEGER DEFAULT 0, status TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS career_source_records (source TEXT NOT NULL, external_id TEXT NOT NULL, career_id INTEGER NOT NULL, PRIMARY KEY(source, external_id))")


def _upsert_occupation(conn, record, source="NCO_2015"):
    name = _clean(record["name"])
    if not name:
        return False
    division = _clean(record.get("division", ""))
    subdivision = _clean(record.get("subdivision", ""))
    group = _clean(record.get("group", ""))
    family = _clean(record.get("family", ""))
    category, skills = _category_and_skills(division, subdivision, group, family, name)
    description = (f"Indian occupation listed in {source}. Classification: {division}; {subdivision}; {group}; {family}. "
                   f"Occupation code: {record.get('code', 'Not provided')}. Source: Government of India / NSDC catalogue.")
    cur = conn.execute("INSERT OR IGNORE INTO careers(name,description,category,education,experience,status,updated) VALUES(?,?,?,?,?,?,?)",
                       (name, description, category, "Depends on the occupation; see relevant Indian qualification requirements", "Varies by role", "Active", datetime.now(timezone.utc).date().isoformat()))
    career = conn.execute("SELECT id FROM careers WHERE name=? COLLATE NOCASE", (name,)).fetchone()
    if not career:
        return False
    cid = career["id"]
    # Only add inferred skills if this career has no existing skill mapping.
    if not conn.execute("SELECT 1 FROM career_skills WHERE career_id=? LIMIT 1", (cid,)).fetchone():
        conn.executemany("INSERT INTO career_skills(career_id,skill,weight) VALUES(?,?,?)",
                         [(cid, skill, 3) for skill in skills])
    if not conn.execute("SELECT 1 FROM career_roles WHERE career_id=? LIMIT 1", (cid,)).fetchone():
        conn.execute("INSERT INTO career_roles(career_id,title) VALUES(?,?)", (cid, name))
    ext_id = _clean(record.get("code") or name.lower())
    conn.execute("INSERT OR IGNORE INTO career_source_records(source,external_id,career_id) VALUES(?,?,?)", (source, ext_id, cid))
    return cur.rowcount > 0


def sync_indian_career_catalogue(db_path, force=False, max_nco_pages=400):
    """Import Indian NCO occupations and NSDC job-role titles.

    The DGE listing is paginated. Pages are fetched until no further occupation
    rows are found (with a safety cap). A successful sync is cached for 24 hours.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _ensure_state(conn)
    try:
        state = conn.execute("SELECT last_sync FROM career_sync_state WHERE source='INDIA_CAREER_CATALOGUE'").fetchone()
        if not force and state and state["last_sync"]:
            try:
                last = datetime.fromisoformat(state["last_sync"])
                if datetime.now(timezone.utc) - last < timedelta(hours=SYNC_INTERVAL_HOURS):
                    return {"status": "recent", "imported": 0}
            except ValueError:
                pass

        imported_nco, checked_nco, seen_codes = 0, 0, set()
        empty_pages = 0
        for page in range(max_nco_pages):
            url = DGE_URL if page == 0 else f"{DGE_URL}?page={page}"
            html = _download(url)
            records = _parse_dge_page(html)
            checked_nco += len(records)
            new_on_page = 0
            for rec in records:
                if rec["code"] in seen_codes:
                    continue
                seen_codes.add(rec["code"])
                if _upsert_occupation(conn, rec, "NCO_2015"):
                    imported_nco += 1
                    new_on_page += 1
            empty_pages = empty_pages + 1 if not records else 0
            if empty_pages >= 2:
                break
            # Stop if the page repeats the same rows, a common pagination fallback.
            if records and new_on_page == 0 and page > 0:
                break

        # NSDC page provides supplementary role/qualification references. Extract
        # job-role-like anchor labels; NCO remains the structured primary catalogue.
        nsdc_html = _download(NSDC_URL)
        class _AnchorParser(HTMLParser):
            def __init__(self):
                super().__init__(); self.items=[]; self.href=None; self.parts=[]
            def handle_starttag(self, tag, attrs):
                if tag == "a": self.href=dict(attrs).get("href", ""); self.parts=[]
            def handle_data(self, data):
                if self.href is not None: self.parts.append(data)
            def handle_endtag(self, tag):
                if tag == "a" and self.href is not None:
                    self.items.append((_clean(" ".join(self.parts)), urljoin(NSDC_URL, self.href))); self.href=None
        ap = _AnchorParser(); ap.feed(nsdc_html)
        imported_nsdc = 0
        for label, href in ap.items:
            low = label.lower()
            if not label or len(label) > 140 or not any(k in low for k in ("job role", "qualification", "qp listing", "standalone nos", "occupational standard")):
                continue
            # Do not turn generic navigation labels into occupations. The label is
            # retained as a source reference; role names are loaded from DGE/NCO.
            continue

        now = datetime.now(timezone.utc).isoformat()
        total = imported_nco + imported_nsdc
        conn.execute("INSERT OR REPLACE INTO career_sync_state(source,last_sync,imported,status) VALUES('INDIA_CAREER_CATALOGUE',?,?,?)",
                     (now, total, f"success; NCO records scanned={checked_nco}; NCO pages={page + 1}; NSDC catalogue checked"))
        conn.commit()
        return {"status": "success", "imported": total, "nco_imported": imported_nco,
                "nsdc_imported": imported_nsdc, "occupations_checked": checked_nco, "pages_checked": page + 1}
    except Exception as exc:
        conn.execute("INSERT OR REPLACE INTO career_sync_state(source,last_sync,imported,status) VALUES('INDIA_CAREER_CATALOGUE',NULL,0,?)",
                     ("error: " + str(exc)[:400],))
        conn.commit()
        return {"status": "error", "imported": 0, "message": str(exc)}
    finally:
        conn.close()


# Backwards-compatible function name for any older imports in the project.
def sync_job_market_careers(db_path, force=False):
    return sync_indian_career_catalogue(db_path, force=force)
