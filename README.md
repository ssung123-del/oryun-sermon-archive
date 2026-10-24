# 오륜 설교 아카이브

오륜교회 공식 홈페이지의 공개 설교 **메타데이터와 원본 링크**를 검색하는 비공식 비영리 아카이브입니다. HTML/CSS/JavaScript 한 파일과 `sermons.json`만 배포합니다. 웹 프레임워크, DB, 백엔드, 외부 폰트/CDN, 유료 서비스가 필요하지 않습니다.

- 통합검색, 예배 유형·구약/신약·66권·장·날짜 복합 필터, 날짜 정렬
- 정확히 같은 본문과 겹치는 본문을 구분하는 비교 창
- 검색 결과 전체 CSV (UTF-8 BOM, CRLF, Excel 수식 실행 방지)
- 클라이언트 검색용 인덱스, 30편씩 페이지 표시, 모바일 카드
- 5분마다 배포 JSON 확인, 입력한 필터와 현재 페이지 유지, 오류 시 기존 화면 유지

공개 사이트: <https://ssung123-del.github.io/oryun-sermon-archive/>

저장소: <https://github.com/ssung123-del/oryun-sermon-archive>

**운영 상태 (2026-10-25):** 사이트와 검증된 데이터 배포는 완료했습니다. GitHub 호스팅 runner에서는 공식 사이트의 robots.txt 연결이 시간 초과되어 자동 수집의 실환경 성공을 확인하지 못했습니다. Linux x64/ARM 및 macOS에서 DNS는 정상이나 TCP 연결이 성립하지 않았습니다. 정확한 원인은 확정할 수 없습니다. 매일 09:10 예약은 활성 상태이며, 연결 실패 시 기존 공개 데이터가 유지됩니다. 공식 사이트와 GitHub 사이의 연결 문제 해소가 완전 자동 운영의 남은 조건입니다.

## 파일

| 파일 | 역할 |
| --- | --- |
| `index.html` | 스타일·검색 엔진·화면을 포함한 단일 페이지 |
| `sermons.json` | 실제 수집한 데이터와 성공 시각·정책·진행 상태 |
| `scraper.py` | robots/약관 확인, HTML 파싱, 증분 수집, 검증, 원자적 저장 |
| `requirements.txt` | Python 직접 의존성 2개 |
| `.github/workflows/update.yml` | 테스트 → 수집 → 커밋 → Pages 아티팩트 → 명시적 배포 |
| `tests/` | 실제 HTML 메타데이터 fixture, Python/JS/브라우저 테스트 |
| `tests/REPORT.md` | 실행 결과와 검증 범위 |

## 로컬 실행

Python 3.12 이상이 필요합니다. Python 패키지 설치·크롤링에는 인터넷이 필요하며, 이미 수집된 사이트의 검색은 외부 서비스 없이 동작합니다.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m http.server 8000 --bind 127.0.0.1
```

브라우저에서 <http://localhost:8000>을 엽니다. HTML 파일을 직접 여는 `file://` 방식은 JSON fetch 제한 때문에 지원하지 않습니다. HTTP 서버는 로컬 미리보기용이며 운영에는 필요하지 않습니다.

## 전체 데이터 최초 수집

```sh
source .venv/bin/activate
python scraper.py --full
python scraper.py --validate-only
```

배포 파일에는 실제 전체 수집 결과가 포함되어 있습니다. 데이터가 없거나 `full_collected_at`이 없는 최초 실행은 `--full` 없이도 전체 수집합니다. `--full`은 공식 목록에 현재 공개된 모든 페이지를 순회합니다. 삭제된 게시물·비공개 자료·공식 목록에서 연결되지 않은 과거 자료까지 복원하지는 않습니다.

평상시에는 다음 명령을 사용합니다.

```sh
python scraper.py
```

예배별 최신 2페이지와 과거 목록 2페이지를 순환 점검합니다. 오래 실행하지 않아 최신 창 너머로 신규 글이 밀리면 기존 식별자를 만날 때까지 탐색을 연장합니다. 오래된 글의 수정은 해당 페이지의 순환 점검 때 반영되므로 즉시 감지되는 것은 아닙니다. 현재 가장 긴 목록 40페이지 기준 약 20회의 성공 실행 이내에 전체 목록을 재확인합니다. 더 빠른 과거 점검은 `--audit-pages 4`, 전체 재점검은 `--full`을 사용합니다.

목록 HTML에 모든 필수 정보가 있으므로 설교마다 상세 요청을 반복하지 않습니다. 매 실행 예배별 첫 설교를 상세 페이지와 대조하며, 본문이 누락된 목록 항목도 상세 페이지로 확인합니다. 검증한 결과 본문이 없는 경우 빈 원문과 `failed` 상태를 저장합니다.

## 데이터와 성경 본문 규칙

- `sermons`의 저장 단위는 **공식 분류별 게시 항목**입니다. 식별자는 `menu:tid`이며 같은 항목의 재수집은 덮어쓰고 중복 저장하지 않습니다.
- 공식 사이트가 같은 `tid`를 여러 분류에 싣는 경우 출처를 보존하기 위해 각 분류 항목을 유지합니다. `meta.total`은 분류별 항목 수, `meta.unique_total`은 고유 `tid` 수입니다.
- **화면·비교·CSV는 `tid`별로 합쳐 한 설교만 표시**하며 모든 예배 분류에 필터가 적용됩니다. 기본 원본 링크는 가장 작은 menu를 사용합니다. 같은 `tid`의 상충하는 원문 정보는 공개하지 않습니다.
- 날짜, 제목, 설교자, `reference_raw`, 예배 분류, `source_url`, menu, tid, 내용 해시, 최초 수집·내용 갱신·마지막 관측 시각을 보존합니다.
- `first_collected_at`은 최초 수집 시각, `updated_at`은 내용 변경 시각, `last_seen_at`은 해당 목록에서 실제로 확인한 시각입니다. 게시 자체의 수정 시각은 원본 사이트가 제공하지 않아 저장하지 않습니다.
- `meta.last_success_at`은 **전체 실행이 검증을 통과한 시각**입니다. 파일에는 UTC ISO 8601을 저장하고 화면에는 한국시간을 표시합니다. 신규 글이 없어도 성공 시각은 갱신됩니다.
- 구약 39권·신약 27권, 정식 명칭과 한국어 약어, 장 전체·장 범위·절 범위·장을 넘는 범위·복수 본문·불연속 절을 지원합니다. 예: `요 8:1-3, 5, 7-11; 롬 1:1-2`.
- 각 범위를 **권·장·시작 절·끝 절**의 닫힌 구간으로 분해한 뒤 정렬하고 인접/중복 구간을 합칩니다. 모든 구간의 합집합이 같으면 정확히 동일합니다. 하나라도 교집합이 있고 합집합은 다르면 겹치는 본문입니다. `요 8:1-11`과 `요 8:1-20`은 겹침으로만 표시됩니다.
- 장·절 개수만 내장하며 성경 문장은 포함하지 않습니다. 장절 개수는 [thiagobodruk/bible의 KJV 구조](https://github.com/thiagobodruk/bible/blob/master/json/en_kjv.json)에서 개수만 추출했습니다. 일반적인 한국어 성경과 같은 66권 장절 체계를 기준으로 하며 다른 절 구분의 번역은 지원하지 않습니다.
- 원문 오타, `10a` 같은 부분 절, `이하` 등 모호한 표기는 **추측하지 않고 전체 분석을 실패**시킵니다. 부분적으로 해석한 범위도 비교에 사용하지 않습니다. 실패/미기재 본문은 원문 문자열 검색이 가능하고 성경 구조 필터·비교에서는 제외됩니다.
- 본문만 입력한 검색은 범위 교집합을 찾습니다. 일반 검색은 공백으로 나눈 단어를 모두 포함하는 항목을 찾습니다. 서로 다른 구약·신약 본문을 가진 설교는 두 구분 모두에 표시될 수 있습니다.

## 공식 HTML 및 수집 정책 확인

2026-10-25 KST에 다음 공식 경로를 실제로 확인했습니다.

| 분류 | 공식 URL |
| --- | --- |
| 주일예배 | <https://oryun.org/tv/?menu=57> |
| 수요예배 | <https://oryun.org/tv/?menu=58> |
| 금요기도회 | <https://oryun.org/tv/?menu=59> |
| 주일예배(부목사) | <https://oryun.org/tv/?menu=61> |
| 외부강사 | <https://oryun.org/tv/?menu=62> |

목록 `.PhotoList a[href*="tid="]` 내부의 `.cont.tit`, `.cont.text`, `.cont.date`를 읽습니다. `.paging .post_page`와 `.paging .m_num`의 실제 페이지 수를 대조합니다. 상세 URL은 `/tv/?menu=...&mode=view&tid=...`이고 `.title_Box`의 날짜·제목·설교자, `.list_Box > .title`의 본문 표기를 대조합니다. 외부강사 상세의 예배명은 금요기도회로 나타나기도 하므로 분류는 진입한 목록의 menu를 기준으로 합니다.

[robots.txt](https://oryun.org/robots.txt)는 확인 시 `User-agent: *`였고 제한 지시는 없었습니다. [이용약관](https://oryun.org/about/?menu=312)과 상세의 영상 다운로드/재배포 금지 안내를 검토했습니다. 매 수집 실행에서 robots를 새로 확인하고 경로별 제한·Crawl-delay·Request-rate를 적용합니다. 약관 본문 해시가 검토한 내용과 달라지면 자동 수집을 중단합니다. 운영자가 새 약관을 직접 검토하고 적합한 경우 `REVIEWED_TERMS_HASH` 및 필요 시 `terms_text` 파서를 변경해야 합니다. 단순히 실행을 통과시키려고 해시를 바꾸면 안 됩니다.

영상·음원·첨부파일·성경 문장·쿠키 로그인·비공개 API는 수집하지 않습니다. 요청은 단일 작업에서 최소 1.2초 간격으로 보내며 타임아웃, 최대 4회 재시도, 429의 Retry-After를 지원합니다. 401/403·리디렉션·정책 확인 실패는 중단하며 제한을 우회하지 않습니다. 교회의 수집 중단 요청이나 정책 변경이 있으면 예약 작업을 중지하세요.

## GitHub 저장소 생성 및 업로드

GitHub Free의 **공개 저장소**와 GitHub 호스팅 표준 Linux runner를 사용하면 이 구성은 별도 서버 비용 없이 운영할 수 있습니다. GitHub의 서비스 제공 조건·사용량 한도는 적용됩니다.

GitHub CLI를 사용하는 새 설치 예:

```sh
gh auth login
git init -b main
git add index.html sermons.json scraper.py requirements.txt .github tests README.md .gitignore
git commit -m "Build Oryun sermon archive"
gh repo create oryun-sermon-archive --public --source . --remote origin
git push -u origin main
```

이미 원격 저장소가 있으면 새로 만들지 말고 해당 저장소에 push하세요. 워크플로 파일 업로드가 거부되면 GitHub 로그인 토큰의 `workflow` 권한을 확인하세요. `.venv`, 로그, 백업, 브라우저 패키지와 테스트 스크린샷은 업로드하지 않습니다.

## GitHub Pages와 Actions 설정

1. 저장소 **Settings → Pages → Build and deployment → Source → GitHub Actions**를 선택합니다. `Deploy from a branch`를 사용하지 않습니다.
2. **Settings → Actions → General → Workflow permissions → Read and write permissions**를 선택합니다. 조직 정책이 있으면 허용되는지 확인합니다.
3. 워크플로는 수집 job에 `contents: write`, 배포 job에 `pages: write`, `id-token: write`를 명시합니다. 기본 제공 `GITHUB_TOKEN`을 사용하며 별도 유료 API 키가 없습니다.
4. `github-pages` environment의 배포 가능 브랜치가 기본 브랜치를 허용하도록 합니다. 브랜치 보호로 봇 직접 push를 막은 저장소라면 이 프로젝트의 자동 커밋 정책과 맞춰 조정해야 합니다.
5. **Actions → Update sermons and deploy Pages → Run workflow**를 기본 브랜치에서 실행합니다.

같은 워크플로에서 `upload-pages-artifact`로 **index.html과 sermons.json만** 담은 사이트를 올리고, 성공한 update job에 의존하는 deploy job에서 `deploy-pages`로 실제 배포합니다. `GITHUB_TOKEN`의 커밋이 다른 워크플로를 다시 실행시킬 것이라고 가정하지 않습니다. 수집·테스트·검증·커밋 중 어느 단계가 실패해도 새 데이터는 배포하지 않습니다.

공식 설명: [Pages 사용자 정의 워크플로](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## 매일 오전 9:10 실행

```yaml
schedule:
  - cron: "10 9 * * *"
    timezone: "Asia/Seoul"
```

UTC 환산 cron을 혼용하지 않습니다. 이 구성은 GitHub Actions가 지원하는 IANA timezone 스케줄을 사용합니다. 기본 브랜치에 워크플로가 있어야 하며 GitHub 부하에 따라 정확히 09:10에 시작하지 않을 수 있습니다. 공개 저장소는 60일간 활동이 없으면 예약 작업이 비활성화될 수 있으므로 Actions 상태를 점검하세요. 참고: [예약 이벤트 공식 문서](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## 수동 갱신

- **사이트의 배포 데이터 새로고침**: 이미 공개된 `sermons.json`만 다시 읽습니다. 크롤러 실행 권한이나 서버 요청 기능이 없습니다.
- **서버 측 수집**: GitHub Actions에서 `Run workflow`. 보통 `full=false`, `deploy_only=false`입니다.
- **전체 재검사**: `full=true`. 새 설교가 없어도 최근 성공 시각은 갱신됩니다.
- **수집 없는 재배포**: `deploy_only=true`. 정상 JSON 검증 후 현재 파일을 배포합니다. 복구 또는 화면 수정 시 사용합니다.
- 기본 브랜치로 코드/데이터를 push해도 테스트·수집·배포가 실행됩니다. README만 수정하면 실행하지 않습니다.

## 현재 GitHub runner 연결 문제와 운영 방법

[실제 수집 실패 로그](https://github.com/ssung123-del/oryun-sermon-archive/actions/runs/40137328539)와 [표준 runner 3종 연결 진단](https://github.com/ssung123-del/oryun-sermon-archive/actions/runs/40137547170)을 확인했습니다. 로컬에서는 동일한 공식 HTTPS URL 수집이 정상이며, GitHub에서는 HTTP 응답 이전 연결 시간 초과가 발생합니다. IP 제한·방화벽·경로 문제 중 어떤 원인인지는 확정하지 않았습니다. 대체 주소·프록시·TLS 검증 해제로 우회하지 않습니다. 진단용 임시 워크플로 파일은 검사 후 제거했습니다.

연결이 복구될 때까지는 로컬에서 다음과 같이 갱신하고, Actions에서 `deploy_only=true`로 배포할 수 있습니다.

```sh
source .venv/bin/activate
python scraper.py
python scraper.py --validate-only
git add sermons.json
git commit -m "data: update verified sermon metadata [skip ci]"
git push
gh workflow run update.yml -f deploy_only=true -f full=false
```

GitHub의 연결이 허용되는 환경이 확보되면 기본 예약 흐름 그대로 자동 운영됩니다. 별도 대안으로 운영자가 명시적으로 선택해 관리하는 self-hosted runner를 연결할 수 있으나, 컴퓨터 상시 실행과 저장소 보안 관리가 필요하므로 이 프로젝트에서는 설치하지 않았습니다. 원본 운영자에게 연락하거나 네트워크 정책을 변경하는 작업도 수행하지 않았습니다.

## 오류 확인과 복구

1. **Actions 실행 → 실패한 step 로그**와 Summary를 확인합니다. 성공·실패의 크롤러 로그는 `crawler-logs-실행ID` artifact로 14일 보관합니다. 로컬 로그는 `logs/scraper.log`입니다.
2. 크롤러는 모든 수집과 검증이 끝나기 전에는 JSON을 쓰지 않습니다. 기록은 같은 디렉터리 임시파일 → fsync → `os.replace`로 교체합니다. 직전 파일은 로컬의 `sermons.json.bak`에 보존합니다.
3. 필드/페이지 구조 변경, 목록·상세 불일치, 필수 제목/날짜/설교자 누락, 상충하는 중복은 실패 처리합니다. 본문 정규화 실패는 명시된 실패 데이터이므로 제목 등 정상 메타데이터는 공개합니다.
4. 분류별 페이지 수가 기존보다 `max(1, 기존의 10%)`를 초과해 줄거나, 전체 재수집 관측 항목 수가 기존의 90% 미만이면 중단합니다. 중간 페이지는 16항목이어야 합니다. 기존 항목은 자동 삭제하지 않으므로 일시 누락이 곧 데이터 유실이 되지 않습니다. 작은 정상 삭제도 기존 항목이 남을 수 있어 운영자가 원본을 확인한 뒤 정리해야 합니다.
5. 네트워크 장애는 다음 실행 또는 Re-run으로 복구합니다. 구조 변경은 공식 HTML 확인 → 파서와 fixture 수정 → 테스트 → 수동 실행 순서로 처리합니다.
6. 데이터 복구는 Git 이력의 정상 `sermons.json` 또는 로컬 백업을 복원하고 `python scraper.py --validate-only`로 확인한 뒤 커밋하세요. 원본 장애 때문에 수집이 계속 실패한다면 `deploy_only=true`로 정상 파일을 배포할 수 있습니다.

```sh
cp sermons.json.bak sermons.json
python scraper.py --validate-only
git add sermons.json
git commit -m "Restore verified sermon data"
git push
# 이후 Actions에서 deploy_only=true로 수집 없이 복구 배포 가능
```

원본이 실제로 대규모 자료를 삭제한 경우 안전 검사를 무작정 우회하지 마세요. 기존 아카이브 보존·삭제 정책을 검토하고 검증된 데이터를 별도 백업한 뒤 운영자가 정리해야 합니다. 정규화 규칙을 수정할 때는 기존 JSON의 원문에서 reference 필드를 다시 생성하고 검증해야 하며 Python/브라우저 양쪽의 카탈로그와 파서를 함께 변경해야 합니다.

## 테스트

```sh
source .venv/bin/activate
python -m unittest discover -s tests -v
node --test tests/core.test.cjs
python scraper.py --validate-only
```

Node 22 이상은 테스트용이며 정적 사이트 운영에는 필요하지 않습니다. 별도 개발용 브라우저 테스트:

```sh
npm install --no-save --package-lock=false playwright
npx playwright install chromium webkit
node tests/browser.cjs
```

이 개발용 패키지는 `requirements.txt`나 배포물에 포함되지 않습니다. fixture에는 실제 공식 HTML의 메타데이터 조각만 보관하며 성경 문장·영상 스크립트는 제외했습니다.

브라우저 테스트는 데스크톱 1440px, 모바일 390px/320px에서 Chromium과 WebKit을 사용해 검색·복합 필터·본문 비교·페이지 이동·CSV 바이트·5분 갱신·잘못된 배포 데이터 거부를 확인합니다. Excel 앱에서 직접 열어 보는 검사와 실제 휴대폰 터치 동작은 별도 검증 사항입니다.
