"""
generator.py — 섹션 교체를 문자열 마커 방식으로 처리
BeautifulSoup str(soup) 문제 완전 우회
"""
import json
import re
import subprocess
import anthropic
from datetime import datetime, date
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, DEPLOY_DIR

PAGES_URL = "https://capjjunse.github.io/tmembership-dashboard/"


def is_first_week_of_month() -> bool:
    return datetime.today().day <= 7


def is_odd_week() -> bool:
    return date.today().isocalendar()[1] % 2 == 1


def api_call(prompt: str, max_tokens: int = 4000) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def clean(s: str) -> str:
    return re.sub(r'```[^\n]*\n?', '', s).strip()


def replace_js_array(html: str, var_name: str, data: list) -> str:
    return re.sub(
        rf'const {var_name}\s*=\s*\[.*?\];',
        f'const {var_name} = {json.dumps(data)};',
        html, flags=re.DOTALL
    )


def swap_by_id(html: str, elem_id: str, new_outer_html: str) -> str:
    """
    id="elem_id" 속성을 가진 div를 new_outer_html로 교체.
    BeautifulSoup 없이 순수 문자열 조작.
    """
    # 시작 태그 찾기
    start_pat = re.compile(rf'<div[^>]+id=["\']?{re.escape(elem_id)}["\']?[^>]*>', re.IGNORECASE)
    m = start_pat.search(html)
    if not m:
        print(f"    ⚠️ #{elem_id} 시작 태그 없음")
        return html

    start = m.start()
    tag_end = m.end()

    # 중첩 div 카운트로 닫는 태그 찾기
    depth = 1
    pos = tag_end
    while pos < len(html) and depth > 0:
        next_open  = html.find('<div', pos)
        next_close = html.find('</div>', pos)
        if next_close == -1:
            break
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + 4
        else:
            depth -= 1
            pos = next_close + 6

    end = pos  # </div> 닫힌 직후

    html = html[:start] + new_outer_html + html[end:]
    return html


# ── 주간 ─────────────────────────────────────────────────

def update_trend(html: str, data: dict) -> str:
    t = data.get("trend", {})
    if not t.get("labels"):
        print("  ⚠️ 트렌드 없음")
        return html
    html = replace_js_array(html, "labels", t["labels"])
    html = replace_js_array(html, "skt", t["skt"])
    html = replace_js_array(html, "kt",  t["kt"])
    html = replace_js_array(html, "lgu", t["lgu"])
    ymax = int(max(max(t["skt"]), max(t["kt"]), max(t["lgu"])) * 1.1) + 1
    html = re.sub(r'const yMax\s*=\s*[^;]+;', f'const yMax = {ymax};', html)
    html = re.sub(r'출처: 네이버 DataLab API · [\d\.\s:]+수집',
                  f'출처: 네이버 DataLab API · {data["collected_at"]} 수집', html)
    print("  ✅ 트렌드")
    return html


def update_news(html: str, data: dict) -> str:
    news = data.get("news", {})
    if not any(news.values()):
        print("  ⚠️ 뉴스 없음")
        return html

    prompt = f"""뉴스 데이터로 3개 탭 HTML 생성. 날짜는 YYYY-MM-DD 형식.

데이터:
{json.dumps(news, ensure_ascii=False, indent=2)}

출력 (HTML만, ```없이):
<div id="np-skt">
  <div class="nc"><div class="nct"><span class="nb nb신규">신규</span><span class="ntitle">제목</span></div><div class="nsum">요약</div><div class="nmeta">날짜 · <a href="URL" target="_blank">출처</a></div></div>
</div>
<div id="np-kt" class="hidden">...</div>
<div id="np-lgu" class="hidden">...</div>

각 통신사 최대 3건."""

    try:
        resp = clean(api_call(prompt, 3000))
        for sid in ["np-skt", "np-kt", "np-lgu"]:
            m = re.search(rf'(<div[^>]+id=["\']?{sid}["\']?[^>]*>[\s\S]+?)(?=<div[^>]+id=["\']?np-(?!{sid})|$)', resp)
            if m:
                html = swap_by_id(html, sid, m.group(1).rstrip())
        print("  ✅ 뉴스")
    except Exception as e:
        print(f"  ⚠️ 뉴스 실패: {e}")
    return html


def update_sentiment(html: str, data: dict) -> str:
    sentiment = data.get("sentiment", {})
    if not any(sentiment.values()):
        print("  ⚠️ 고객반응 없음")
        return html

    prompt = f"""고객반응 데이터로 3개 탭 HTML 생성. 최근 4주 이내.

데이터:
{json.dumps(sentiment, ensure_ascii=False, indent=2)}

출력 (HTML만, ```없이):
<div id="sent-skt">
  <div class="srcs" style="margin-bottom:12px"><span class="srcbadge act">출처1</span><span class="srcbadge act">출처2</span></div>
  <div class="tr2" style="margin-bottom:12px">
    <button class="kw on" onclick="K('skt','kw1',this)">#키워드1</button>
    <button class="kw" onclick="K('skt','kw2',this)">#키워드2</button>
    <button class="kw" onclick="K('skt','kw3',this)">#키워드3</button>
  </div>
  <div id="skt-kw1">
    <div class="rc"><div class="rct"><span class="rbg rpos">긍정</span><span class="rtag treal">실제 댓글</span><span class="rtag tsrc">출처</span></div><div class="rtx">내용</div><div class="rsrc">출처 · 날짜 · <a href="URL" target="_blank">원문</a></div></div>
  </div>
  <div id="skt-kw2" class="hidden">...</div>
  <div id="skt-kw3" class="hidden">...</div>
</div>
<div id="sent-kt" class="hidden">...</div>
<div id="sent-lgu" class="hidden">...</div>

키워드 3개, 카드 긍정→부정→중립."""

    try:
        resp = clean(api_call(prompt, 5000))
        for sid in ["sent-skt", "sent-kt", "sent-lgu"]:
            m = re.search(rf'(<div[^>]+id=["\']?{sid}["\']?[^>]*>[\s\S]+?)(?=<div[^>]+id=["\']?sent-(?!{sid})|$)', resp)
            if m:
                html = swap_by_id(html, sid, m.group(1).rstrip())
        print("  ✅ 고객반응")
    except Exception as e:
        print(f"  ⚠️ 고객반응 실패: {e}")
    return html


def update_monthly(html: str, data: dict) -> str:
    monthly = data.get("monthly", {})
    if not any(v.get("title") for v in monthly.values()):
        print("  ⚠️ 월별혜택 없음")
        return html

    prompt = f"""월별혜택 데이터로 HTML 생성. content 비어도 최근 뉴스 기반으로 작성.

데이터:
{json.dumps(monthly, ensure_ascii=False, indent=2)}

출력 (HTML만, ```없이):
<div class="m3">
  <div class="mc">
    <div class="mch ms"><span>SKT — T day + 0 week</span><a href="https://sktmembership.tworld.co.kr/mps/pc-bff/sktmembership/tday.do" target="_blank" class="mlink" style="color:var(--skt-t)">T day →</a></div>
    <div class="mcb">
      <div class="mblk"><div class="mbtit"><span class="mbdot" style="background:var(--skt)"></span>T day — 전 등급</div><ul class="mblist"><li>혜택</li></ul></div>
      <div class="mblk"><div class="mbtit"><span class="mbdot" style="background:#6644ff"></span>0 week — 만13~34세 첫째주 5일</div><ul class="mblist"><li>혜택</li></ul></div>
    </div>
  </div>
  <div class="mc">
    <div class="mch mk"><span>KT — 달달혜택</span><a href="https://event.kt.com/html/event/ongoing_event_view.html?pcEvtNo=13783" target="_blank" class="mlink" style="color:var(--kt-t)">달달혜택 →</a></div>
    <div class="mcb"><div class="mblk"><div class="mbtit"><span class="mbdot" style="background:var(--kt)"></span>달달초이스</div><ul class="mblist"><li>혜택</li></ul></div></div>
  </div>
  <div class="mc">
    <div class="mch ml"><span>LGU+ — 유플투쁠</span><a href="https://www.lguplus.com/benefit/uplustobeul" target="_blank" class="mlink" style="color:var(--lgu-t)">유플투쁠 →</a></div>
    <div class="mcb"><div class="mblk"><div class="mbtit"><span class="mbdot" style="background:var(--lgu)"></span>투쁠데이</div><ul class="mblist"><li>혜택</li></ul></div></div>
  </div>
</div>"""

    try:
        resp = clean(api_call(prompt, 3000))
        m = re.search(r'<div\s+class=["\']m3["\']>[\s\S]+', resp)
        if m:
            new_m3 = m.group(0)
            # m3 div의 끝 찾기
            depth = 0
            pos = 0
            end = len(new_m3)
            for i, ch in enumerate(new_m3):
                if new_m3[i:i+4] == '<div':
                    depth += 1
                elif new_m3[i:i+6] == '</div>':
                    depth -= 1
                    if depth == 0:
                        end = i + 6
                        break
            new_m3 = new_m3[:end]
            # HTML에서 m3 교체
            html = re.sub(r'<div\s+class=["\']m3["\']>[\s\S]+?</div>\s*</div>\s*</div>',
                          new_m3, html, count=1)
            print("  ✅ 월별혜택")
        else:
            print("  ⚠️ 월별혜택 m3 없음")
    except Exception as e:
        print(f"  ⚠️ 월별혜택 실패: {e}")
    return html


# ── 격주 ─────────────────────────────────────────────────

def update_history(html: str, data: dict) -> str:
    news = data.get("news", {})
    prompt = f"""뉴스에서 멤버십 변경/신설/종료 이력 최근 5건.
기준일: {data['collected_at']}
뉴스: {json.dumps(news, ensure_ascii=False)}

출력 (HTML만):
<tbody id="hist-tbody">
<tr><td>YYYY.MM.DD</td><td><span class="cb bs">SKT</span></td><td>프로그램</td><td>내용</td><td><span class="tb t변경">변경</span></td><td><a href="URL" target="_blank">출처</a></td></tr>
</tbody>"""
    try:
        resp = clean(api_call(prompt, 2000))
        m = re.search(r'<tbody[^>]+id=["\']?hist-tbody["\']?[^>]*>[\s\S]+?</tbody>', resp)
        if m:
            html = re.sub(r'<tbody[^>]+id=["\']?hist-tbody["\']?[^>]*>[\s\S]+?</tbody>',
                          m.group(0), html, count=1)
            print("  ✅ 변경이력")
        else:
            print("  ⚠️ 변경이력 파싱 실패")
    except Exception as e:
        print(f"  ⚠️ 변경이력 실패: {e}")
    return html


def update_non_telecom(html: str, data: dict) -> str:
    prompt = f"""기준일 {data['collected_at']} 비통신 멤버십 최신 동향.
출력 (HTML만):
<div class="ntg">
  <div class="ntc"><div class="nth" style="background:linear-gradient(135deg,#03c75a,#02a84c);color:#fff">네이버플러스 멤버십</div><div class="ntb"><span class="nttag" style="background:#e6f9ee;color:#1a7f3c">구독형 · 월 4,900원</span><br><b>핵심:</b> 내용<br><br><b>주목:</b> 내용</div></div>
  (쿠팡 와우, 현대카드, 당근, 카카오페이/토스, 올리브영·무신사 총 6개)
</div>"""
    try:
        resp = clean(api_call(prompt, 3000))
        m = re.search(r'<div\s+class=["\']ntg["\']>[\s\S]+', resp)
        if m:
            # ntg div 끝 찾기
            ntg = m.group(0)
            depth = 0
            end = len(ntg)
            for i in range(len(ntg)):
                if ntg[i:i+4] == '<div': depth += 1
                elif ntg[i:i+6] == '</div>':
                    depth -= 1
                    if depth == 0: end = i + 6; break
            html = re.sub(r'<div\s+class=["\']ntg["\']>[\s\S]+?</div>\s*</div>',
                          ntg[:end], html, count=1)
            print("  ✅ 비통신 멤버십")
        else:
            print("  ⚠️ 비통신 파싱 실패")
    except Exception as e:
        print(f"  ⚠️ 비통신 실패: {e}")
    return html


def update_ai_insight(html: str, data: dict) -> str:
    namu = data.get("namu", {})
    news = data.get("news", {})
    prompt = f"""AI 인사이트 HTML. 기준일 {data['collected_at']}
나무위키: SKT {namu.get('skt',{}).get('text','')[:600]} KT {namu.get('kt',{}).get('text','')[:600]} LGU+ {namu.get('lgu',{}).get('text','')[:600]}
뉴스: {json.dumps(news, ensure_ascii=False)}

출력 (HTML만):
<div class="swot-grid">
  <div class="swot-card"><div class="swot-hdr sh-skt"><div class="swot-ico">📱</div><span>SKT T멤버십</span></div>
    <div class="swot-body">
      <div class="swot-section str"><div class="swot-label str">강점</div><div class="swot-items"><div class="swot-item">내용</div></div></div>
      <div class="swot-section wk"><div class="swot-label wk">약점</div><div class="swot-items"><div class="swot-item">내용</div></div></div>
    </div></div>
  <div class="swot-card"><div class="swot-hdr sh-kt"><div class="swot-ico">📶</div><span>KT 멤버십</span></div>
    <div class="swot-body">
      <div class="swot-section str"><div class="swot-label str">강점</div><div class="swot-items"><div class="swot-item">내용</div></div></div>
      <div class="swot-section wk"><div class="swot-label wk">약점</div><div class="swot-items"><div class="swot-item">내용</div></div></div>
    </div></div>
  <div class="swot-card"><div class="swot-hdr sh-lgu"><div class="swot-ico">🌸</div><span>LGU+ 멤버십</span></div>
    <div class="swot-body">
      <div class="swot-section str"><div class="swot-label str">강점</div><div class="swot-items"><div class="swot-item">내용</div></div></div>
      <div class="swot-section wk"><div class="swot-label wk">약점</div><div class="swot-items"><div class="swot-item">내용</div></div></div>
    </div></div>
</div>
<div class="ins-list">
  <div class="ins-item"><div class="ins-num">1</div><div class="ins-txt"><b>제목:</b> 내용</div></div>
  (5개)
</div>"""
    try:
        resp = clean(api_call(prompt, 3000))
        swot = re.search(r'<div\s+class=["\']swot-grid["\']>[\s\S]+?(?=<div\s+class=["\']ins-list)', resp)
        ins  = re.search(r'<div\s+class=["\']ins-list["\']>[\s\S]+?</div>\s*</div>', resp)
        if swot:
            html = re.sub(r'<div\s+class=["\']swot-grid["\']>[\s\S]+?(?=<div\s+class=["\']ins-list)',
                          swot.group(0), html, count=1)
        if ins:
            html = re.sub(r'<div\s+class=["\']ins-list["\']>[\s\S]+?</div>\s*</div>',
                          ins.group(0), html, count=1)
        if swot or ins: print("  ✅ AI 인사이트")
        else: print("  ⚠️ AI 인사이트 파싱 실패")
    except Exception as e:
        print(f"  ⚠️ AI 인사이트 실패: {e}")
    return html


# ── 월간 ─────────────────────────────────────────────────

def update_overview(html: str, data: dict) -> str:
    namu = data.get("namu", {})
    news = data.get("news", {})
    monthly = data.get("monthly", {})
    prompt = f"""이달 핵심 동향 HTML. 기준일 {data['collected_at']}
나무위키: SKT {namu.get('skt',{}).get('text','')[:800]} KT {namu.get('kt',{}).get('text','')[:800]} LGU+ {namu.get('lgu',{}).get('text','')[:800]}
뉴스: {json.dumps(news, ensure_ascii=False)}
월별혜택: {json.dumps(monthly, ensure_ascii=False)}

출력 (HTML만):
<div class="og">
  <div class="oc cs"><div class="ol"><span class="cb bs">SKT</span></div><div class="ov">핵심변경</div><div class="od">설명</div></div>
  <div class="oc ck"><div class="ol"><span class="cb bk">KT</span></div><div class="ov">핵심변경</div><div class="od">설명</div></div>
  <div class="oc cl"><div class="ol"><span class="cb bl">LGU+</span></div><div class="ov">핵심변경</div><div class="od">설명</div></div>
  <div class="oc cg"><div class="ol" style="font-size:11px;color:var(--tx3)">주요 변경</div><div class="ov" style="font-size:13px">변경</div><div class="od">설명</div></div>
</div>
<div class="tl">
  <div class="ti"><div class="tdot" style="background:var(--skt)"></div><div class="tt"><span class="cb bs">SKT</span> 상세</div></div>
  <div class="ti"><div class="tdot" style="background:var(--kt)"></div><div class="tt"><span class="cb bk">KT</span> 상세</div></div>
  <div class="ti"><div class="tdot" style="background:var(--lgu)"></div><div class="tt"><span class="cb bl">LGU+</span> 상세</div></div>
</div>"""
    try:
        resp = clean(api_call(prompt, 2000))
        og = re.search(r'<div\s+class=["\']og["\']>[\s\S]+?</div>\s*</div>\s*</div>\s*</div>\s*</div>', resp)
        tl = re.search(r'<div\s+class=["\']tl["\']>[\s\S]+?</div>\s*</div>\s*</div>\s*</div>', resp)
        if og:
            html = re.sub(r'<div\s+class=["\']og["\']>[\s\S]+?</div>\s*</div>\s*</div>\s*</div>\s*</div>',
                          og.group(0), html, count=1)
        if tl:
            html = re.sub(r'<div\s+class=["\']tl["\']>[\s\S]+?</div>\s*</div>\s*</div>\s*</div>',
                          tl.group(0), html, count=1)
        if og or tl: print("  ✅ 개요")
        else: print("  ⚠️ 개요 파싱 실패")
    except Exception as e:
        print(f"  ⚠️ 개요 실패: {e}")
    return html


def update_regular_benefits(html: str, data: dict) -> str:
    namu = data.get("namu", {})
    if not any(v.get("text") for v in namu.values()):
        print("  ⚠️ 나무위키 없음"); return html
    prompt = f"""상시 혜택 비교 테이블 HTML. 기준일 {data['collected_at']}
SKT: {namu.get('skt',{}).get('text','')[:2500]}
KT: {namu.get('kt',{}).get('text','')[:2500]}
LGU+: {namu.get('lgu',{}).get('text','')[:2500]}

카테고리별 <div class="cl2">카테고리</div> + <table class="ct">...</table> 형태.
카테고리: 영화관, 베이커리, 패밀리레스토랑, 피자, 카페·디저트, 편의점
LGU+ CGV: 최대 4,000원 할인. SKT 롯데시네마: 종료(class="wt"). 이상/할인 텍스트."""
    try:
        resp = clean(api_call(prompt, 4000))
        # 첫 cl2부터 sec 끝 직전까지 교체
        m_start = re.search(r'<div\s+class=["\']cl2["\']>', resp)
        if m_start:
            new_content = resp[m_start.start():]
            # 기존 HTML에서 첫 cl2부터 rg sec 닫힘 직전까지 교체
            html = re.sub(
                r'(<div\s+class=["\']cl2["\']>[\s\S]+?)(?=</div>\s*<!--\s*월별|</div>\s*<!-- VIP|</div>\s*\n\s*<!-- 월)',
                new_content, html, count=1
            )
            print("  ✅ 상시혜택")
        else:
            print("  ⚠️ 상시혜택 파싱 실패")
    except Exception as e:
        print(f"  ⚠️ 상시혜택 실패: {e}")
    return html


def update_vip(html: str, data: dict) -> str:
    namu = data.get("namu", {})
    prompt = f"""VIP 특화 혜택 테이블. 기준일 {data['collected_at']}
SKT: {namu.get('skt',{}).get('text','')[:1200]}
KT: {namu.get('kt',{}).get('text','')[:1200]}
LGU+: {namu.get('lgu',{}).get('text','')[:1200]}

출력 (HTML만):
<table class="vt">
  <thead><tr><th>구분</th><th class="th-skt"><span class="cb bs">SKT</span> VIP Pick</th><th class="th-kt"><span class="cb bk">KT</span> VIP·VVIP 초이스</th><th class="th-lgu"><span class="cb bl">LGU+</span> VIP콕</th></tr></thead>
  <tbody>
    <tr><td>제공 주기</td><td>내용</td><td>내용</td><td>내용</td></tr>
    <tr><td>영화</td><td>내용</td><td>롯데시네마 2인 무료</td><td>내용</td></tr>
    <tr><td>OTT·구독</td><td>내용</td><td>내용</td><td>내용</td></tr>
    <tr><td>생일</td><td>내용</td><td>내용</td><td>내용</td></tr>
  </tbody>
</table>"""
    try:
        resp = clean(api_call(prompt, 2000))
        m = re.search(r'<table\s+class=["\']vt["\']>[\s\S]+?</table>', resp)
        if m:
            html = re.sub(r'<table\s+class=["\']vt["\']>[\s\S]+?</table>', m.group(0), html, count=1)
            print("  ✅ VIP 특화")
        else:
            print("  ⚠️ VIP 파싱 실패")
    except Exception as e:
        print(f"  ⚠️ VIP 실패: {e}")
    return html


def update_date(html: str, collected_at: str) -> str:
    d = collected_at.split(" ")[0]
    html = re.sub(r'\d{4}\.\d{2}\.\d{2} 기준', f'{d} 기준', html)
    print(f"  ✅ 기준일: {d}")
    return html


# ── 메인 ─────────────────────────────────────────────────

def generate_dashboard(collected: dict) -> str:
    html_path = DEPLOY_DIR / "index.html"
    if not html_path.exists():
        raise FileNotFoundError(f"기준 HTML 없음: {html_path}")

    html = html_path.read_text(encoding="utf-8")
    is_monthly  = is_first_week_of_month()
    is_biweekly = is_odd_week()

    mode = "🗓️ 월간" if is_monthly else ("📋 격주" if is_biweekly else "📅 주간")
    print(f"  HTML: {len(html):,}자 | 모드: {mode}")

    print("\n  [주간]")
    html = update_trend(html, collected)
    html = update_news(html, collected)
    html = update_sentiment(html, collected)
    html = update_monthly(html, collected)

    if is_monthly or is_biweekly:
        print("\n  [격주]")
        html = update_history(html, collected)
        html = update_non_telecom(html, collected)
        html = update_ai_insight(html, collected)

    if is_monthly:
        print("\n  [월간]")
        html = update_overview(html, collected)
        html = update_regular_benefits(html, collected)
        html = update_vip(html, collected)

    html = update_date(html, collected["collected_at"])
    print(f"\n  최종: {len(html):,}자")
    return html


def save_and_deploy(html: str) -> str:
    DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
    html_path = DEPLOY_DIR / "index.html"
    html_path.write_text(html, encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    for cmd in [
        ["git", "-C", str(DEPLOY_DIR), "add", "index.html"],
        ["git", "-C", str(DEPLOY_DIR), "commit", "-m", f"Auto update {today}"],
        ["git", "-C", str(DEPLOY_DIR), "push"],
    ]:
        r = __import__('subprocess').run(cmd, capture_output=True, text=True)
        if r.returncode != 0 and "nothing to commit" not in r.stdout + r.stderr:
            raise RuntimeError(f"git 실패: {r.stderr}")
    print(f"  배포 → {PAGES_URL}")
    return PAGES_URL
