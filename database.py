"""
database.py — SQLite layer for SNU Faculty Explorer
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path('data/faculty.db')


def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS professors (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name_kr     TEXT NOT NULL,
            name_en     TEXT,
            college     TEXT,
            department  TEXT,
            position    TEXT,
            email       TEXT,
            phone       TEXT,
            office      TEXT,
            lab         TEXT,
            research_areas TEXT DEFAULT '[]',
            bio         TEXT,
            photo_url   TEXT,
            profile_url TEXT,
            homepage    TEXT,
            joined_year INTEGER,
            semantic_scholar_id TEXT,
            updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS papers (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            professor_id INTEGER NOT NULL,
            title        TEXT NOT NULL,
            authors      TEXT,
            venue        TEXT,
            year         INTEGER,
            doi          TEXT,
            arxiv_id     TEXT,
            abstract     TEXT,
            citations    INTEGER DEFAULT 0,
            paper_type   TEXT DEFAULT 'recent',
            url          TEXT,
            FOREIGN KEY (professor_id) REFERENCES professors(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_prof_college   ON professors(college);
        CREATE INDEX IF NOT EXISTS idx_prof_dept      ON professors(department);
        CREATE INDEX IF NOT EXISTS idx_prof_position  ON professors(position);
        CREATE INDEX IF NOT EXISTS idx_paper_prof     ON papers(professor_id);
        CREATE INDEX IF NOT EXISTS idx_paper_type     ON papers(paper_type);
    ''')
    conn.commit()
    conn.close()


def upsert_professor(data: dict) -> int:
    conn = get_conn()
    existing = conn.execute(
        'SELECT id FROM professors WHERE name_kr=? AND department=?',
        (data.get('name_kr'), data.get('department'))
    ).fetchone()

    ra = json.dumps(data.get('research_areas', []), ensure_ascii=False)

    if existing:
        prof_id = existing['id']
        conn.execute('''
            UPDATE professors SET
                name_en     = COALESCE(NULLIF(?, ''), name_en),
                college     = COALESCE(?, college),
                position    = COALESCE(?, position),
                email       = COALESCE(NULLIF(?, ''), email),
                phone       = COALESCE(NULLIF(?, ''), phone),
                office      = COALESCE(NULLIF(?, ''), office),
                lab         = COALESCE(NULLIF(?, ''), lab),
                research_areas = CASE WHEN ? != '[]' THEN ? ELSE research_areas END,
                bio         = COALESCE(NULLIF(?, ''), bio),
                photo_url   = COALESCE(NULLIF(?, ''), photo_url),
                profile_url = COALESCE(NULLIF(?, ''), profile_url),
                homepage    = COALESCE(NULLIF(?, ''), homepage),
                joined_year = COALESCE(?, joined_year),
                updated_at  = ?
            WHERE id = ?
        ''', (
            data.get('name_en'), data.get('college'), data.get('position'),
            data.get('email'), data.get('phone'), data.get('office'), data.get('lab'),
            ra, ra,
            data.get('bio'), data.get('photo_url'), data.get('profile_url'),
            data.get('homepage'), data.get('joined_year'),
            datetime.now().isoformat(), prof_id
        ))
    else:
        cursor = conn.execute('''
            INSERT INTO professors
                (name_kr, name_en, college, department, position,
                 email, phone, office, lab, research_areas, bio,
                 photo_url, profile_url, homepage, joined_year, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            data.get('name_kr'), data.get('name_en'),
            data.get('college'), data.get('department'), data.get('position'),
            data.get('email'), data.get('phone'), data.get('office'), data.get('lab'),
            ra, data.get('bio'),
            data.get('photo_url'), data.get('profile_url'), data.get('homepage'),
            data.get('joined_year'), datetime.now().isoformat()
        ))
        prof_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return prof_id


def upsert_papers(professor_id: int, papers: list):
    conn = get_conn()
    for paper in papers:
        existing = conn.execute(
            'SELECT id FROM papers WHERE professor_id=? AND title=?',
            (professor_id, paper.get('title'))
        ).fetchone()

        if not existing:
            conn.execute('''
                INSERT INTO papers
                    (professor_id, title, authors, venue, year,
                     doi, arxiv_id, abstract, citations, paper_type, url)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                professor_id, paper.get('title'), paper.get('authors'),
                paper.get('venue'), paper.get('year'), paper.get('doi'),
                paper.get('arxiv_id'), paper.get('abstract'),
                paper.get('citations', 0), paper.get('paper_type', 'recent'),
                paper.get('url')
            ))
        else:
            conn.execute(
                'UPDATE papers SET citations=? WHERE id=?',
                (paper.get('citations', 0), existing['id'])
            )

    conn.commit()
    conn.close()


def get_professors(filters: dict) -> list:
    conn = get_conn()
    query = 'SELECT * FROM professors WHERE 1=1'
    params = []

    if filters.get('college'):
        query += ' AND college = ?'
        params.append(filters['college'])

    if filters.get('department'):
        query += ' AND department = ?'
        params.append(filters['department'])

    if filters.get('position'):
        query += ' AND position = ?'
        params.append(filters['position'])

    if filters.get('keyword'):
        kw = f'%{filters["keyword"]}%'
        query += ' AND (research_areas LIKE ? OR bio LIKE ? OR lab LIKE ?)'
        params.extend([kw, kw, kw])

    if filters.get('search'):
        s = f'%{filters["search"]}%'
        query += ' AND (name_kr LIKE ? OR name_en LIKE ? OR research_areas LIKE ? OR lab LIKE ? OR email LIKE ?)'
        params.extend([s, s, s, s, s])

    sort_map = {
        'name_kr':   'name_kr ASC',
        'name_en':   'COALESCE(name_en, name_kr) ASC',
        'joined':    'joined_year DESC, name_kr ASC',
        'department':'department ASC, name_kr ASC',
        'updated':   'updated_at DESC',
    }
    sort = sort_map.get(filters.get('sort', 'name_kr'), 'name_kr ASC')
    query += f' ORDER BY {sort}'

    rows = conn.execute(query, params).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        try:
            d['research_areas'] = json.loads(d.get('research_areas') or '[]')
        except Exception:
            d['research_areas'] = []
        result.append(d)

    conn.close()
    return result


def get_professor_detail(prof_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute('SELECT * FROM professors WHERE id=?', (prof_id,)).fetchone()
    if not row:
        conn.close()
        return None

    prof = dict(row)
    try:
        prof['research_areas'] = json.loads(prof.get('research_areas') or '[]')
    except Exception:
        prof['research_areas'] = []

    papers = conn.execute(
        'SELECT * FROM papers WHERE professor_id=? ORDER BY year DESC, citations DESC',
        (prof_id,)
    ).fetchall()
    prof['papers'] = [dict(p) for p in papers]
    conn.close()
    return prof


def get_all_keywords() -> list:
    conn = get_conn()
    rows = conn.execute(
        'SELECT research_areas FROM professors WHERE research_areas IS NOT NULL'
    ).fetchall()
    counts: dict[str, int] = {}
    for row in rows:
        try:
            for area in json.loads(row['research_areas'] or '[]'):
                area = area.strip()
                if area:
                    counts[area] = counts.get(area, 0) + 1
        except Exception:
            pass
    result = sorted(
        [{'keyword': k, 'count': v} for k, v in counts.items()],
        key=lambda x: -x['count']
    )
    conn.close()
    return result


def get_colleges() -> list:
    conn = get_conn()
    rows = conn.execute('''
        SELECT college, department, COUNT(*) AS cnt
        FROM professors
        GROUP BY college, department
        ORDER BY college, department
    ''').fetchall()

    colleges: dict[str, dict] = {}
    for row in rows:
        c = row['college'] or '기타'
        d = row['department'] or '기타'
        if c not in colleges:
            colleges[c] = {'name': c, 'departments': [], 'total': 0}
        colleges[c]['departments'].append({'name': d, 'count': row['cnt']})
        colleges[c]['total'] += row['cnt']

    conn.close()
    return list(colleges.values())


def get_stats() -> dict:
    conn = get_conn()
    stats = {
        'professors': conn.execute('SELECT COUNT(*) FROM professors').fetchone()[0],
        'colleges':   conn.execute('SELECT COUNT(DISTINCT college) FROM professors').fetchone()[0],
        'departments':conn.execute('SELECT COUNT(DISTINCT department) FROM professors').fetchone()[0],
        'papers':     conn.execute('SELECT COUNT(*) FROM papers').fetchone()[0],
    }
    conn.close()
    return stats
