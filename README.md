# 서울 주택 노후도 (seoul-housing-age.com)

서울 25개 자치구의 주택·아파트가 얼마나 오래됐는지 보여주는 정적 웹사이트입니다. 공공 통계만 쓰고, 매년 자동으로 갱신합니다. 투자 권유나 자문이 아닙니다.

## 페이지

| 경로 | 내용 |
|---|---|
| `/` | 2D 지도: 전체 30년+, 5년 증가폭, 아파트 30년+·20~30년, 저층 주택 20년+ |
| `/3d/` | 3D 지도 (three.js, 사이트 안에 포함) |
| `/gu/` · `/gu/<구>/` | 자치구 목록과 구별 상세 페이지 25개 (추이 차트, 지은 연도별 주택 수, 연도별 표) |
| `/projects/` | 정비사업 진행 현황 (기준월·출처 포함) |
| `/news/` | 서울시·국토교통부 보도자료 중 서울 주택·부동산 관련 자료 (제목·원문 링크, 매일 갱신) |
| `/methodology/` · `/data/` · `/about/` · `/privacy/` | 방법론, 데이터 출처, 소개, 개인정보처리방침 |

## 폴더 구조

```
config.json              사이트 이름, 도메인, 문의 이메일, 광고 ID
data/housing_age.json    자치구·연도별 주택 수 집계 (사이트의 모든 수치의 원천)
data/projects.json       정비사업 현황 (손으로 관리)
data/news.json           보도자료 모음 (자동 갱신, 제목·기관·날짜·링크만)
data/seoul_gu.geojson    자치구 경계
src/templates/           지도·3D 페이지 본문
src/assets/              CSS, JS, three.js, 아이콘, 공유 이미지
scripts/build.py         dist/ 에 사이트 생성 (표준 라이브러리만 사용)
scripts/fetch_data.py    서울 데이터 허브에서 원자료를 받아 housing_age.json 재생성
scripts/validate.py      데이터 검증 (합계, 연도 연속성, 기존 값과 비교)
scripts/fetch_news.py    서울시 보도자료 RSS·국토교통부 보도자료 목록에서 관련 자료 선별
.github/workflows/       deploy.yml (자동 배포), annual-update.yml (연 1회 갱신), news.yml (매일 보도자료)
```

## 로컬에서 보기

```bash
python scripts/build.py
cd dist && python -m http.server 8000   # http://localhost:8000
```

## 자동 배포와 연간 갱신

- `main` 브랜치에 변경이 올라오면 **Deploy site** 워크플로가 데이터를 검증하고 사이트를 빌드해 GitHub Pages에 배포합니다.
- **Annual data update** 워크플로는 매년 5월 1일 09:00(KST)에 실행됩니다.
  1. 서울 데이터 허브에서 두 통계(노후기간별·건축연도별 주택현황)를 내려받습니다.
  2. `validate.py`로 검증합니다. 기존 연도 값이 5% 넘게 바뀌거나 합계가 안 맞으면 멈춥니다.
  3. 바뀐 내용이 있으면 Pull Request를 엽니다. 내용을 확인하고 **Merge**하면 사이트가 갱신됩니다.
  4. 정비사업 현황을 점검하라는 Issue도 함께 만듭니다.
- Actions 탭 → Annual data update → **Run workflow**로 언제든 수동 실행할 수 있습니다.

### 보도자료 모음 (매일)

**Daily press releases** 워크플로가 매일 12:20, 19:20(KST)에 실행됩니다. 서울시 보도자료 RSS와 국토교통부 보도자료(주택토지·국토도시) 목록에서 제목에 재건축·재개발·주택공급 같은 말이 들어간 자료를 골라 하루 최대 3건을 `data/news.json`에 더하고, 바뀌면 사이트를 다시 배포합니다.

- 제목·기관·부서·날짜·원문 링크만 저장합니다. 본문·요약·사진·첨부파일은 옮기지 않습니다.
- 언론사 기사는 넣지 않습니다. 언론사 기사를 계속 모아 보여주면 「신문 등의 진흥에 관한 법률」의 인터넷뉴스서비스로 등록해야 할 수 있습니다.
- 잘못 고른 항목은 `data/news.json`에서 지우고 커밋하면 됩니다. 고르는 낱말은 `scripts/fetch_news.py`의 `STRONG`, `WEAK`에 있습니다.

### 정비사업 현황 고치기

`data/projects.json`에서 항목을 고치고, 항목별 `asOf`(기준월)와 맨 위 `asOf`를 새 기준월로 바꾼 뒤 커밋하면 됩니다. 위치는 `lon`/`lat`(동 단위 대략값)입니다.

### 광고 붙이기

`config.json`의 `adsense_client`(예: `ca-pub-1234...`)와 `adsense_slots`를 채우면 광고 스크립트, 광고 자리, `ads.txt`, 개인정보처리방침의 광고 문단이 자동으로 들어갑니다. 카카오 애드핏은 `kakao_adfit_units`에 광고 단위 ID를 넣습니다.

### 방문 통계 (GA4)

`config.json`의 `ga4_measurement_id`에 측정 ID(`G-…`)를 넣으면 모든 페이지에 Google 애널리틱스 태그가 들어가고, 개인정보처리방침에 쿠키·국외 이전·거부 방법 안내가 자동으로 붙습니다. 비우면 둘 다 빠집니다. Google 신호와 광고 개인화는 꺼 둡니다.

### 공유 이미지 다시 만들기

`src/assets/og.png`는 한 번 만들어 둔 이미지입니다. 수치를 새로 반영하려면 `pip install playwright && playwright install chromium` 후 `python scripts/make_og.py`를 실행합니다.

## 출처와 라이선스

- 주택 통계: 국가데이터처 주택총조사 — 서울 데이터 허브 「서울시 노후기간별 주택현황 통계」, 「서울시 건축연도별 주택현황 통계」 (공공누리 제1유형)
- 보도자료 모음: 서울특별시·국토교통부 보도자료의 제목과 원문 링크 (저작권은 각 기관)
- 자치구 경계: 통계청 센서스용 행정구역경계(2013), [southkorea/seoul-maps](https://github.com/southkorea/seoul-maps) 가공본
- three.js: MIT License (`src/assets/vendor/three.LICENSE.txt`)
- 글꼴: IBM Plex Sans KR / IBM Plex Mono (SIL Open Font License, Google Fonts)
