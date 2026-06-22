"""
paper_fetcher.py — Semantic Scholar API + arXiv fallback
"""

import requests
import time
import xml.etree.ElementTree as ET
from typing import Optional

SS_BASE   = 'https://api.semanticscholar.org/graph/v1'
ARXIV_BASE = 'https://export.arxiv.org/api/query'

HEADERS = {'User-Agent': 'SNU-Faculty-Explorer/1.0 (academic research tool)'}


# ─── Semantic Scholar ─────────────────────────────────────────────────────────

def _ss_get(path: str, params: dict) -> Optional[dict]:
    try:
        resp = requests.get(f'{SS_BASE}{path}', params=params, headers=HEADERS, timeout=12)
        if resp.status_code == 429:
            print('    [!] SS rate limit — waiting 10s')
            time.sleep(10)
            resp = requests.get(f'{SS_BASE}{path}', params=params, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f'    [!] SS request failed: {e}')
    return None


def search_author_ss(name_en: str) -> Optional[str]:
    """Return Semantic Scholar authorId if found with SNU affiliation."""
    data = _ss_get('/author/search', {
        'query': f'{name_en} Seoul National University',
        'limit': 8,
        'fields': 'name,affiliations,paperCount,externalIds'
    })
    if not data:
        return None

    for author in data.get('data', []):
        affils = ' '.join(a.get('name', '') for a in author.get('affiliations', [])).lower()
        if 'seoul national' in affils or 'snu' in affils:
            return author['authorId']

    # Fallback: first result with >3 papers
    for author in data.get('data', []):
        if author.get('paperCount', 0) > 3:
            return author['authorId']

    return None


def get_papers_ss(author_id: str, limit: int = 40) -> list:
    data = _ss_get(f'/author/{author_id}/papers', {
        'limit': limit,
        'fields': 'title,year,venue,authors,abstract,citationCount,externalIds,url,publicationTypes'
    })
    if not data:
        return []

    papers = []
    for p in data.get('data', []):
        if not p.get('title'):
            continue
        paper = {
            'title':     p['title'],
            'year':      p.get('year'),
            'venue':     p.get('venue', ''),
            'authors':   ', '.join(a.get('name', '') for a in p.get('authors', [])[:6]),
            'abstract':  (p.get('abstract') or '')[:600],
            'citations': p.get('citationCount', 0),
            'url':       p.get('url', ''),
        }
        ext = p.get('externalIds') or {}
        if ext.get('DOI'):
            paper['doi'] = ext['DOI']
        if ext.get('ArXiv'):
            paper['arxiv_id'] = ext['ArXiv']
        papers.append(paper)

    return papers


# ─── arXiv fallback ────────────────────────────────────────────────────────────

def get_papers_arxiv(name_en: str) -> list:
    # Build a name search query (last name only for reliability)
    parts = name_en.strip().split()
    last = parts[-1] if parts else name_en
    query = f'au:{last}'

    try:
        resp = requests.get(ARXIV_BASE, params={
            'search_query': query,
            'start': 0,
            'max_results': 15,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending',
        }, headers=HEADERS, timeout=12)

        root = ET.fromstring(resp.text)
        ns_atom  = 'http://www.w3.org/2005/Atom'
        ns_arxiv = 'http://arxiv.org/schemas/atom'

        papers = []
        for entry in root.findall(f'{{{ns_atom}}}entry'):
            title    = (entry.findtext(f'{{{ns_atom}}}title') or '').replace('\n', ' ').strip()
            abstract = (entry.findtext(f'{{{ns_atom}}}summary') or '').strip()[:600]
            pub_date = entry.findtext(f'{{{ns_atom}}}published') or ''
            year     = int(pub_date[:4]) if pub_date else None
            arxiv_url = entry.findtext(f'{{{ns_atom}}}id') or ''
            arxiv_id  = arxiv_url.split('/')[-1]

            authors = ', '.join(
                a.findtext(f'{{{ns_atom}}}name') or ''
                for a in entry.findall(f'{{{ns_atom}}}author')[:6]
            )

            papers.append({
                'title':      title,
                'year':       year,
                'venue':      'arXiv',
                'authors':    authors,
                'abstract':   abstract,
                'arxiv_id':   arxiv_id,
                'citations':  0,
                'url':        arxiv_url,
            })

        return papers
    except Exception as e:
        print(f'    [!] arXiv fetch failed: {e}')
        return []


# ─── Classification ────────────────────────────────────────────────────────────

def classify_papers(papers: list) -> list:
    if not papers:
        return []

    # Sort descending by citations
    by_cit = sorted(papers, key=lambda p: p.get('citations', 0), reverse=True)

    # Tag top-cited as representative (up to 5, minimum 5 citations)
    rep_ids = {id(p) for p in by_cit[:5] if p.get('citations', 0) >= 5}

    for p in papers:
        if id(p) in rep_ids:
            p['paper_type'] = 'representative'
        elif p.get('year') and p['year'] >= 2021:
            p['paper_type'] = 'recent'
        else:
            p['paper_type'] = 'other'

    return papers


# ─── Main entry point ──────────────────────────────────────────────────────────

def fetch_papers_for_professor(name_en: str, name_kr: str = '') -> list:
    if not name_en:
        return []

    print(f'    📄 Fetching papers for: {name_en}')
    author_id = search_author_ss(name_en)
    papers = []

    if author_id:
        print(f'    → SS author ID: {author_id}')
        papers = get_papers_ss(author_id)
        time.sleep(0.4)

    if not papers:
        print(f'    → arXiv fallback')
        papers = get_papers_arxiv(name_en)

    papers = classify_papers(papers)
    return papers
