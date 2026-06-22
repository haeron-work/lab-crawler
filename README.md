# 🎓 SNU Faculty Explorer

서울대학교 교수 프로필, 연구분야, 논문을 한 곳에서 탐색할 수 있는 웹 애플리케이션입니다.

**Features:**
- 🔍 **다중 탐색**: 학부/학과별 계층 탐색 + 키워드 검색 + 태그 클라우드
- 📊 **상세 프로필**: 교수 사진, 약력, 연구분야, 논문(대표/최근/전체 분류)
- 🎯 **스마트 필터**: 직위, 학과, 연구분야, 정렬 옵션
- 🔐 **개인용**: 로컬에서만 실행되는 데이터베이스
- 🚀 **자동 갱신**: GitHub Actions 기반 크롤러로 주기적 업데이트 가능

---

## 🛠 Setup

### 1. 의존성 설치

```bash
# 가상 환경 생성 (선택사항)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는: venv\Scripts\activate  # Windows

# 패키지 설치
pip install -r requirements.txt
```

**의존성:**
- `Flask` — 웹 서버
- `beautifulsoup4` — 웹 크롤링
- `requests` — HTTP 요청
- `Flask-CORS` — 크로스 오리진 지원

### 2. 교수 데이터 수집

```bash
# 전체 부서 크롤링 (⏱️ ~30-40분)
python crawler.py

# 특정 부서만 (예: 전기정보, 컴퓨터, 재료공학)
python crawler.py --dept ee,cse,mse

# 논문 없이 빠르게 (⏱️ ~5분)
python crawler.py --no-papers

# 사용 가능한 부서 목록
python crawler.py --list
```

**크롤러 출력:**
```
════════════════════════════════════════════════════
  공과대학  ▸  컴퓨터공학부
════════════════════════════════════════════════════
  → Trying: https://cse.snu.ac.kr/people/faculty
  [A] 42 cards with selector ".faculty-item"
  Found 42 professors
  cs_prof1: 35 papers
  cs_prof2: 28 papers
  ...
  ✓  Done. Total saved/updated: 42
```

### 3. 웹 서버 실행

```bash
python app.py
```

브라우저에서 **http://localhost:5050** 열기

---

## 📖 사용법

### 🔍 검색 & 탐색

| 기능 | 방법 |
|------|------|
| **빠른 검색** | 상단 검색창 (이름, 연구분야, 실험실명) |
| **키워드 단축키** | `⌘K` / `Ctrl+K` |
| **계층 탐색** | 좌측 사이드바 → 학부 → 학과 선택 |
| **직위 필터** | 교수, 부교수, 조교수, 명예교수 |
| **연구 키워드** | 우측 태그로 검색 및 정렬 |
| **태그 클라우드** | 상단 "키워드" 버튼으로 전체 분야 탐색 |

### 📋 보기 모드

- **카드 뷰** (기본): 사진, 이름, 직위, 연구분야 한눈에
- **목록 뷰**: 밀집된 정보 표시
- **태그 클라우드**: 키워드 기반 탐색

### 👤 교수 프로필

카드 클릭 → 사이드 패널 열기:

- ✓ 프로필 사진 & 기본 정보
- ✓ 이메일, 연구실, 홈페이지
- ✓ 연구분야 태그 (클릭하면 관련 교수 필터링)
- ✓ **논문** (대표/최근/전체 탭):
  - 제목, 저널, 연도, 인용수
  - DOI, arXiv 링크
  - 요약 보기/접기

---

## 📂 프로젝트 구조

```
snu-explorer/
├── app.py              # Flask 웹 서버
├── crawler.py          # SNU 교수 웹사이트 크롤러
├── paper_fetcher.py    # Semantic Scholar + arXiv API
├── database.py         # SQLite 데이터베이스 계층
├── requirements.txt    # Python 의존성
├── setup.sh           # 초기 설정 스크립트
├── README.md          # 이 파일
├── data/
│   └── faculty.db     # SQLite 데이터베이스 (자동 생성)
└── static/
    ├── index.html      # UI 구조
    ├── style.css       # 다크 모드 디자인
    └── app.js          # 프론트엔드 로직
```

---

## 🔧 크롤러 상세

### 지원 부서 (30+개)

**공과대학 (13개)**
- `ee` 전기·정보공학부
- `cse` 컴퓨터공학부
- `me` 기계공학부
- `mse` 재료공학부
- `cbe` 화학생물공학부
- `civil` 건설환경공학부
- `ie` 산업공학과
- `aerospace` 항공우주공학과
- `nuclear` 원자핵공학과
- `naoe` 조선해양공학과
- `energy` 에너지자원공학과
- `arch` 건축학과
- `archeng` 건축공학과

**자연과학대학 (6개)**
- `math` 수리과학부
- `stat` 통계학과
- `physics` 물리·천문학부
- `chem` 화학부
- `biosci` 생명과학부
- `ees` 지구환경과학부

**기타 단과대학 (11개)**
- 농업생명과학대학, 의과대학, 치의학대학원, 약학대학, 사범대학, 경영대학, 사회과학대학

### 크롤링 전략

1. **SNU 부서 웹사이트** 자동 탐지
   - 일관된 카드 구조 해석
   - 여러 선택자 패턴 시도 (fallback)
   
2. **개별 교수 프로필** 깊이 분석
   - 사진, 이메일, 연구실 정보
   - 연구분야 추출
   - 개인 홈페이지 링크

3. **논문 수집** (Semantic Scholar + arXiv)
   - Semantic Scholar API로 주요 논문
   - arXiv 백업 (접근 불가 시)
   - 인용수 기반 대표논문 자동 분류

### 필터 & 정렬

```
필터: --dept [key,key,...]  부서별 선택
      --no-papers            논문 수집 제외 (빠름)

정렬: --sort [name_kr | name_en | joined | department | updated]
```

---

## 📊 데이터베이스 스키마

### professors
```
id              INTEGER PRIMARY KEY
name_kr         TEXT (필수)
name_en         TEXT
college         TEXT
department      TEXT
position        TEXT (교수, 부교수, 조교수, 명예교수, ...)
email           TEXT
phone           TEXT
office          TEXT
lab             TEXT (연구실명)
research_areas  JSON (["분야1", "분야2", ...])
bio             TEXT
photo_url       TEXT
profile_url     TEXT (SNU 프로필 링크)
homepage        TEXT
joined_year     INTEGER
updated_at      TIMESTAMP
```

### papers
```
id              INTEGER PRIMARY KEY
professor_id    INTEGER (Foreign Key)
title           TEXT
authors         TEXT
venue           TEXT (저널명, arXiv)
year            INTEGER
doi             TEXT
arxiv_id        TEXT
abstract        TEXT
citations       INTEGER
paper_type      TEXT (representative | recent | other)
url             TEXT
```

---

## 🎨 UI/UX 특성

- **다크 모드** (학술적 분위기)
- **반응형 레이아웃** (데스크탑 최적화, 태블릿 지원)
- **키보드 네비게이션** (`⌘K` 검색, `ESC` 패널 닫기)
- **부드러운 애니메이션** (카드 페이드인, 패널 슬라이드)
- **SNU 색상 테마** (블루 #5B8FE8 강조)

---

## 🔒 개인정보 & 저작권

- **로컬 전용**: 모든 데이터는 로컬 SQLite에만 저장
- **공개 API 사용**: Semantic Scholar, arXiv (규약 준수)
- **SNU 데이터**: 공개 웹사이트만 크롤링
- **논문 메타데이터**: 접근/교육 목적

---

## 🐛 Troubleshooting

### "No modules named Flask"
```bash
pip install -r requirements.txt
```

### "서버 연결 실패"
1. `python app.py` 실행 확인
2. http://localhost:5050 접속
3. 포트 충돌 시: `PORT=5051 python app.py`

### "데이터 없음"
```bash
# 크롤러 실행
python crawler.py --dept cse,mse  # 빠른 테스트

# 진행 상황 보기 (크롤 중)
python crawler.py 2>&1 | tee crawl.log
```

### "논문 데이터 부족"
- 논문 크롤링은 **선택사항**
- Semantic Scholar API 연결 확인 (rate limit 주의)
- arXiv는 무료 공개 API

---

## 📈 향후 개선 사항

- [ ] GitHub Actions 기반 주기적 크롤링 자동화
- [ ] KakaoTalk 봇 알림
- [ ] PDF 논문 다운로드 링크 통합
- [ ] 연구비 수주 현황
- [ ] 학생 정보 (석박사 과정)
- [ ] 협업 네트워크 시각화

---

## 📝 License

MIT License — 개인 학습 & 연구 목적 사용

---

**Made for exploring SNU's research landscape** 🇰🇷
