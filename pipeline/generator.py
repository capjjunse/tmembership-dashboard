"""
generator.py — 주간/격주/월간 업데이트 분기
BeautifulSoup 파싱 방식으로 안정적 교체
"""
import json
import re
import subprocess
import anthropic
from pathlib import Path
from datetime import datetime, date
from bs4 import BeautifulSoup
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, DEPLOY_DIR

PAGES_URL = "https://capjjunse.github.io/tmembership-dashboard/"


def is_first_week_of_month() -> bool:
    return datetime.today().day <= 7


def is_odd_week() -> bool:
    return date.today().isocalendar()[1] % 2 == 1


def api_call(prompt: str, max_tokens: int = 4000) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def clean_response(response: str) -> str:
    """마크다운 코드블록 제거"""
    return re.sub(r'```[^\n]*\n?', '', response).strip()


def replace_js_array(html: str, var_name: str, new_data: list) -> str:
    pattern = rf'const {var_name}\s*=\s*\[.*?\];'
    replacement = f'const {var_name} = {json.dumps(new_data)};'
    return re.sub(pattern, replacement, html, flags=re.DOTALL)


def replace_element_by_id(html: str, elem_id: str, new_html: str) -> str:
    """id로 div 요소를 찾아 innerHTML 교체 (BeautifulSoup 방식)"""
    soup = BeautifulSoup(html, "html.parser")
    target = soup.find(id=elem_id)
    if not target:
        print(f"    ⚠️ #{elem_id} 못 찾음")
        return html
    new_soup = BeautifulSoup(new_html, "html.parser")
    new_elem = new_soup.find()
    if new_elem:
        target.replace_with(new_elem)
    return str(soup)


def replace_element_by_class(html: str, tag: str, class_name: str, new_html: str) -> str:
    """class로 요소 찾아 교체"""
    soup = BeautifulSoup(html, "html.parser")
    target = soup.find(tag, class_=class_name)
    if not target:
        print(f"    ⚠️ {tag}.{class_name} 못 찾음")
        return html
    new_soup = BeautifulSoup(new_html, "html.parser")
    new_elem = new_soup.find()
    if new_elem:
        target.replace_with(new_elem)
    return str(soup)


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

    prompt = f"""아래 뉴스 데이터로 3개 탭 HTML을 생성해줘.

데이터:
{json.dumps(news, ensure_ascii=False, indent=2)}

출력 형식 (```없이 HTML만):
<div id="np-skt">
  <div class="nc"><div class="nct"><span class="nb nb신규">신규</span><span class="ntitle">제목</span></div><div class="nsum">요약</div><div class="nmeta">날짜 · <a href="URL" target="_blank">출처명</a></div></div>
</div>
<div id="np-kt" class="hidden">...</div>
<div id="np-lgu" class="hidden">...</div>

규칙: 각 통신사 최대 3건. 날짜는 YYYY-MM-DD 형식. 배지: nb신규/nb변경/nb종료/nb이슈."""

    try:
        response = clean_response(api_call(prompt, max_tokens=3000))
        for sid in ["np-skt", "np-kt", "np-lgu"]:
            soup = BeautifulSoup(response, "html.parser")
            new_elem = soup.find(id=sid)
            if new_elem:
                html = replace_element_by_id(html, sid, str(new_elem))
        print("  ✅ 뉴스")
    except Exception as e:
        print(f"  ⚠️ 뉴스 실패: {e} — 기존 유지")
    return html


def update_sentiment(html: str, data: dict) -> str:
    sentiment = data.get("sentiment", {})
    if not any(sentiment.values()):
        print("  ⚠️ 고객반응 없음 — 기존 유지")
        return html

    prompt = f"""아래 고객반응 데이터로 3개 탭 HTML을 생성해줘.
기준일: {data['collected_at']} (최근 4주 이내)

데이터:
{json.dumps(sentiment, ensure_ascii=False, indent=2)}

출력 형식 (```없이 HTML만):
<div id="sent-skt">
  <div class="srcs" style="margin-bottom:12px"><span class="srcbadge act">출처1</span></div>
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

규칙: 키워드 3개, 카드 긍정→부정→중립 순서. 데이터 없으면 "최근 4주 수집 없음" 표시."""

    try:
        response = clean_response(api_call(prompt, max_tokens=5000))
        for sid in ["sent-skt", "sent-kt", "sent-lgu"]:
            soup = BeautifulSoup(response, "html.parser")
            new_elem = soup.find(id=sid)
            if new_elem:
                html = replace_element_by_id(html, sid, str(new_elem))
        print("  ✅ 고객반응")
    except Exception as e:
        print(f"  ⚠️ 고객반응 실패: {e} — 기존 유지")
    return html


def update_monthly(html: str, data: dict) -> str:
    monthly = data.get("monthly", {})
    if not any(v.get("title") for v in monthly.values()):
        print("  ⚠️ 월별혜택 없음 — 건너뜀")
        return html

    prompt = f"""아래 월별혜택 데이터로 대시보드 월별혜택 섹션 HTML을 생성해줘.
content가 비어있어도 title/url 활용하고 최근 뉴스 기반으로 이번달 대표 혜택 작성.

데이터:
{json.dumps(monthly, ensure_ascii=False, indent=2)}

출력 형식 (```없이 HTML만):
<div class="m3">
  <div class="mc">
    <div class="mch ms"><span>SKT — T day + 0 week</span><a href="https://sktmembership.tworld.co.kr/mps/pc-bff/sktmembership/tday.do" target="_blank" class="mlink" style="color:var(--skt-t)">T day →</a></div>
    <div class="mcb">
      <div class="mblk"><div class="mbtit"><span class="mbdot" style="background:var(--skt)"></span>T day — 전 등급</div><ul class="mblist"><li>혜택1</li><li>혜택2</li></ul></div>
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
</div>

규칙: 할인 표기는 '할인' 텍스트. 이상 표기도 텍스트."""

    try:
        response = clean_response(api_call(prompt, max_tokens=3000))
        soup_resp = BeautifulSoup(response, "html.parser")
        new_m3 = soup_resp.find("div", class_="m3")
        if new_m3:
            html = replace_element_by_class(html, "div", "m3", str(new_m3))
            print("  ✅ 월별혜택")
        else:
            print("  ⚠️ 월별혜택 m3 못 찾음 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ 월별혜택 실패: {e} — 기존 유지")
    return html


# ════════════════════════════════════════════
# 격주 업데이트 (홀수 주)
# ════════════════════════════════════════════

def update_history(html: str, data: dict) -> str:
    news = data.get("news", {})
    prompt = f"""뉴스 데이터에서 멤버십 혜택 변경/신설/종료 이력 최근 5건 생성.
기준일: {data['collected_at']}
뉴스: {json.dumps(news, ensure_ascii=False)}

출력 형식 (```없이 HTML만):
<tbody id="hist-tbody">
  <tr><td>YYYY.MM.DD</td><td><span class="cb bs">SKT</span></td><td>프로그램</td><td>내용</td><td><span class="tb t변경">변경</span></td><td><a href="URL" target="_blank">출처</a></td></tr>
</tbody>"""
    try:
        response = clean_response(api_call(prompt, max_tokens=2000))
        soup_resp = BeautifulSoup(response, "html.parser")
        new_tbody = soup_resp.find("tbody", id="hist-tbody")
        if new_tbody:
            soup = BeautifulSoup(html, "html.parser")
            old = soup.find("tbody", id="hist-tbody")
            if old:
                old.replace_with(new_tbody)
                html = str(soup)
                print("  ✅ 변경이력")
        else:
            print("  ⚠️ 변경이력 파싱 실패 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ 변경이력 실패: {e}")
    return html


def update_non_telecom(html: str, data: dict) -> str:
    prompt = f"""기준일 {data['collected_at']} 비통신 멤버십 최신 동향 HTML.
출력 (```없이 HTML만):
<div class="ntg">
  <div class="ntc"><div class="nth" style="background:linear-gradient(135deg,#03c75a,#02a84c);color:#fff">네이버플러스 멤버십</div><div class="ntb"><span class="nttag" style="background:#e6f9ee;color:#1a7f3c">구독형 · 월 4,900원</span><br><b>핵심:</b> 내용<br><br><b>주목:</b> 내용</div></div>
  ... (쿠팡 와우, 현대카드, 당근, 카카오페이/토스, 올리브영·무신사 총 6개)
</div>"""
    try:
        response = clean_response(api_call(prompt, max_tokens=3000))
        soup_resp = BeautifulSoup(response, "html.parser")
        new_ntg = soup_resp.find("div", class_="ntg")
        if new_ntg:
            html = replace_element_by_class(html, "div", "ntg", str(new_ntg))
            print("  ✅ 비통신 멤버십")
        else:
            print("  ⚠️ 비통신 파싱 실패 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ 비통신 실패: {e}")
    return html


def update_ai_insight(html: str, data: dict) -> str:
    namu = data.get("namu", {})
    news = data.get("news", {})
    prompt = f"""통신 3사 멤버십 AI 인사이트 HTML 생성.
기준일: {data['collected_at']}
나무위키: SKT {namu.get('skt',{}).get('text','')[:600]} / KT {namu.get('kt',{}).get('text','')[:600]} / LGU+ {namu.get('lgu',{}).get('text','')[:600]}
뉴스: {json.dumps(news, ensure_ascii=False)}

출력 (```없이 HTML만):
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
  ... (5개)
</div>"""
    try:
        response = clean_response(api_call(prompt, max_tokens=3000))
        soup_resp = BeautifulSoup(response, "html.parser")
        swot = soup_resp.find("div", class_="swot-grid")
        ins  = soup_resp.find("div", class_="ins-list")
        if swot:
            html = replace_element_by_class(html, "div", "swot-grid", str(swot))
        if ins:
            html = replace_element_by_class(html, "div", "ins-list", str(ins))
        if swot or ins:
            print("  ✅ AI 인사이트")
        else:
            print("  ⚠️ AI 인사이트 파싱 실패 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ AI 인사이트 실패: {e}")
    return html


# ════════════════════════════════════════════
# 월간 업데이트 (첫째 주만)
# ════════════════════════════════════════════

def update_overview(html: str, data: dict) -> str:
    namu = data.get("namu", {})
    news = data.get("news", {})
    monthly = data.get("monthly", {})
    prompt = f"""이달 핵심 동향 섹션 HTML.
기준일: {data['collected_at']}
나무위키: SKT {namu.get('skt',{}).get('text','')[:800]} / KT {namu.get('kt',{}).get('text','')[:800]} / LGU+ {namu.get('lgu',{}).get('text','')[:800]}
뉴스: {json.dumps(news, ensure_ascii=False)}
월별혜택: {json.dumps(monthly, ensure_ascii=False)}

출력 (```없이 HTML만):
<div class="og">
  <div class="oc cs"><div class="ol"><span class="cb bs">SKT</span></div><div class="ov">핵심변경 1줄</div><div class="od">설명</div></div>
  <div class="oc ck"><div class="ol"><span class="cb bk">KT</span></div><div class="ov">핵심변경 1줄</div><div class="od">설명</div></div>
  <div class="oc cl"><div class="ol"><span class="cb bl">LGU+</span></div><div class="ov">핵심변경 1줄</div><div class="od">설명</div></div>
  <div class="oc cg"><div class="ol" style="font-size:11px;color:var(--tx3)">주요 변경</div><div class="ov" style="font-size:13px">변경</div><div class="od">설명</div></div>
</div>
<div class="tl">
  <div class="ti"><div class="tdot" style="background:var(--skt)"></div><div class="tt"><span class="cb bs">SKT</span> 상세</div></div>
  <div class="ti"><div class="tdot" style="background:var(--kt)"></div><div class="tt"><span class="cb bk">KT</span> 상세</div></div>
  <div class="ti"><div class="tdot" style="background:var(--lgu)"></div><div class="tt"><span class="cb bl">LGU+</span> 상세</div></div>
</div>"""
    try:
        response = clean_response(api_call(prompt, max_tokens=2000))
        soup_resp = BeautifulSoup(response, "html.parser")
        og = soup_resp.find("div", class_="og")
        tl = soup_resp.find("div", class_="tl")
        if og:
            html = replace_element_by_class(html, "div", "og", str(og))
        if tl:
            html = replace_element_by_class(html, "div", "tl", str(tl))
        if og or tl:
            print("  ✅ 개요(핵심동향)")
        else:
            print("  ⚠️ 개요 파싱 실패 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ 개요 실패: {e}")
    return html


def update_regular_benefits(html: str, data: dict) -> str:
    namu = data.get("namu", {})
    if not any(v.get("text") for v in namu.values()):
        print("  ⚠️ 나무위키 데이터 없음 — 기존 유지")
        return html
    prompt = f"""통신 3사 상시 혜택 비교 테이블 HTML.
기준일: {data['collected_at']}
SKT: {namu.get('skt',{}).get('text','')[:2500]}
KT: {namu.get('kt',{}).get('text','')[:2500]}
LGU+: {namu.get('lgu',{}).get('text','')[:2500]}

출력 (```없이 HTML만): <div class="cl2">영화관</div><table class="ct">...</table> ... 형태.
카테고리: 영화관, 베이커리, 패밀리레스토랑, 피자, 카페·디저트, 편의점
규칙: LGU+ CGV 최대 4,000원 할인. SKT 롯데시네마 종료(class="wt"). '이상'/'할인' 텍스트."""
    try:
        response = clean_response(api_call(prompt, max_tokens=4000))
        # cl2들을 감싸는 부모 섹션 찾아서 교체
        soup = BeautifulSoup(html, "html.parser")
        rg_sec = soup.find(id="rg")
        if rg_sec:
            soup_resp = BeautifulSoup(response, "html.parser")
            # sh div(헤더) 이후 내용 교체
            sh = rg_sec.find("div", class_="sh")
            if sh:
                # sh 이후 모든 태그 제거
                for sibling in list(sh.find_next_siblings()):
                    sibling.decompose()
                # 새 내용 추가
                for elem in soup_resp.contents:
                    rg_sec.append(elem)
                html = str(soup)
                print("  ✅ 상시혜택")
        else:
            print("  ⚠️ #rg 섹션 못 찾음 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ 상시혜택 실패: {e}")
    return html


def update_vip(html: str, data: dict) -> str:
    namu = data.get("namu", {})
    prompt = f"""VIP 특화 혜택 테이블 HTML.
기준일: {data['collected_at']}
SKT: {namu.get('skt',{}).get('text','')[:1200]}
KT: {namu.get('kt',{}).get('text','')[:1200]}
LGU+: {namu.get('lgu',{}).get('text','')[:1200]}

출력 (```없이 HTML만):
<table class="vt">
  <thead><tr><th>구분</th><th class="th-skt"><span class="cb bs">SKT</span> VIP Pick</th><th class="th-kt"><span class="cb bk">KT</span> VIP·VVIP 초이스</th><th class="th-lgu"><span class="cb bl">LGU+</span> VIP콕</th></tr></thead>
  <tbody>
    <tr><td>제공 주기</td><td>내용<br><a href="URL" target="_blank" class="vlink">링크 →</a></td><td>...</td><td>...</td></tr>
    <tr><td>영화</td><td>...</td><td>롯데시네마 2인 무료</td><td>...</td></tr>
    <tr><td>OTT·구독</td><td>...</td><td>...</td><td>...</td></tr>
    <tr><td>생일</td><td>...</td><td>...</td><td>...</td></tr>
  </tbody>
</table>"""
    try:
        response = clean_response(api_call(prompt, max_tokens=2000))
        soup_resp = BeautifulSoup(response, "html.parser")
        new_vt = soup_resp.find("table", class_="vt")
        if new_vt:
            html = replace_element_by_class(html, "table", "vt", str(new_vt))
            print("  ✅ VIP 특화")
        else:
            print("  ⚠️ VIP 파싱 실패 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ VIP 실패: {e}")
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
    is_monthly  = is_first_week_of_month()
    is_biweekly = is_odd_week()

    if is_monthly:
        mode = "🗓️ 월간 전체 (첫째 주)"
    elif is_biweekly:
        mode = "📋 격주 (홀수 주)"
    else:
        mode = "📅 주간"

    print(f"  기준 HTML: {len(html):,}자 | 모드: {mode}")

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
    print(f"  배포 완료 → {PAGES_URL}")
    return PAGES_URL
