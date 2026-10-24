# 오륜 설교 아카이브

[사이트 열기](https://ssung123-del.github.io/oryun-sermon-archive/) · [저장소](https://github.com/ssung123-del/oryun-sermon-archive)

오륜교회 공식 홈페이지의 공개 설교 메타데이터와 원본 링크를 검색하는 비공식 비영리 사이트입니다. HTML/CSS/JavaScript 한 파일과 `sermons.json`으로 동작합니다. 별도 DB·백엔드·유료 서비스가 없습니다.

## 사용 방법

1. 사이트를 열면 기본 아카이브 또는 이 브라우저에 저장된 최신 목록으로 바로 검색할 수 있습니다.
2. **설교 목록 불러오기**를 누르면 브라우저가 오륜교회 공식 목록과 상세 페이지를 직접 확인합니다.
3. 검증이 끝나면 새 목록으로 검색·필터·본문 비교·CSV가 즉시 갱신됩니다. **재배포는 필요하지 않습니다.**
4. 불러온 목록은 현재 브라우저의 localStorage에 저장되어 다시 열 때도 사용됩니다. 다른 기기/브라우저와 자동 공유되지는 않습니다.
5. **과거 전체도 확인**을 선택하면 현재 공개된 모든 목록 페이지를 다시 수집합니다. 기본 불러오기는 최신 2페이지와 과거 2페이지를 분류별로 점검하며, 오래 방문하지 않아 새 설교가 많으면 기존 항목을 만날 때까지 최신 탐색을 연장합니다.
6. 불러오는 동안 진행 상태를 확인하거나 **취소**할 수 있습니다. 중간 실패·취소 시 기존 데이터와 저장본은 유지됩니다.

브라우저가 닫혀 있거나 버튼을 누르지 않으면 수집하지 않습니다. 예약 실행·5분 자동 확인·GitHub 자동 수집·데이터 자동 커밋은 없습니다. `.github/workflows/update.yml`은 삭제했고 예약 작업도 중지했습니다.

**목록 다시 열기**는 저장된 목록/기본 파일을 여는 기능입니다. 새 설교 수집은 상단의 **설교 목록 불러오기**를 사용하세요. 저장 공간이 부족하거나 비공개 모드에서 저장이 제한되면 화면에는 반영되지만 다음 방문까지 유지되지 않을 수 있습니다.

## 기능과 데이터

- 설교자·제목·성경 본문 검색, 예배 유형·구약/신약·66권·장·날짜 복합 필터
- 기본 날짜 최신순, 오래된순, 30편씩 페이지 표시, 모바일 카드
- 동일한 본문 범위와 일부가 겹치는 본문 범위를 구분하는 비교
- 검색 결과 전체 CSV: UTF-8 BOM, CRLF, 따옴표 처리, Excel 수식 실행 방지
- 원본 링크, 최근 확인 시각, 로딩·진행·빈 결과·오류 표시

기본 파일에는 2013-12-15~2026-10-23의 고유 설교 **1,370편**이 있습니다. 공식 사이트의 여러 분류에 함께 게시된 항목을 포함하면 출처 항목은 1,458개입니다.

`sermons.json`은 `schema_version`, `meta`, `sermons`로 구성됩니다. 날짜·설교자·제목·본문 원문·분류·원본 URL·menu/tid·내용 해시·최초 수집/내용 갱신/마지막 관측 시각을 보존합니다. `meta.total`은 출처 항목 수, `meta.unique_total`은 고유 tid 수입니다. 화면과 CSV는 같은 tid를 한 편으로 합치고 모든 분류에 필터를 적용합니다.

성경 원문 문자열 `reference_raw`는 항상 보존합니다. 구약 39권·신약 27권, 한국어 정식 명칭과 약어, 장 전체·장/절 범위·복수 본문·불연속 절을 지원합니다. 예: `요 8:1-3, 5, 7-11; 롬 1:1-2`. 구간 합집합이 같으면 동일 범위이고, 합집합이 다르면서 교집합이 있으면 겹치는 본문입니다.

원본 오타·부분 절(`10a`)·모호한 표기 등은 추측하지 않고 `failed`로 표시합니다. 본문이 없는 경우에도 이를 명시하고 원본 링크를 제공합니다. 해석 실패 항목은 원문 문자열 검색이 가능하지만 성경 구조 필터와 비교에서는 제외됩니다. 장절 개수만 내장하며 성경 문장은 포함하지 않습니다. 개수 출처는 [KJV 구조 데이터](https://github.com/thiagobodruk/bible/blob/master/json/en_kjv.json)입니다.

## 수집 범위와 정책

공식 목록: [주일예배](https://oryun.org/tv/?menu=57), [수요예배](https://oryun.org/tv/?menu=58), [금요기도회](https://oryun.org/tv/?menu=59), [주일예배(부목사)](https://oryun.org/tv/?menu=61), [외부강사](https://oryun.org/tv/?menu=62).

공식 사이트가 현재 `Access-Control-Allow-Origin: *`를 제공하므로 브라우저가 직접 목록 HTML을 읽을 수 있습니다. 쿠키나 로그인 정보는 보내지 않습니다. 이 정책이 변경되거나 사용자의 네트워크에서 연결되지 않으면 기존 목록을 유지하고 오류를 표시합니다. 프록시·대체 주소·접근 제한 우회는 사용하지 않습니다.

수집 전 [robots.txt](https://oryun.org/robots.txt)와 [이용약관](https://oryun.org/about/?menu=312)을 확인합니다. robots의 Allow/Disallow, Crawl-delay, Request-rate를 반영하고 해석하지 못하는 새 지시나 약관 변경이 있으면 중단합니다. 검토한 약관 해시는 `index.html`과 `scraper.py`에 있습니다. 정책이 달라지면 원문을 검토하고 파서를 함께 수정해야 합니다.

요청은 한 번에 하나씩 최소 1.2초 간격으로 보내며, 타임아웃·최대 4회 재시도·429 Retry-After를 지원합니다. 401/403·리디렉션은 중단합니다. 목록 필드·페이지 번호·중간 페이지의 16항목·분류별 첫 상세 페이지를 검증합니다. 페이지 수 급감, 전체 재수집 건수 10% 초과 감소, 중복 충돌, 목록·상세 불일치는 갱신 실패로 처리합니다. 기존 항목은 자동 삭제하지 않습니다.

영상·음원·첨부파일·성경 문장을 저장하거나 재배포하지 않습니다. 원본의 비공개/삭제 자료나 공개 목록에서 연결되지 않는 자료는 수집하지 않습니다. 교회의 정책 변경이나 수집 중단 요청이 있으면 사용을 중지하세요.

## 파일과 로컬 실행

| 파일 | 역할 |
| --- | --- |
| `index.html` | 검색 화면, 브라우저 크롤러, 정책 확인, 브라우저 저장 |
| `sermons.json` | 사이트를 처음 열 때 사용하는 검증된 기본 아카이브 |
| `scraper.py` | 관리자가 필요할 때 실행할 수 있는 Python 수집기 |
| `requirements.txt` | Python 수집기의 직접 의존성 2개 |
| `tests/` | 파서·검색·브라우저·수동 크롤링 테스트와 검증 기록 |

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

<http://localhost:8000>으로 엽니다. 브라우저 버튼 사용에는 Python 패키지가 필요하지 않습니다. `file://`로 직접 열면 JSON과 브라우저 저장/암호화 API가 제한될 수 있어 지원하지 않습니다.

Python으로 기본 아카이브를 관리할 경우에만:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scraper.py         # 증분 수집
python scraper.py --full  # 현재 공개된 전체 목록 수집
python scraper.py --validate-only
```

Python 수집기는 모든 검증을 통과한 후에만 임시파일과 `os.replace`로 교체하며 직전 파일을 `sermons.json.bak`에 보존합니다. 실패 로그는 `logs/scraper.log`입니다. 브라우저 갱신본은 Python 기본 파일을 변경하지 않습니다.

## GitHub Pages 운영

GitHub에는 예약 크롤러나 사용자 정의 Actions 워크플로가 없습니다. **Pages → Source: Deploy from a branch → codex/pages / (root)**로 정적 파일만 제공합니다. codex/pages 브랜치에는 `index.html`, `sermons.json`, `.nojekyll`만 게시합니다. GitHub의 기본 Pages 게시 작업은 정적 호스팅을 위한 것이며 공식 사이트 수집이나 데이터 갱신을 실행하지 않습니다.

일반 사용자는 버튼만 누르면 최신 목록을 사용할 수 있으므로 재배포가 필요 없습니다. 화면 코드 변경 또는 모든 신규 방문자를 위한 기본 파일 교체 때만 관리자가 수동으로 정적 파일을 게시합니다. GitHub 토큰이나 저장소 쓰기 권한은 브라우저 코드에 포함하지 않습니다.

새 저장소를 만들 경우 GitHub Free의 공개 저장소를 사용하고, 소스는 main에 업로드한 뒤 공개 파일 세 개만 codex/pages에 게시하세요. Pages에서 codex/pages 루트를 선택하면 됩니다. 사용자 정의 Actions 권한이나 자동 커밋 권한은 필요하지 않습니다.

## 장애와 복구

- 버튼 수집 실패/취소: 기존 화면과 localStorage 저장본 유지. 연결이 정상화된 뒤 재시도합니다.
- 공식 HTML/약관 변경: 관리자가 공식 원문 확인 → 파서/fixture 수정 → 테스트 → 화면 코드 게시 순서로 처리합니다.
- 브라우저 저장 데이터 손상: 검증을 통과한 기본 JSON으로 열 수 있습니다. 브라우저 사이트 데이터 삭제 시 이 기기에 저장한 목록도 사라집니다.
- 기본 파일 복구: Git 이력 또는 `sermons.json.bak`에서 복원하고 `python scraper.py --validate-only`로 검증한 뒤 수동 게시합니다.
- GitHub runner에서 공식 사이트 연결이 시간 초과됐던 이전 방식은 제거했습니다. 현재 수집은 방문자의 브라우저와 네트워크에서 실행됩니다.

## 테스트

```sh
source .venv/bin/activate
python -m unittest discover -s tests -v
node --test tests/core.test.cjs
python scraper.py --validate-only
```

브라우저 테스트용 개발 의존성은 별도로 설치할 수 있으며 배포물에는 포함되지 않습니다.

```sh
npm install --no-save --package-lock=false playwright
npx playwright install chromium webkit
node tests/browser.cjs
node tests/manual-browser.cjs
```

브라우저 테스트는 검색·필터·비교·CSV·수동 갱신·자동 요청 없음·브라우저 저장과 재방문·실패 시 보존·취소·정책 변경·파서의 Python 결과 일치를 확인합니다. 상세 결과와 실제 환경 검증 범위는 [검증 기록](tests/REPORT.md)에 있습니다.
