"""
generator.py — 주간/월간 업데이트 분기
- 매주: 트렌드, 뉴스, 고객반응, 월별혜택
- 매월 첫째 주: 위 + 상시혜택, VIP특화, 변경이력, 비통신멤버십, AI인사이트, 개요
"""
import json
import re
import subprocess
import anthropic
from pathlib import Path
from datetime import datetime
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, DEPLOY_DIR

NETLIFY_URL = "https://profound-bienenstitch-f41a8a.netlify.app/"


def is_first_week_of_month() -> bool:
    """오늘이 이번 달 첫째 주(1~7일)인지 확인"""
    return datetime.today().day <= 7


def api_call(prompt: str, max_tokens: int = 4000) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def clean_html(response: str) -> str:
    if "```" in response:
        response = re.sub(r'```[^\n]*\n?', '', response).strip()
    return response


def replace_js_array(html: str, var_name: str, new_data: list) -> str:
    pattern = rf'const {var_name}\s*=\s*\[.*?\];'
    replacement = f'const {var_name} = {json.dumps(new_data)};'
    return re.sub(pattern, replacement, html, flags=re.DOTALL)


# ════════════════════════════════════════════
# 주간 업데이트 (매주)
# ════════════════════════════════════════════

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
    print("  ✅ 트렌드")
    return html


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

규칙: 각 통신사 최대 3건. 배지: nb신규/nb변경/nb종료/nb이슈. div 정확히 열고 닫기."""
    try:
        response = clean_html(api_call(prompt, max_tokens=3000))
        for sid in ["np-skt", "np-kt", "np-lgu"]:
            m = re.search(rf'<div\s+id="{sid}"[^>]*>.*?(?=<div\s+id="np-(?!{sid})|$)', response, re.DOTALL)
            if m:
                html = re.sub(rf'(<div\s+id="{sid}"[^>]*>).*?(?=<div\s+id="np-(?!{sid})|<!--)',
                              m.group(0), html, count=1, flags=re.DOTALL)
        print("  ✅ 뉴스")
    except Exception as e:
        print(f"  ⚠️ 뉴스 실패: {e} — 기존 유지")
    return html


def update_sentiment(html: str, data: dict) -> str:
    print("  ✅ 고객반응 — 기존 유지 (안정성)")
    return html


def update_monthly(html: str, data: dict) -> str:
    monthly = data.get("monthly", {})
    if not any(v.get("content") for v in monthly.values()):
        print("  ⚠️ 월별혜택 없음 — 건너뜀")
        return html
    prompt = f"""아래 월별혜택 데이터로 대시보드 월별혜택 섹션 HTML을 생성해줘.

데이터:
{json.dumps(monthly, ensure_ascii=False, indent=2)}

출력 형식 (```없이 HTML만):
<div class="m3">
  <div class="mc">
    <div class="mch ms"><span>SKT — T day + 0 week</span><a href="https://sktmembership.tworld.co.kr/mps/pc-bff/sktmembership/tday.do" target="_blank" class="mlink" style="color:var(--skt-t)">T day →</a></div>
    <div class="mcb"><div class="mblk"><div class="mbtit"><span class="mbdot" style="background:var(--skt)"></span>프로그램명</div><ul class="mblist"><li>혜택</li></ul></div></div>
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

규칙: div 정확히 열고 닫기. 할인 표기는 '할인' 명시 (↓ 사용 금지)."""
    try:
        response = clean_html(api_call(prompt, max_tokens=3000))
        m = re.search(r'<div\s+class="m3">[\s\S]+?</div>\s*</div>\s*</div>', response)
        if m:
            html = re.sub(r'<div\s+class="m3">[\s\S]+?</div>\s*</div>\s*</div>',
                          m.group(0), html, count=1)
            print("  ✅ 월별혜택")
        else:
            print("  ⚠️ 월별혜택 파싱 실패 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ 월별혜택 실패: {e} — 기존 유지")
    return html


# ════════════════════════════════════════════
# 월간 업데이트 (첫째 주만)
# ════════════════════════════════════════════

def update_overview(html: str, data: dict) -> str:
    """개요 — 이번 달 핵심 동향"""
    namu = data.get("namu", {})
    news = data.get("news", {})
    monthly = data.get("monthly", {})
    prompt = f"""아래 수집 데이터로 대시보드 '이번 달 핵심 동향' 섹션 HTML을 생성해줘.
기준일: {data['collected_at']}

나무위키 상시혜택:
SKT: {namu.get('skt', {}).get('text', '')[:1000]}
KT: {namu.get('kt', {}).get('text', '')[:1000]}
LGU+: {namu.get('lgu', {}).get('text', '')[:1000]}

뉴스: {json.dumps(news, ensure_ascii=False)}
월별혜택: {json.dumps(monthly, ensure_ascii=False)}

출력 형식 (```없이 HTML만):
<div class="og">
  <div class="oc cs"><div class="ol"><span class="cb bs">SKT</span></div><div class="ov">핵심변경 1줄</div><div class="od">설명<br>날짜</div></div>
  <div class="oc ck"><div class="ol"><span class="cb bk">KT</span></div><div class="ov">핵심변경 1줄</div><div class="od">설명</div></div>
  <div class="oc cl"><div class="ol"><span class="cb bl">LGU+</span></div><div class="ov">핵심변경 1줄</div><div class="od">설명</div></div>
  <div class="oc cg"><div class="ol" style="font-size:11px;color:var(--tx3)">주요 변경</div><div class="ov" style="font-size:13px">변경사항</div><div class="od">설명</div></div>
</div>
<div class="tl">
  <div class="ti"><div class="tdot" style="background:var(--skt)"></div><div class="tt"><span class="cb bs">SKT</span> 상세내용</div></div>
  <div class="ti"><div class="tdot" style="background:var(--kt)"></div><div class="tt"><span class="cb bk">KT</span> 상세내용</div></div>
  <div class="ti"><div class="tdot" style="background:var(--lgu)"></div><div class="tt"><span class="cb bl">LGU+</span> 상세내용</div></div>
</div>

규칙: 이달 실제 변경/신설 혜택 기반. 이상/할인 표기 (↑/↓ 금지)."""
    try:
        response = clean_html(api_call(prompt, max_tokens=2000))
        og = re.search(r'<div\s+class="og">[\s\S]+?</div>\s*<div\s+class="tl">', response)
        tl = re.search(r'<div\s+class="tl">[\s\S]+?</div>', response)
        if og and tl:
            html = re.sub(r'<div\s+class="og">[\s\S]+?</div>\s*<div\s+class="tl">',
                          og.group(0), html, count=1)
            html = re.sub(r'<div\s+class="tl">[\s\S]+?</div>',
                          tl.group(0), html, count=1)
            print("  ✅ 개요(핵심동향)")
        else:
            print("  ⚠️ 개요 파싱 실패 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ 개요 실패: {e} — 기존 유지")
    return html


def update_regular_benefits(html: str, data: dict) -> str:
    """상시혜택 — 나무위키 기반"""
    namu = data.get("namu", {})
    if not any(v.get("text") for v in namu.values()):
        print("  ⚠️ 나무위키 데이터 없음 — 기존 유지")
        return html
    prompt = f"""아래 나무위키 데이터로 통신 3사 상시 혜택 비교 테이블 HTML을 생성해줘.
기준일: {data['collected_at']}

SKT 나무위키: {namu.get('skt', {}).get('text', '')[:3000]}
KT 나무위키: {namu.get('kt', {}).get('text', '')[:3000]}
LGU+ 나무위키: {namu.get('lgu', {}).get('text', '')[:3000]}

출력 형식 (```없이 HTML만): 카테고리별 <div class="cl2">카테고리</div> + <table class="ct"> 구조.
카테고리: 영화관, 베이커리, 패밀리레스토랑, 피자, 카페·디저트, 편의점
각 테이블: thead(제휴처/SKT/KT/LGU+) + tbody(제휴처별 행)

중요 규칙:
- LGU+ CGV: 최대 4,000원 할인
- SKT 롯데시네마: 2026.02.01 제휴 종료 (class="wt" 적용)
- KT 롯데시네마: VVIP 초이스 표기 없이 전 등급 최대 5,000원 할인만
- 이상/할인 표기 (↑이상 ↓할인 사용 금지, '이상'/'할인' 텍스트로)
- 상시 없는 경우: <td class="na">기본 상시 없음</td>"""
    try:
        response = clean_html(api_call(prompt, max_tokens=4000))
        # 첫 번째 cl2부터 상시혜택 섹션 끝까지 교체
        m = re.search(r'<div\s+class="cl2">[\s\S]+?(?=</div>\s*<!--\s*월별)', response)
        if m:
            html = re.sub(r'<div\s+class="cl2">[\s\S]+?(?=</div>\s*<!--\s*월별)',
                          m.group(0), html, count=1)
            print("  ✅ 상시혜택")
        else:
            print("  ⚠️ 상시혜택 파싱 실패 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ 상시혜택 실패: {e} — 기존 유지")
    return html


def update_vip(html: str, data: dict) -> str:
    """VIP 특화 혜택"""
    namu = data.get("namu", {})
    prompt = f"""아래 데이터로 VIP 특화 혜택 테이블 HTML을 생성해줘.
기준일: {data['collected_at']}

SKT: {namu.get('skt', {}).get('text', '')[:1500]}
KT: {namu.get('kt', {}).get('text', '')[:1500]}
LGU+: {namu.get('lgu', {}).get('text', '')[:1500]}

출력 형식 (```없이 HTML만):
<table class="vt">
  <thead><tr><th>구분</th><th class="th-skt"><span class="cb bs">SKT</span> VIP Pick</th><th class="th-kt"><span class="cb bk">KT</span> VIP·VVIP 초이스</th><th class="th-lgu"><span class="cb bl">LGU+</span> VIP콕</th></tr></thead>
  <tbody>
    <tr><td>제공 주기</td><td>내용<br><a href="URL" target="_blank" class="vlink">링크 →</a></td><td>...</td><td>...</td></tr>
    <tr><td>영화</td><td>...</td><td>...</td><td>...</td></tr>
    <tr><td>OTT·구독</td><td>...</td><td>...</td><td>...</td></tr>
    <tr><td>생일</td><td>...</td><td>...</td><td>...</td></tr>
  </tbody>
</table>

규칙: KT 영화 항목에 VIP/VVIP 횟수 표기 없이 '롯데시네마 2인 무료'만. 이상/할인 텍스트 사용."""
    try:
        response = clean_html(api_call(prompt, max_tokens=2000))
        m = re.search(r'<table\s+class="vt">[\s\S]+?</table>', response)
        if m:
            html = re.sub(r'<table\s+class="vt">[\s\S]+?</table>', m.group(0), html, count=1)
            print("  ✅ VIP 특화")
        else:
            print("  ⚠️ VIP 파싱 실패 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ VIP 실패: {e} — 기존 유지")
    return html


def update_history(html: str, data: dict) -> str:
    """변경 이력 — 뉴스 기반으로 신규 이력 추가"""
    news = data.get("news", {})
    prompt = f"""아래 뉴스 데이터에서 멤버십 혜택 변경/신설/종료 이력을 찾아 변경이력 테이블 행을 생성해줘.
기준일: {data['collected_at']}

뉴스: {json.dumps(news, ensure_ascii=False)}

출력 형식 (```없이 HTML만, 최근 5건):
<tbody id="hist-tbody">
  <tr><td>날짜</td><td><span class="cb bs">SKT</span></td><td>프로그램</td><td>변경내용</td><td><span class="tb t변경">변경</span></td><td><a href="URL" target="_blank">출처</a></td></tr>
  ...
</tbody>

배지 클래스: t신규/t변경/t종료/t재개
날짜 형식: YYYY.MM.DD"""
    try:
        response = clean_html(api_call(prompt, max_tokens=2000))
        m = re.search(r'<tbody\s+id="hist-tbody">[\s\S]+?</tbody>', response)
        if m:
            html = re.sub(r'<tbody\s+id="hist-tbody">[\s\S]+?</tbody>', m.group(0), html, count=1)
            print("  ✅ 변경이력")
        else:
            print("  ⚠️ 변경이력 파싱 실패 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ 변경이력 실패: {e} — 기존 유지")
    return html


def update_non_telecom(html: str, data: dict) -> str:
    """비통신 멤버십 동향"""
    prompt = f"""기준일 {data['collected_at']} 기준 비통신 멤버십 최신 동향으로 HTML을 생성해줘.

출력 형식 (```없이 HTML만):
<div class="ntg">
  <div class="ntc"><div class="nth" style="background:linear-gradient(135deg,#03c75a,#02a84c);color:#fff">네이버플러스 멤버십</div><div class="ntb"><span class="nttag" style="background:#e6f9ee;color:#1a7f3c">구독형 · 월 N원</span><br><b>핵심:</b> 내용<br><br><b>주목:</b> 내용</div></div>
  ... (쿠팡 와우, 현대카드, 당근, 카카오페이/토스, 올리브영·무신사)
</div>

6개 카드 모두 포함. 최신 가격/서비스 반영."""
    try:
        response = clean_html(api_call(prompt, max_tokens=3000))
        m = re.search(r'<div\s+class="ntg">[\s\S]+?</div>\s*</div>', response)
        if m:
            html = re.sub(r'<div\s+class="ntg">[\s\S]+?</div>\s*</div>', m.group(0), html, count=1)
            print("  ✅ 비통신 멤버십")
        else:
            print("  ⚠️ 비통신 파싱 실패 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ 비통신 실패: {e} — 기존 유지")
    return html


def update_ai_insight(html: str, data: dict) -> str:
    """AI 인사이트 — SWOT + 전략 시사점"""
    namu = data.get("namu", {})
    news = data.get("news", {})
    prompt = f"""아래 데이터로 통신 3사 멤버십 AI 인사이트 섹션 HTML을 생성해줘.
기준일: {data['collected_at']}

나무위키: SKT {namu.get('skt',{}).get('text','')[:800]} / KT {namu.get('kt',{}).get('text','')[:800]} / LGU+ {namu.get('lgu',{}).get('text','')[:800]}
뉴스: {json.dumps(news, ensure_ascii=False)}

출력 형식 (```없이 HTML만):
<div class="swot-grid">
  <div class="swot-card"><div class="swot-hdr sh-skt"><div class="swot-ico">📱</div><span>SKT T멤버십</span></div>
    <div class="swot-body">
      <div class="swot-section str"><div class="swot-label str">강점</div><div class="swot-items"><div class="swot-item">내용</div></div></div>
      <div class="swot-section wk"><div class="swot-label wk">약점</div><div class="swot-items"><div class="swot-item">내용</div></div></div>
    </div>
  </div>
  ... (KT sh-kt 📶, LGU+ sh-lgu 🌸)
</div>
<div style="font-size:12px;font-weight:800;color:var(--tx);margin-bottom:12px;display:flex;align-items:center;gap:7px"><span style="width:3px;height:15px;background:linear-gradient(180deg,var(--p),var(--pm));border-radius:2px;display:inline-block"></span>핵심 인사이트 및 전략 시사점</div>
<div class="ins-list">
  <div class="ins-item"><div class="ins-num">1</div><div class="ins-txt"><b>제목:</b> 내용</div></div>
  ... (5개)
</div>"""
    try:
        response = clean_html(api_call(prompt, max_tokens=3000))
        # swot-grid 교체
        m_swot = re.search(r'<div\s+class="swot-grid">[\s\S]+?</div>\s*</div>\s*</div>', response)
        if m_swot:
            html = re.sub(r'<div\s+class="swot-grid">[\s\S]+?</div>\s*</div>\s*</div>',
                          m_swot.group(0), html, count=1)
        # ins-list 교체
        m_ins = re.search(r'<div\s+class="ins-list">[\s\S]+?</div>\s*</div>', response)
        if m_ins:
            html = re.sub(r'<div\s+class="ins-list">[\s\S]+?</div>\s*</div>',
                          m_ins.group(0), html, count=1)
        if m_swot or m_ins:
            print("  ✅ AI 인사이트")
        else:
            print("  ⚠️ AI 인사이트 파싱 실패 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ AI 인사이트 실패: {e} — 기존 유지")
    return html


def update_date(html: str, collected_at: str) -> str:
    date_str = collected_at.split(" ")[0]
    html = re.sub(r'\d{4}\.\d{2}\.\d{2} 기준', f'{date_str} 기준', html)
    print(f"  ✅ 기준일: {date_str}")
    return html


# ════════════════════════════════════════════
# 메인 진입점
# ════════════════════════════════════════════

def generate_dashboard(collected: dict) -> str:
    html_path = DEPLOY_DIR / "index.html"
    if not html_path.exists():
        raise FileNotFoundError(f"기준 HTML 없음: {html_path}")

    html = html_path.read_text(encoding="utf-8")
    is_monthly = is_first_week_of_month()
    mode = "🗓️ 월간 전체 업데이트" if is_monthly else "📅 주간 업데이트"
    print(f"  기준 HTML: {len(html):,}자 | 모드: {mode}")

    # ── 주간 업데이트 (매주) ──────────────────
    print("\n  [주간]")
    html = update_trend(html, collected)
    html = update_news(html, collected)
    html = update_sentiment(html, collected)
    html = update_monthly(html, collected)

    # ── 월간 업데이트 (첫째 주만) ─────────────
    if is_monthly:
        print("\n  [월간 추가]")
        html = update_overview(html, collected)
        html = update_regular_benefits(html, collected)
        html = update_vip(html, collected)
        html = update_history(html, collected)
        html = update_non_telecom(html, collected)
        html = update_ai_insight(html, collected)

    html = update_date(html, collected["collected_at"])
    print(f"\n  최종 HTML: {len(html):,}자")
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
