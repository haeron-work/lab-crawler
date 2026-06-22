"""
crawler.py — SNU Department Faculty Crawler

Usage:
    python crawler.py              # crawl all departments
    python crawler.py --dept ee    # single department
    python crawler.py --dept ee,cse,mse
    python crawler.py --list       # list all available departments
    python crawler.py --no-papers  # skip paper fetching (faster)
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import argparse
import re
from urllib.parse import urljoin, urlparse

import database
from paper_fetcher import fetch_papers_for_professor

# ─── Config ────────────────────────────────────────────────────────────────────

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
}

# Departments: key → {name, college, url, alt_urls}
# alt_urls: fallback URLs if primary fails
DEPARTMENTS = {
    # ── 공과대학 ──────────────────────────────────────────────────────
    'ee': {
        'name': '전기·정보공학부', 'college': '공과대학',
        'url': 'https://ee.snu.ac.kr/people/faculty',
        'alt_urls': ['https://ee.snu.ac.kr/research/faculty', 'https://ee.snu.ac.kr/ko/people/faculty'],
    },
    'cse': {
        'name': '컴퓨터공학부', 'college': '공과대학',
        'url': 'https://cse.snu.ac.kr/people/faculty',
        'alt_urls': ['https://cse.snu.ac.kr/ko/people/faculty'],
    },
    'me': {
        'name': '기계공학부', 'college': '공과대학',
        'url': 'https://me.snu.ac.kr/people/professors',
        'alt_urls': ['https://me.snu.ac.kr/ko/node/36'],
    },
    'mse': {
        'name': '재료공학부', 'college': '공과대학',
        'url': 'https://mse.snu.ac.kr/people/professors',
        'alt_urls': ['https://mse.snu.ac.kr/ko/people/professors'],
    },
    'cbe': {
        'name': '화학생물공학부', 'college': '공과대학',
        'url': 'https://cbe.snu.ac.kr/people/faculty',
        'alt_urls': ['https://cbe.snu.ac.kr/ko/people/faculty'],
    },
    'ie': {
        'name': '산업공학과', 'college': '공과대학',
        'url': 'https://ie.snu.ac.kr/people/faculty',
        'alt_urls': ['https://ie.snu.ac.kr/ko/people/faculty'],
    },
    'civil': {
        'name': '건설환경공학부', 'college': '공과대학',
        'url': 'https://civil.snu.ac.kr/people/faculty',
        'alt_urls': ['https://civil.snu.ac.kr/ko/people/faculty'],
    },
    'aerospace': {
        'name': '항공우주공학과', 'college': '공과대학',
        'url': 'https://aerospace.snu.ac.kr/people/faculty',
        'alt_urls': ['https://aerospace.snu.ac.kr/ko/people'],
    },
    'nuclear': {
        'name': '원자핵공학과', 'college': '공과대학',
        'url': 'https://nuclear.snu.ac.kr/people/faculty',
        'alt_urls': ['https://nuclear.snu.ac.kr/ko/people/faculty'],
    },
    'naoe': {
        'name': '조선해양공학과', 'college': '공과대학',
        'url': 'https://naoe.snu.ac.kr/people/faculty',
        'alt_urls': ['https://naoe.snu.ac.kr/ko/people/professors'],
    },
    'energy': {
        'name': '에너지자원공학과', 'college': '공과대학',
        'url': 'https://energy.snu.ac.kr/people/faculty',
        'alt_urls': ['https://energy.snu.ac.kr/ko/people/faculty'],
    },
    'arch': {
        'name': '건축학과', 'college': '공과대학',
        'url': 'https://architecture.snu.ac.kr/people/faculty',
        'alt_urls': ['https://architecture.snu.ac.kr/ko/people/professors'],
    },
    'archeng': {
        'name': '건축공학과', 'college': '공과대학',
        'url': 'https://ae.snu.ac.kr/people/faculty',
        'alt_urls': ['https://ae.snu.ac.kr/ko/people/faculty'],
    },
    # ── 자연과학대학 ──────────────────────────────────────────────────
    'math': {
        'name': '수리과학부', 'college': '자연과학대학',
        'url': 'https://math.snu.ac.kr/people/faculty',
        'alt_urls': ['https://math.snu.ac.kr/ko/people/faculty'],
    },
    'stat': {
        'name': '통계학과', 'college': '자연과학대학',
        'url': 'https://stat.snu.ac.kr/people/faculty',
        'alt_urls': ['https://stat.snu.ac.kr/ko/people/faculty'],
    },
    'physics': {
        'name': '물리·천문학부', 'college': '자연과학대학',
        'url': 'https://physics.snu.ac.kr/people/faculty',
        'alt_urls': ['https://physics.snu.ac.kr/ko/people/faculty'],
    },
    'chem': {
        'name': '화학부', 'college': '자연과학대학',
        'url': 'https://chem.snu.ac.kr/people/faculty',
        'alt_urls': ['https://chem.snu.ac.kr/ko/people/faculty'],
    },
    'biosci': {
        'name': '생명과학부', 'college': '자연과학대학',
        'url': 'https://biosci.snu.ac.kr/people/faculty',
        'alt_urls': ['https://biosci.snu.ac.kr/ko/people/faculty'],
    },
    'ees': {
        'name': '지구환경과학부', 'college': '자연과학대학',
        'url': 'https://ees.snu.ac.kr/people/faculty',
        'alt_urls': ['https://ees.snu.ac.kr/ko/people/faculty'],
    },
    # ── 농업생명과학대학 ──────────────────────────────────────────────
    'agr_plant': {
        'name': '식물생산과학부', 'college': '농업생명과학대학',
        'url': 'https://pls.snu.ac.kr/people/faculty',
        'alt_urls': [],
    },
    'agr_food': {
        'name': '식품·동물생명공학부', 'college': '농업생명과학대학',
        'url': 'https://foodanimal.snu.ac.kr/people/faculty',
        'alt_urls': [],
    },
    'agr_env': {
        'name': '바이오시스템·소재학부', 'college': '농업생명과학대학',
        'url': 'https://bse.snu.ac.kr/people/faculty',
        'alt_urls': [],
    },
    # ── 의과대학 ──────────────────────────────────────────────────────
    'medicine': {
        'name': '의학과', 'college': '의과대학',
        'url': 'https://medicine.snu.ac.kr/people/faculty',
        'alt_urls': [],
    },
    # ── 치의학대학원 ──────────────────────────────────────────────────
    'dentistry': {
        'name': '치의과학과', 'college': '치의학대학원',
        'url': 'https://dentistry.snu.ac.kr/people/faculty',
        'alt_urls': [],
    },
    # ── 약학대학 ──────────────────────────────────────────────────────
    'pharmacy': {
        'name': '약학과', 'college': '약학대학',
        'url': 'https://pharm.snu.ac.kr/people/faculty',
        'alt_urls': [],
    },
    # ── 사범대학 ──────────────────────────────────────────────────────
    'edu_math': {
        'name': '수학교육과', 'college': '사범대학',
        'url': 'https://mathed.snu.ac.kr/people/faculty',
        'alt_urls': [],
    },
    'edu_sci': {
        'name': '과학교육과', 'college': '사범대학',
        'url': 'https://sci-edu.snu.ac.kr/people/faculty',
        'alt_urls': [],
    },
    # ── 경영대학 ──────────────────────────────────────────────────────
    'business': {
        'name': '경영학과', 'college': '경영대학',
        'url': 'https://biz.snu.ac.kr/people/faculty',
        'alt_urls': [],
    },
    # ── 사회과학대학 ──────────────────────────────────────────────────
    'economics': {
        'name': '경제학부', 'college': '사회과학대학',
        'url': 'https://econ.snu.ac.kr/people/faculty',
        'alt_urls': [],
    },
}

# ─── Helpers ───────────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '').strip())


def extract_email(text: str) -> str:
    m = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
    return m.group(0) if m else ''


def parse_research_areas(text: str) -> list[str]:
    areas = re.split(r'[,;/\n·•●▶\|]', text or '')
    seen = set()
    result = []
    for a in areas:
        a = clean(a)
        # Strip leading labels
        a = re.sub(r'^(연구\s*분야|관심\s*분야|Research\s*Interests?)\s*[:：]?\s*', '', a, flags=re.I)
        if a and len(a) > 1 and a not in seen and len(a) < 80:
            seen.add(a)
            result.append(a)
    return result[:12]


def extract_position(text: str) -> str:
    positions = [
        ('명예교수', '명예교수'), ('석좌교수', '석좌교수'),
        ('겸임교수', '겸임교수'), ('초빙교수', '초빙교수'),
        ('조교수', '조교수'), ('부교수', '부교수'), ('교수', '교수'),
        ('Assistant Professor', '조교수'), ('Associate Professor', '부교수'),
        ('Professor', '교수'),
    ]
    for pattern, label in positions:
        if pattern in text:
            return label
    return '교수'


def fetch_page(url: str, retries: int = 3) -> BeautifulSoup | None:
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or 'utf-8'
            return BeautifulSoup(resp.text, 'html.parser')
        except requests.RequestException as e:
            wait = 2 ** attempt
            print(f'    [!] Attempt {attempt+1} failed for {url}: {e} — retry in {wait}s')
            if attempt < retries - 1:
                time.sleep(wait)
    return None


def get_base_url(url: str) -> str:
    p = urlparse(url)
    return f'{p.scheme}://{p.netloc}'


# ─── Element-level extraction ─────────────────────────────────────────────────

# Common selectors for professor cards across SNU CMS variants
CARD_SELECTORS = [
    '.people-list .person', '.faculty-list .faculty-item',
    '.views-row', '.faculty-card', '.professor-card',
    '.people-card', '.member-card', '.staff-item',
    'article.professor', 'li.professor', 'div.professor',
    '.field-content .views-field', 'tr.professor',
    '.board-list tr', 'tbody tr',
]

PROFILE_LINK_PATTERNS = re.compile(
    r'/(people|faculty|professor|member|staff|person)/(?!faculty|staff|member|person)[\w\-]+/?$',
    re.I
)


def extract_from_card(el: BeautifulSoup, config: dict, base_url: str) -> dict | None:
    text_all = clean(el.get_text(' '))

    # ── Name ──────────────────────────────────────────────────────────
    name_kr = ''
    name_en = ''

    for sel in ['h2', 'h3', 'h4', '.name', '.professor-name', 'strong', 'b', '.title', 'dt', 'th']:
        el_name = el.find(sel)
        if el_name:
            t = clean(el_name.get_text())
            m_kr = re.search(r'[가-힣]{2,5}', t)
            if m_kr:
                name_kr = m_kr.group(0)
            m_en = re.search(r'[A-Z][a-z]+(?:\s+[A-Z]?\w+){1,3}', t)
            if m_en:
                name_en = m_en.group(0)
            if name_kr:
                break

    if not name_kr:
        m_kr = re.search(r'[가-힣]{2,5}', text_all)
        name_kr = m_kr.group(0) if m_kr else ''
    if not name_kr:
        return None

    # ── Photo ─────────────────────────────────────────────────────────
    photo_url = ''
    img = el.find('img')
    if img:
        src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or ''
        if src and not src.endswith('.svg'):
            photo_url = urljoin(base_url, src)

    # ── Profile link ──────────────────────────────────────────────────
    profile_url = ''
    for a in el.find_all('a', href=True):
        href = a['href']
        if not href.startswith('mailto:') and not href.startswith('tel:'):
            full = urljoin(base_url, href)
            if PROFILE_LINK_PATTERNS.search(href) or base_url in full:
                profile_url = full
                break
    if not profile_url:
        a = el.find('a', href=True)
        if a:
            href = a['href']
            if not href.startswith(('mailto:', 'tel:', '#')):
                profile_url = urljoin(base_url, href)

    # ── Research areas ────────────────────────────────────────────────
    research_areas: list[str] = []
    for kw in ['연구분야', '연구 분야', '관심분야', '연구관심', 'Research', 'Interest']:
        for tag in el.find_all(['p', 'span', 'div', 'li', 'td', 'dd']):
            t = clean(tag.get_text())
            if kw in t:
                research_areas = parse_research_areas(t)
                if research_areas:
                    break
        if research_areas:
            break

    # ── Email / position ─────────────────────────────────────────────
    email = extract_email(text_all)
    position = extract_position(text_all)

    return {
        'name_kr': name_kr,
        'name_en': name_en,
        'college': config['college'],
        'department': config['name'],
        'photo_url': photo_url,
        'profile_url': profile_url,
        'email': email,
        'position': position,
        'research_areas': research_areas,
    }


# ─── Profile page deep-scrape ─────────────────────────────────────────────────

def deep_scrape_profile(url: str, partial: dict, base_url: str) -> dict:
    """Visit a professor's own page and enrich partial data."""
    soup = fetch_page(url)
    if not soup:
        return partial

    text_all = soup.get_text(' ')

    # Email
    if not partial.get('email'):
        partial['email'] = extract_email(text_all)

    # Homepage (personal lab page)
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('http') and base_url not in href and 'snu.ac.kr' not in href:
            text = clean(a.get_text()).lower()
            if any(kw in text for kw in ['homepage', 'lab', 'laboratory', 'website', '홈페이지']):
                partial['homepage'] = href
                break

    # Bio / research description
    bio_candidates = []
    for el in soup.find_all(['p', 'div'], class_=re.compile(r'bio|about|intro|description|research', re.I)):
        t = clean(el.get_text())
        if len(t) > 50:
            bio_candidates.append(t)
    if bio_candidates:
        partial['bio'] = max(bio_candidates, key=len)[:800]

    # Research areas (more likely on individual page)
    if not partial.get('research_areas'):
        for el in soup.find_all(['p', 'li', 'td', 'div']):
            t = clean(el.get_text())
            if any(kw in t for kw in ['연구분야', '관심분야', 'Research Area', 'Research Interest']):
                areas = parse_research_areas(t)
                if areas:
                    partial['research_areas'] = areas
                    break

    # Joined year
    m = re.search(r'(19|20)\d{2}', text_all)
    if m:
        yr = int(m.group(0))
        if 1970 <= yr <= 2024:
            partial.setdefault('joined_year', yr)

    # Better photo
    if not partial.get('photo_url'):
        for img in soup.find_all('img'):
            src = img.get('src') or ''
            if any(kw in src.lower() for kw in ['photo', 'profile', 'faculty', 'professor']):
                partial['photo_url'] = urljoin(base_url, src)
                break

    return partial


# ─── Main scrape strategies ───────────────────────────────────────────────────

def scrape_dept(config: dict) -> list[dict]:
    """Try primary URL then alt_urls; try multiple card selectors."""
    urls_to_try = [config['url']] + config.get('alt_urls', [])
    soup = None
    used_url = None

    for url in urls_to_try:
        print(f'  → Trying: {url}')
        soup = fetch_page(url)
        if soup:
            used_url = url
            break

    if not soup:
        print(f'  [✗] All URLs failed for {config["name"]}')
        return []

    base_url = get_base_url(used_url)

    # ── Strategy A: Known card selectors ──────────────────────────────
    cards = []
    for sel in CARD_SELECTORS:
        found = soup.select(sel)
        if found and len(found) >= 2:
            cards = found
            print(f'  [A] {len(cards)} cards with selector "{sel}"')
            break

    # ── Strategy B: Find profile links, scrape each ───────────────────
    if not cards:
        links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if PROFILE_LINK_PATTERNS.search(href):
                links.add(urljoin(base_url, href))
        if links:
            print(f'  [B] {len(links)} profile links found')
            return scrape_from_links(list(links), config, base_url)

    # ── Strategy C: Any element containing a Korean name + email ──────
    if not cards:
        candidates = []
        for el in soup.find_all(['tr', 'li', 'div', 'article']):
            t = el.get_text()
            if re.search(r'[가-힣]{2,5}', t) and ('@' in t or '교수' in t):
                candidates.append(el)
        if candidates:
            cards = candidates
            print(f'  [C] {len(cards)} fallback elements')

    if not cards:
        print(f'  [✗] No structured data found')
        return []

    # Extract from cards
    professors = []
    seen = set()
    for card in cards:
        prof = extract_from_card(card, config, base_url)
        if prof and prof['name_kr'] and prof['name_kr'] not in seen:
            seen.add(prof['name_kr'])
            professors.append(prof)

    # Deep-scrape individual pages for richer data
    enriched = []
    for prof in professors:
        if prof.get('profile_url') and prof['profile_url'] != used_url:
            time.sleep(0.4)
            prof = deep_scrape_profile(prof['profile_url'], prof, base_url)
        enriched.append(prof)

    return enriched


def scrape_from_links(links: list[str], config: dict, base_url: str) -> list[dict]:
    professors = []
    seen = set()
    for url in links[:60]:
        time.sleep(0.4)
        soup = fetch_page(url)
        if not soup:
            continue

        prof = {'college': config['college'], 'department': config['name'],
                'profile_url': url, 'research_areas': []}

        h = soup.find('h1') or soup.find('h2') or soup.find('h3')
        if h:
            t = clean(h.get_text())
            m = re.search(r'[가-힣]{2,5}', t)
            if m:
                prof['name_kr'] = m.group(0)
            m2 = re.search(r'[A-Z][a-z]+(?:\s+\w+){1,2}', t)
            if m2:
                prof['name_en'] = m2.group(0)

        if not prof.get('name_kr') or prof['name_kr'] in seen:
            continue
        seen.add(prof['name_kr'])

        text_all = soup.get_text()
        prof['email'] = extract_email(text_all)
        prof['position'] = extract_position(text_all)

        img = soup.find('img')
        if img:
            src = img.get('src') or ''
            prof['photo_url'] = urljoin(base_url, src)

        prof = deep_scrape_profile(url, prof, base_url)
        professors.append(prof)

    return professors


# ─── CLI ───────────────────────────────────────────────────────────────────────

def crawl_dept(key: str, fetch_papers: bool = True) -> int:
    config = DEPARTMENTS[key]
    print(f'\n{"═"*60}')
    print(f'  {config["college"]}  ▸  {config["name"]}')
    print(f'{"═"*60}')

    professors = scrape_dept(config)
    print(f'  Found {len(professors)} professors')

    saved = 0
    for prof in professors:
        try:
            prof_id = database.upsert_professor(prof)

            if fetch_papers:
                name = prof.get('name_en') or prof.get('name_kr', '')
                if name:
                    papers = fetch_papers_for_professor(name, prof.get('name_kr'))
                    if papers:
                        database.upsert_papers(prof_id, papers)
                        print(f'    {prof.get("name_kr")}: {len(papers)} papers')
                time.sleep(0.3)

            saved += 1
        except Exception as e:
            print(f'  [!] Error saving {prof.get("name_kr")}: {e}')

    return saved


def main():
    parser = argparse.ArgumentParser(description='SNU Faculty Crawler')
    parser.add_argument('--dept', default='all',
                        help='Dept key or comma-separated list or "all"')
    parser.add_argument('--list', action='store_true', help='List departments')
    parser.add_argument('--no-papers', action='store_true', help='Skip paper fetching')
    args = parser.parse_args()

    if args.list:
        print('\n  Key            College                    Department')
        print('  ─' * 25)
        for k, v in DEPARTMENTS.items():
            print(f'  {k:<14} {v["college"]:<26} {v["name"]}')
        return

    database.init_db()
    fetch_papers = not args.no_papers
    total = 0

    if args.dept == 'all':
        keys = list(DEPARTMENTS.keys())
    else:
        keys = [k.strip() for k in args.dept.split(',') if k.strip() in DEPARTMENTS]
        invalid = [k.strip() for k in args.dept.split(',') if k.strip() not in DEPARTMENTS]
        if invalid:
            print(f'[!] Unknown dept keys: {", ".join(invalid)}')

    for key in keys:
        count = crawl_dept(key, fetch_papers=fetch_papers)
        total += count
        time.sleep(1.5)

    print(f'\n✓  Done. Total saved/updated: {total}')


if __name__ == '__main__':
    main()
