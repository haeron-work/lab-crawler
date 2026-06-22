/* ══════════════════════════════════════════════════════════════
   SNU Faculty Explorer — app.js (static / GitHub Pages build)
   All data loaded from data.json; filtering done in-memory.
   ══════════════════════════════════════════════════════════════ */

'use strict';

// ─── State ──────────────────────────────────────────────────────────────────

const state = {
  all:        [],   // master list — never mutated
  keywords:   [],   // { keyword, count }[]
  colleges:   [],   // college tree

  view: 'grid',
  filters: {
    college:    '',
    department: '',
    keyword:    '',
    search:     '',
    sort:       'name_kr',
    position:   '',
  },
  activeKeyword: '',
};

// ─── Data loading ────────────────────────────────────────────────────────────

async function loadData() {
  // Support both GitHub Pages (data.json) and local http.server
  const paths = ['data.json', './data.json', '../static/data.json'];
  for (const path of paths) {
    try {
      const res = await fetch(path);
      if (res.ok) return res.json();
    } catch (_) { /* try next */ }
  }
  throw new Error('data.json not found — run: python crawler.py && python export.py');
}

// ─── Compute helpers ─────────────────────────────────────────────────────────

function computeKeywords(profs) {
  const counts = {};
  profs.forEach(p => {
    (p.research_areas || []).forEach(a => {
      if (a) counts[a] = (counts[a] || 0) + 1;
    });
  });
  return Object.entries(counts)
    .map(([keyword, count]) => ({ keyword, count }))
    .sort((a, b) => b.count - a.count);
}

function computeColleges(profs) {
  const map = {};
  profs.forEach(p => {
    const c = p.college    || '기타';
    const d = p.department || '기타';
    if (!map[c]) map[c] = { name: c, depts: {}, total: 0 };
    map[c].depts[d] = (map[c].depts[d] || 0) + 1;
    map[c].total++;
  });
  return Object.values(map).map(c => ({
    name:        c.name,
    total:       c.total,
    departments: Object.entries(c.depts)
                   .map(([name, count]) => ({ name, count }))
                   .sort((a, b) => a.name.localeCompare(b.name)),
  })).sort((a, b) => a.name.localeCompare(b.name));
}

function computeStats(profs) {
  const colleges   = new Set(profs.map(p => p.college)).size;
  const departments= new Set(profs.map(p => p.department)).size;
  const papers     = profs.reduce((s, p) => s + (p.papers?.length || 0), 0);
  return { professors: profs.length, colleges, departments, papers };
}

// ─── Filtering & sorting ─────────────────────────────────────────────────────

const SORT_FNS = {
  name_kr:    (a, b) => (a.name_kr || '').localeCompare(b.name_kr || '', 'ko'),
  name_en:    (a, b) => (a.name_en || a.name_kr || '').localeCompare(b.name_en || b.name_kr || ''),
  joined:     (a, b) => (b.joined_year || 0) - (a.joined_year || 0) || (a.name_kr || '').localeCompare(b.name_kr || '', 'ko'),
  department: (a, b) => (a.department || '').localeCompare(b.department || '', 'ko') || (a.name_kr || '').localeCompare(b.name_kr || '', 'ko'),
  updated:    (a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''),
};

function applyFilters() {
  const f = state.filters;
  let result = state.all;

  if (f.college)    result = result.filter(p => p.college === f.college);
  if (f.department) result = result.filter(p => p.department === f.department);
  if (f.position)   result = result.filter(p => p.position === f.position);

  if (f.keyword) {
    const kw = f.keyword.toLowerCase();
    result = result.filter(p =>
      (p.research_areas || []).join(' ').toLowerCase().includes(kw) ||
      (p.bio  || '').toLowerCase().includes(kw) ||
      (p.lab  || '').toLowerCase().includes(kw)
    );
  }

  if (f.search) {
    const s = f.search.toLowerCase();
    result = result.filter(p =>
      (p.name_kr  || '').includes(s) ||
      (p.name_en  || '').toLowerCase().includes(s) ||
      (p.research_areas || []).join(' ').toLowerCase().includes(s) ||
      (p.lab      || '').toLowerCase().includes(s) ||
      (p.email    || '').toLowerCase().includes(s)
    );
  }

  const sortFn = SORT_FNS[f.sort] || SORT_FNS.name_kr;
  result = [...result].sort(sortFn);

  renderProfessors(result);
  document.getElementById('result-count').textContent = `${result.length}명`;
  updateActiveFilterBadge();
}

// ─── Render helpers ──────────────────────────────────────────────────────────

function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function posClass(pos) {
  const map = { '교수':'교수','부교수':'부교수','조교수':'조교수','명예교수':'명예교수','석좌교수':'석좌교수' };
  return 'pos-' + (map[pos] || 'default');
}

function initials(name_kr, name_en) {
  if (name_kr && /[가-힣]/.test(name_kr)) return name_kr[0];
  if (name_en) return name_en.split(' ').filter(Boolean).map(w => w[0]).join('').slice(0,2).toUpperCase();
  return '?';
}

function areaTagsHtml(areas, max = 3) {
  if (!areas?.length) return '';
  const shown = areas.slice(0, max).map(a => `<span class="area-tag" title="${esc(a)}">${esc(a)}</span>`).join('');
  const more  = areas.length > max ? `<span class="area-tag">+${areas.length - max}</span>` : '';
  return shown + more;
}

// ─── Cards ───────────────────────────────────────────────────────────────────

function renderCard(p) {
  const inits  = initials(p.name_kr, p.name_en);
  const posCls = posClass(p.position);
  const photo  = p.photo_url
    ? `<img class="card-photo" src="${esc(p.photo_url)}" alt="${esc(p.name_kr)}" loading="lazy"
            onerror="this.parentElement.innerHTML='<div class=\\"card-photo-placeholder\\">${esc(inits)}</div>'">`
    : `<div class="card-photo-placeholder">${esc(inits)}</div>`;

  return `
  <div class="prof-card" data-id="${p.id}" role="button" tabindex="0">
    <div class="card-photo-wrap">${photo}</div>
    <div class="card-body">
      <div class="card-name-kr">${esc(p.name_kr)}</div>
      ${p.name_en ? `<div class="card-name-en">${esc(p.name_en)}</div>` : ''}
      <div class="card-meta">
        <span class="card-position ${posCls}">${esc(p.position || '교수')}</span>
        <span class="card-dept">${esc(p.department || '')}</span>
      </div>
      ${(p.research_areas||[]).length ? `<div class="card-areas">${areaTagsHtml(p.research_areas, 3)}</div>` : ''}
      <div class="card-footer">
        <span class="card-paper-count">${p.papers?.length ? `논문 ${p.papers.length}편` : ''}</span>
        ${p.email ? `<span class="card-email">${esc(p.email)}</span>` : ''}
      </div>
    </div>
  </div>`;
}

function renderListItem(p) {
  const inits  = initials(p.name_kr, p.name_en);
  const posCls = posClass(p.position);
  const thumb  = p.photo_url
    ? `<div class="list-thumb"><img src="${esc(p.photo_url)}" alt="${esc(p.name_kr)}"
            onerror="this.outerHTML='<div class=\\"list-thumb\\">${esc(inits)}</div>'"></div>`
    : `<div class="list-thumb">${esc(inits)}</div>`;

  const areas  = (p.research_areas || []).slice(0,4).map(a => `<span class="area-tag">${esc(a)}</span>`).join('');

  return `
  <div class="list-item" data-id="${p.id}" role="button" tabindex="0">
    ${thumb}
    <div style="display:flex;flex-direction:column;gap:1px;min-width:70px">
      <div class="list-name-kr">${esc(p.name_kr)}</div>
      ${p.name_en ? `<div class="list-name-en">${esc(p.name_en)}</div>` : ''}
    </div>
    <span class="card-position ${posCls}" style="flex-shrink:0">${esc(p.position||'교수')}</span>
    <span class="list-sep">·</span>
    <span class="list-dept">${esc(p.department||'')} · ${esc(p.college||'')}</span>
    <div class="list-areas" style="margin-left:auto">${areas}</div>
  </div>`;
}

function renderProfessors(profs) {
  const grid  = document.getElementById('view-grid');
  const list  = document.getElementById('view-list');
  const empty = document.getElementById('empty-state');

  empty.style.display = profs.length ? 'none' : 'flex';
  grid.innerHTML = profs.map(renderCard).join('');
  list.innerHTML = profs.map(renderListItem).join('');

  document.querySelectorAll('.prof-card, .list-item').forEach(el => {
    el.addEventListener('click', () => openPanel(+el.dataset.id));
    el.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openPanel(+el.dataset.id); }
    });
  });
}

// ─── Side Panel ──────────────────────────────────────────────────────────────

function openPanel(profId) {
  const p       = state.all.find(x => x.id === profId);
  const panel   = document.getElementById('side-panel');
  const overlay = document.getElementById('panel-overlay');

  if (!p) return;
  overlay.style.display = 'block';
  panel.classList.add('open');
  document.getElementById('panel-content').innerHTML = buildPanelHTML(p);
  initPanelInteractions(document.getElementById('panel-content'), p);
}

function closePanel() {
  document.getElementById('side-panel').classList.remove('open');
  document.getElementById('panel-overlay').style.display = 'none';
}

function buildPanelHTML(p) {
  const areas  = p.research_areas || [];
  const papers = p.papers || [];
  const posCls = posClass(p.position);
  const inits  = initials(p.name_kr, p.name_en);

  const repPapers    = papers.filter(x => x.paper_type === 'representative');
  const recentPapers = papers.filter(x => x.paper_type === 'recent');
  const otherPapers  = papers.filter(x => x.paper_type === 'other');

  const photoHTML = p.photo_url
    ? `<img class="panel-photo" src="${esc(p.photo_url)}" alt="${esc(p.name_kr)}"
            onerror="this.outerHTML='<div class=\\"panel-photo\\">${esc(inits)}</div>'">`
    : `<div class="panel-photo">${esc(inits)}</div>`;

  const contacts = [
    p.email      && `<div class="contact-item"><span class="contact-label">이메일</span><a href="mailto:${esc(p.email)}">${esc(p.email)}</a></div>`,
    p.phone      && `<div class="contact-item"><span class="contact-label">전화</span><span>${esc(p.phone)}</span></div>`,
    p.office     && `<div class="contact-item"><span class="contact-label">연구실</span><span>${esc(p.office)}</span></div>`,
    p.lab        && `<div class="contact-item"><span class="contact-label">연구실명</span><span>${esc(p.lab)}</span></div>`,
    p.homepage   && `<div class="contact-item"><span class="contact-label">홈페이지</span><a href="${esc(p.homepage)}" target="_blank" rel="noopener">${esc(p.homepage.replace(/^https?:\/\//,''))}</a></div>`,
    p.profile_url && `<div class="contact-item"><span class="contact-label">SNU 프로필</span><a href="${esc(p.profile_url)}" target="_blank" rel="noopener">바로가기 ↗</a></div>`,
  ].filter(Boolean).join('');

  return `
  <div class="panel-hero">
    ${photoHTML}
    <div class="panel-identity">
      <div class="panel-name-kr">${esc(p.name_kr)}</div>
      ${p.name_en ? `<div class="panel-name-en">${esc(p.name_en)}</div>` : ''}
      <div class="panel-badges">
        <span class="card-position ${posCls}">${esc(p.position || '교수')}</span>
      </div>
      <div class="panel-dept-label">${esc(p.department || '')}</div>
      <div class="panel-college-label">${esc(p.college || '')}</div>
    </div>
  </div>

  ${contacts ? `
  <div class="panel-section">
    <div class="panel-section-title">연락처 · 링크</div>
    <div class="panel-contact-list">${contacts}</div>
  </div>` : ''}

  ${areas.length ? `
  <div class="panel-section">
    <div class="panel-section-title">연구 분야</div>
    <div class="panel-areas">
      ${areas.map(a => `<span class="panel-area-tag" data-area="${esc(a)}">${esc(a)}</span>`).join('')}
    </div>
  </div>` : ''}

  ${p.bio ? `
  <div class="panel-section">
    <div class="panel-section-title">소개</div>
    <div class="panel-bio">${esc(p.bio)}</div>
  </div>` : ''}

  <div class="panel-section">
    <div class="panel-section-title">논문</div>
    <div class="paper-tabs">
      <button class="paper-tab active" data-tab="representative">★ 대표 <span style="opacity:.5">(${repPapers.length})</span></button>
      <button class="paper-tab" data-tab="recent">최근 <span style="opacity:.5">(${recentPapers.length})</span></button>
      <button class="paper-tab" data-tab="other">전체 <span style="opacity:.5">(${otherPapers.length})</span></button>
    </div>
    <div id="paper-list-container">${renderPaperList(repPapers)}</div>
  </div>`;
}

function paperHTML(p) {
  const typeLabel = { representative:'대표', recent:'최근', other:'' };
  const typeCls   = { representative:'pt-representative', recent:'pt-recent', other:'pt-other' };
  const label = typeLabel[p.paper_type] || '';
  const cls   = typeCls[p.paper_type]  || 'pt-other';
  const href  = p.url || (p.doi ? 'https://doi.org/'+p.doi : (p.arxiv_id ? 'https://arxiv.org/abs/'+p.arxiv_id : ''));
  const titleHTML = href
    ? `<a href="${esc(href)}" target="_blank" rel="noopener">${esc(p.title)}</a>`
    : esc(p.title);

  const meta = [
    p.venue      && `<span class="paper-venue">${esc(p.venue)}</span>`,
    p.year       && `<span>${p.year}</span>`,
    p.citations  > 0 && `<span class="paper-citations">인용 ${p.citations}</span>`,
    p.doi        && `<a href="https://doi.org/${esc(p.doi)}" target="_blank" style="color:var(--accent)">DOI</a>`,
    p.arxiv_id   && `<a href="https://arxiv.org/abs/${esc(p.arxiv_id)}" target="_blank" style="color:var(--accent)">arXiv</a>`,
  ].filter(Boolean).join('');

  return `
  <div class="paper-item">
    ${label ? `<div class="paper-type-badge ${cls}">${label}</div>` : ''}
    <div class="paper-title">${titleHTML}</div>
    ${p.authors ? `<div style="font-size:.72rem;color:var(--text-muted);margin-bottom:4px">${esc(p.authors)}</div>` : ''}
    <div class="paper-meta">${meta}</div>
    ${p.abstract ? `<div class="paper-abstract" id="pabs-${p.id}">${esc(p.abstract)}</div>
    <button class="expand-abstract" data-abs="${p.id}">전체 보기</button>` : ''}
  </div>`;
}

function renderPaperList(papers) {
  if (!papers.length) return `<div class="no-papers">논문 데이터 없음<br><small>python crawler.py 실행 후 갱신</small></div>`;
  return `<div class="paper-list">${papers.map(paperHTML).join('')}</div>`;
}

function initPanelInteractions(content, p) {
  content.querySelectorAll('.paper-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      content.querySelectorAll('.paper-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const which = tab.dataset.tab;
      const all   = p.papers || [];
      const filtered = all.filter(x => x.paper_type === which);
      content.querySelector('#paper-list-container').innerHTML = renderPaperList(filtered);
      initExpandButtons(content);
    });
  });

  initExpandButtons(content);

  content.querySelectorAll('.panel-area-tag').forEach(tag => {
    tag.addEventListener('click', () => {
      closePanel();
      state.filters.keyword = tag.dataset.area;
      state.activeKeyword   = tag.dataset.area;
      applyFilters();
      refreshChips();
    });
  });
}

function initExpandButtons(content) {
  content.querySelectorAll('.expand-abstract').forEach(btn => {
    btn.addEventListener('click', () => {
      const el = content.querySelector(`#pabs-${btn.dataset.abs}`);
      if (el) {
        el.classList.toggle('expanded');
        btn.textContent = el.classList.contains('expanded') ? '접기' : '전체 보기';
      }
    });
  });
}

// ─── College Tree ─────────────────────────────────────────────────────────────

function renderCollegeTree(colleges) {
  const tree = document.getElementById('college-tree');
  if (!colleges.length) {
    tree.innerHTML = '<div class="tree-loading">데이터 없음 — 크롤러 실행 필요</div>';
    return;
  }

  tree.innerHTML = colleges.map(c => `
    <div class="college-node" data-college="${esc(c.name)}">
      <div class="college-header">
        <span class="college-name">
          <svg class="college-arrow" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 4l4 4-4 4"/>
          </svg>
          ${esc(c.name)}
        </span>
        <span class="college-count">${c.total}</span>
      </div>
      <div class="dept-list">
        <div class="dept-item" data-college="${esc(c.name)}" data-dept="">
          전체 <span class="dept-count">${c.total}</span>
        </div>
        ${c.departments.map(d => `
          <div class="dept-item" data-college="${esc(c.name)}" data-dept="${esc(d.name)}">
            ${esc(d.name)} <span class="dept-count">${d.count}</span>
          </div>
        `).join('')}
      </div>
    </div>
  `).join('');

  tree.querySelectorAll('.college-header').forEach(h => {
    h.addEventListener('click', () => {
      const node = h.closest('.college-node');
      const wasOpen = node.classList.contains('open');
      if (!wasOpen) {
        node.classList.add('open');
        setCollegeFilter(node.dataset.college, '');
      } else {
        node.classList.toggle('open');
      }
    });
  });

  tree.querySelectorAll('.dept-item').forEach(item => {
    item.addEventListener('click', e => {
      e.stopPropagation();
      setCollegeFilter(item.dataset.college, item.dataset.dept);
      item.closest('.college-node').classList.add('open');
      tree.querySelectorAll('.dept-item').forEach(d => d.classList.remove('active'));
      item.classList.add('active');
    });
  });
}

function setCollegeFilter(college, dept) {
  state.filters.college    = college;
  state.filters.department = dept;
  applyFilters();
}

// ─── Keyword chips & cloud ────────────────────────────────────────────────────

function renderKeywordSuggestions(keywords) {
  const container = document.getElementById('keyword-suggestions');
  container.innerHTML = keywords.slice(0, 20).map(kw => `
    <span class="kw-chip" data-kw="${esc(kw.keyword)}">${esc(kw.keyword)} <small>${kw.count}</small></span>
  `).join('');

  container.querySelectorAll('.kw-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const kw = chip.dataset.kw;
      const active = chip.classList.contains('active');
      container.querySelectorAll('.kw-chip').forEach(c => c.classList.remove('active'));
      state.filters.keyword = active ? '' : kw;
      state.activeKeyword   = active ? '' : kw;
      if (!active) chip.classList.add('active');
      document.getElementById('keyword-search').value = '';
      applyFilters();
    });
  });
}

document.getElementById('keyword-search').addEventListener('input', e => {
  const q = e.target.value.trim();
  document.querySelectorAll('.kw-chip').forEach(c => {
    c.style.display = !q || c.dataset.kw.includes(q) ? '' : 'none';
  });
});

function renderTagCloud(keywords) {
  const cloud = document.getElementById('tag-cloud');
  if (!keywords.length) { cloud.innerHTML = '<p style="color:var(--text-muted)">데이터 없음</p>'; return; }

  const maxC = keywords[0].count;
  const minC = keywords[keywords.length - 1].count || 1;
  const range = maxC - minC || 1;

  cloud.innerHTML = keywords.slice(0, 80).map(kw => {
    const t = (kw.count - minC) / range;
    const size = (0.72 + t * 0.78).toFixed(2);
    const op   = (0.45 + t * 0.55).toFixed(2);
    return `<span class="cloud-tag" data-kw="${esc(kw.keyword)}" style="font-size:${size}rem;opacity:${op}">
      ${esc(kw.keyword)}<span class="cloud-tag-count">${kw.count}</span>
    </span>`;
  }).join('');

  cloud.querySelectorAll('.cloud-tag').forEach(tag => {
    tag.addEventListener('click', () => {
      const kw = tag.dataset.kw;
      const active = tag.classList.contains('active');
      cloud.querySelectorAll('.cloud-tag').forEach(t => t.classList.remove('active'));
      state.filters.keyword = active ? '' : kw;
      state.activeKeyword   = active ? '' : kw;
      if (!active) { tag.classList.add('active'); switchView('grid'); }
      applyFilters();
    });
  });
}

function refreshChips() {
  document.querySelectorAll('.kw-chip').forEach(c =>
    c.classList.toggle('active', c.dataset.kw === state.activeKeyword)
  );
  document.querySelectorAll('.cloud-tag').forEach(t =>
    t.classList.toggle('active', t.dataset.kw === state.activeKeyword)
  );
  document.querySelectorAll('.dept-item').forEach(item =>
    item.classList.toggle('active',
      item.dataset.college === state.filters.college &&
      item.dataset.dept    === state.filters.department
    )
  );
}

// ─── Stats ────────────────────────────────────────────────────────────────────

function renderStats(stats, generatedAt) {
  document.getElementById('stat-profs').textContent  = `${stats.professors}명`;
  document.getElementById('stat-depts').textContent  = `${stats.departments}개 학과`;
  document.getElementById('stat-papers').textContent = `${stats.papers.toLocaleString()}편 논문`;

  if (generatedAt) {
    const d = new Date(generatedAt);
    document.getElementById('stat-papers').title = `갱신: ${d.toLocaleDateString('ko-KR')}`;
  }
}

// ─── Active filter badges ─────────────────────────────────────────────────────

function updateActiveFilterBadge() {
  const badge    = document.getElementById('active-keyword-badge');
  const clearBtn = document.getElementById('clear-all-btn');
  const wrap     = document.getElementById('active-filters-wrap');
  const container= document.getElementById('active-filters');

  const tags = [
    state.filters.college    && { label: state.filters.college,    key: 'college' },
    state.filters.department && { label: state.filters.department, key: 'department' },
    state.filters.keyword    && { label: '🏷 ' + state.filters.keyword, key: 'keyword' },
    state.filters.position   && { label: state.filters.position,   key: 'position' },
  ].filter(Boolean);

  wrap.style.display = tags.length ? '' : 'none';
  container.innerHTML = tags.map(t => `
    <span class="active-filter-tag">
      ${esc(t.label)}<button data-key="${t.key}">×</button>
    </span>
  `).join('');

  container.querySelectorAll('button[data-key]').forEach(btn => {
    btn.addEventListener('click', () => {
      const key = btn.dataset.key;
      state.filters[key] = '';
      if (key === 'keyword') state.activeKeyword = '';
      if (key === 'college') state.filters.department = '';
      applyFilters();
      refreshChips();
    });
  });

  badge.style.display = state.filters.keyword ? '' : 'none';
  if (state.filters.keyword) badge.textContent = '🏷 ' + state.filters.keyword;

  const hasAny = Object.entries(state.filters).some(([k,v]) => v && k !== 'sort');
  clearBtn.style.display = hasAny ? '' : 'none';
}

// ─── View switching ───────────────────────────────────────────────────────────

function switchView(v) {
  state.view = v;
  document.getElementById('view-grid').style.display = v === 'grid' ? '' : 'none';
  document.getElementById('view-list').style.display = v === 'list' ? '' : 'none';
  document.getElementById('view-tags').style.display = v === 'tags' ? '' : 'none';
  document.getElementById('btn-grid').classList.toggle('active', v === 'grid');
  document.getElementById('btn-list').classList.toggle('active', v === 'list');
  document.getElementById('btn-tags').classList.toggle('active', v === 'tags');
}

// ─── Event listeners ──────────────────────────────────────────────────────────

let searchTimer;
document.getElementById('search-input').addEventListener('input', e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.filters.search = e.target.value.trim();
    applyFilters();
  }, 250);
});

document.getElementById('sort-select').addEventListener('change', e => {
  state.filters.sort = e.target.value;
  applyFilters();
});

document.querySelectorAll('input[data-filter="position"]').forEach(cb => {
  cb.addEventListener('change', () => {
    if (!cb.value) {
      state.filters.position = '';
      document.querySelectorAll('input[data-filter="position"][value]').forEach(c => {
        if (c.value) c.checked = false;
      });
    } else {
      document.querySelector('input[data-filter="position"][value=""]').checked = false;
      state.filters.position = cb.checked ? cb.value : '';
    }
    applyFilters();
  });
});

document.getElementById('btn-grid').addEventListener('click', () => switchView('grid'));
document.getElementById('btn-list').addEventListener('click', () => switchView('list'));
document.getElementById('btn-tags').addEventListener('click', () => switchView('tags'));

document.getElementById('panel-close').addEventListener('click', closePanel);
document.getElementById('panel-overlay').addEventListener('click', closePanel);

document.getElementById('clear-all-btn').addEventListener('click', () => {
  state.filters = { college:'', department:'', keyword:'', search:'', sort:'name_kr', position:'' };
  state.activeKeyword = '';
  document.getElementById('search-input').value = '';
  document.getElementById('sort-select').value = 'name_kr';
  document.querySelectorAll('input[data-filter="position"]').forEach(c => { c.checked = !c.value; });
  applyFilters();
  refreshChips();
});

document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    const inp = document.getElementById('search-input');
    inp.focus(); inp.select();
  }
  if (e.key === 'Escape') closePanel();
});

// ─── Init ─────────────────────────────────────────────────────────────────────

async function init() {
  document.getElementById('loading-state').style.display = 'flex';

  try {
    const data = await loadData();
    const profs = data.professors || [];

    state.all      = profs;
    state.keywords = computeKeywords(profs);
    state.colleges = computeColleges(profs);

    renderStats(computeStats(profs), data.generated_at);
    renderCollegeTree(state.colleges);
    renderKeywordSuggestions(state.keywords);
    renderTagCloud(state.keywords);
    applyFilters();

    if (!profs.length) {
      document.getElementById('empty-state').style.display = 'flex';
      document.querySelector('.empty-title').textContent = '데이터 없음';
      document.querySelector('.empty-sub').textContent = 'python crawler.py && python export.py 실행 후 새로고침';
    }

  } catch (err) {
    console.error(err);
    document.getElementById('loading-state').style.display = 'none';
    document.getElementById('empty-state').style.display = 'flex';
    document.querySelector('.empty-title').textContent = '로드 실패';
    document.querySelector('.empty-sub').textContent = err.message;
  } finally {
    document.getElementById('loading-state').style.display = 'none';
  }
}

init();
