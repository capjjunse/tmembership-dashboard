"""
generator.py — 섹션별 교체 방식 (안정화 버전)
- 트렌드: JS 직접 교체 (API 불필요)
- 뉴스: API 1회
- 고객반응: 기존 내용 유지 (API 교체 안 함 — 복잡한 중첩 구조 때문)
- 월별혜택: API 1회
- 기준일: 직접 교체
"""
import json
import re
import subprocess
import anthropic
from pathlib import Path
from datetime import datetime
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, DEPLOY_DIR

NETLIFY_URL = "https://profound-bienenstitch-f41a8a.netlify.app/"


def api_call(prompt: str, max_tokens: int = 4000) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def replace_js_array(html: str, var_name: str, new_data: list) -> str:
    pattern = rf'const {var_name}\s*=\s*\[.*?\];'
    replacement = f'const {var_name} = {json.dumps(new_data)};'
    return re.sub(pattern, replacement, html, flags=re.DOTALL)


# ── 1. 트렌드 (API 불필요) ────────────────────────────────
def update_trend(html: str, data: dict) -> str:
    t = data.get("trend", {})
    if not t.get("labels"):
        print("  ⚠️ 트렌드 없음 — 건너뜀")
        return html
    html = replace_js_array(html, "labels", t["labels"])
    html = replace_js_array(html, "skt",    t["skt"])
    html = replace_js_array(html, "kt",     t["kt"])
    html = replace_js_array(html, "lgu",    t["lgu"])
    y_max = int(max(max(t["skt"]), max(t["kt"]), max(t["lgu"])) * 1.1) + 1
    html = re.sub(r'const yMax\s*=\s*[^;]+;', f'const yMax = {y_max};', html)
    html = re.sub(
        r'출처: 네이버 DataLab API · [\d\.\s:]+수집',
        f'출처: 네이버 DataLab API · {data["collected_at"]} 수집',
        html
    )
    print("  ✅ 트렌드 완료")
    return html


# ── 2. 뉴스 (API 1회) ────────────────────────────────────
def update_news(html: str, data: dict) -> str:
    news = data.get("news", {})
    if not any(news.values()):
        print("  ⚠️ 뉴스 없음 — 건너뜀")
        return html

    prompt = f"""아래 뉴스 데이터로 대시보드 뉴스 섹션 HTML을 생성해줘.

데이터:
{json.dumps(news, ensure_ascii=False, indent=2)}

출력 형식 (```없이 HTML만):
<div id="np-skt">
  <div class="nc"><div class="nct"><span class="nb nb신규">신규</span><span class="ntitle">제목</span></div><div class="nsum">요약</div><div class="nmeta">날짜 · <a href="URL" target="_blank">출처명</a></div></div>
</div>
<div id="np-kt" class="hidden">...</div>
<div id="np-lgu" class="hidden">...</div>

규칙:
- 각 통신사 최대 3건
- 배지: nb신규/nb변경/nb종료/nb이슈 중 적절히
- div 태그 정확히 열고 닫을 것"""

    try:
        response = api_call(prompt, max_tokens=3000)
        # 마크다운 코드블록 제거
        if "```" in response:
            response = re.sub(r'```[^\n]*\n?', '', response).strip()

        for sid in ["np-skt", "np-kt", "np-lgu"]:
            # 해당 섹션 시작 ~ 다음 섹션 시작 사이의 내용으로 교체
            pattern = rf'(<div\s+id="{sid}"[^>]*>)(.*?)(?=<div\s+id="np-|</div>\s*</div>\s*<!--\s*고객)'
            m = re.search(rf'<div\s+id="{sid}"[^>]*>.*?(?=<div\s+id="np-(?!{sid})|$)', response, re.DOTALL)
            if m:
                old_pattern = rf'(<div\s+id="{sid}"[^>]*>).*?(?=<div\s+id="np-(?!{sid})|<!--)'
                html = re.sub(old_pattern, m.group(0), html, count=1, flags=re.DOTALL)
        print("  ✅ 뉴스 완료")
    except Exception as e:
        print(f"  ⚠️ 뉴스 실패: {e} — 기존 유지")
    return html


# ── 3. 고객반응 (기존 유지) ───────────────────────────────
def update_sentiment(html: str, data: dict) -> str:
    # 고객반응 섹션은 중첩 구조가 복잡해서 API 교체 시 레이아웃 깨짐
    # 기존 내용 그대로 유지 (검증된 댓글 데이터 보존)
    print("  ✅ 고객반응 — 기존 내용 유지 (안정성)")
    return html


# ── 4. 월별혜택 (API 1회) ─────────────────────────────────
def update_monthly(html: str, data: dict) -> str:
    monthly = data.get("monthly", {})
    if not any(v.get("content") for v in monthly.values()):
        print("  ⚠️ 월별혜택 없음 — 건너뜀")
        return html

    prompt = f"""아래 월별혜택 데이터로 대시보드 월별혜택 섹션 HTML을 생성해줘.

데이터:
{json.dumps(monthly, ensure_ascii=False, indent=2)}

출력 형식 (```없이 HTML만, 정확히 이 구조로):
<div class="m3">
  <div class="mc">
    <div class="mch ms"><span>SKT — T day + 0 week</span><a href="https://sktmembership.tworld.co.kr/mps/pc-bff/sktmembership/tday.do" target="_blank" class="mlink" style="color:var(--skt-t)">T day →</a></div>
    <div class="mcb">
      <div class="mblk"><div class="mbtit"><span class="mbdot" style="background:var(--skt)"></span>프로그램명</div><ul class="mblist"><li>혜택1</li><li>혜택2</li></ul></div>
    </div>
  </div>
  <div class="mc">
    <div class="mch mk"><span>KT — 달달혜택</span><a href="https://event.kt.com/html/event/ongoing_event_view.html?pcEvtNo=13783" target="_blank" class="mlink" style="color:var(--kt-t)">달달혜택 →</a></div>
    <div class="mcb">...</div>
  </div>
  <div class="mc">
    <div class="mch ml"><span>LGU+ — 유플투쁠</span><a href="https://www.lguplus.com/benefit/uplustobeul" target="_blank" class="mlink" style="color:var(--lgu-t)">유플투쁠 →</a></div>
    <div class="mcb">...</div>
  </div>
</div>

규칙:
- 모든 div 태그 정확히 열고 닫을 것
- 할인 표기: ↓ 대신 '할인' 명시"""

    try:
        response = api_call(prompt, max_tokens=3000)
        if "```" in response:
            response = re.sub(r'```[^\n]*\n?', '', response).strip()

        # m3 div 전체를 찾아서 교체
        m = re.search(r'<div\s+class="m3">[\s\S]+?</div>\s*</div>\s*</div>', response)
        if m:
            html = re.sub(
                r'<div\s+class="m3">[\s\S]+?</div>\s*</div>\s*</div>',
                m.group(0), html, count=1
            )
            print("  ✅ 월별혜택 완료")
        else:
            print("  ⚠️ 월별혜택 파싱 실패 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ 월별혜택 실패: {e} — 기존 유지")
    return html


# ── 5. 기준일 업데이트 ────────────────────────────────────
def update_date(html: str, collected_at: str) -> str:
    date_str = collected_at.split(" ")[0]
    html = re.sub(r'\d{4}\.\d{2}\.\d{2} 기준', f'{date_str} 기준', html)
    print(f"  ✅ 기준일: {date_str}")
    return html


# ── 메인 ─────────────────────────────────────────────────
def generate_dashboard(collected: dict) -> str:
    html_path = DEPLOY_DIR / "index.html"
    if not html_path.exists():
        raise FileNotFoundError(f"기준 HTML 없음: {html_path}")

    html = html_path.read_text(encoding="utf-8")
    print(f"  기준 HTML: {len(html):,}자")

    print("  [1/4] 트렌드...")
    html = update_trend(html, collected)

    print("  [2/4] 뉴스...")
    html = update_news(html, collected)

    print("  [3/4] 고객반응...")
    html = update_sentiment(html, collected)

    print("  [4/4] 월별혜택...")
    html = update_monthly(html, collected)

    html = update_date(html, collected["collected_at"])
    print(f"  최종 HTML: {len(html):,}자")
    return html


def save_and_deploy(html: str) -> str:
    DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
    html_path = DEPLOY_DIR / "index.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  HTML 저장: {len(html):,}자")

    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    for cmd in [
        ["git", "-C", str(DEPLOY_DIR), "add", "index.html"],
        ["git", "-C", str(DEPLOY_DIR), "commit", "-m", f"Auto update {today}"],
        ["git", "-C", str(DEPLOY_DIR), "push"],
    ]:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 and "nothing to commit" not in r.stdout + r.stderr:
            raise RuntimeError(f"git 실패: {r.stderr}")

    print(f"  배포 완료 → {NETLIFY_URL}")
    return NETLIFY_URL
