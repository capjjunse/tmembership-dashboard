"""
collectors/benefit.py — 상시 혜택 + 월별 혜택 수집
SKT: Playwright + T day / 0 week 섹션 분리
KT:  네이버 뉴스 API + 달달혜택 / 고객보답 섹션
LGU: Playwright + 유플투쁠 공식 페이지
"""
import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from config import REQUEST_HEADERS, REQUEST_DELAY, REQUEST_TIMEOUT
from config import NAVER_SEARCH_CLIENT_ID, NAVER_SEARCH_CLIENT_SECRET
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

NAMU_URLS = {
    "skt": "https://namu.wiki/w/T%20Membership",
    "kt":  "https://namu.wiki/w/KT%20%EB%A9%A4%EB%B2%84%EC%8B%AD",
    "lgu": "https://namu.wiki/w/U%2B%EB%A9%A4%EB%B2%84%EC%8B%AD",
}


def fetch_namu(carrier: str) -> dict:
    url = NAMU_URLS[carrier]
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        article = soup.select_one("article") or soup.select_one('[class*="wiki-content"]') or soup.body
        text = article.get_text(separator="\n", strip=True) if article else ""
        time.sleep(REQUEST_DELAY)
        return {"carrier": carrier, "text": text[:8000], "url": url}
    except Exception as e:
        print(f"    [WARN] 나무위키 ({carrier}): {e}")
        return {"carrier": carrier, "text": "", "url": url}


def fetch_all_namu() -> dict:
    return {c: fetch_namu(c) for c in ["skt", "kt", "lgu"]}


def playwright_get_main_content(url: str, wait_sec: int = 7) -> str:
    """Playwright로 JS 렌더링 페이지에서 본문 추출"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except:
                pass
            time.sleep(wait_sec)
            text = page.evaluate("""() => {
                ['nav', 'header', 'footer', '.gnb', '.lnb', '.snb',
                 '.share', '.sns-wrap', '[class*="share"]'].forEach(function(sel) {
                    try { document.querySelectorAll(sel).forEach(function(el) { el.remove(); }); } catch(e) {}
                });
                return document.body.innerText;
            }""")
            browser.close()
            return (text or "")[:6000]
    except Exception as e:
        print(f"    [WARN] Playwright ({url}): {e}")
        return ""


def extract_sections_with_api(carrier: str, raw_text: str, month: int, year: int) -> list:
    """
    Anthropic API로 섹션별 혜택 추출
    Returns: [{"title": "섹션명", "subtitle": "부제목", "dot": "색상변수", "items": [...]}, ...]
    """
    if not raw_text or not ANTHROPIC_API_KEY:
        return []
    try:
        import anthropic, json, re
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        if carrier == "skt":
            prompt = f"""아래 SKT T멤버십 페이지 텍스트에서 {year}년 {month}월 혜택을 섹션별로 추출해줘.

텍스트:
{raw_text[:4000]}

출력: JSON 배열만 (```없이)
[
  {{"title": "T day — 전 등급", "dot": "var(--skt)", "items": ["혜택1", "혜택2"]}},
  {{"title": "0 week — 만13~34세 · 첫째주 5일", "dot": "#6644ff", "items": ["혜택1", "혜택2"]}},
  {{"title": "VIP only 해피아워", "dot": "#9944ff", "items": ["혜택1"]}}
]

규칙:
- T day 혜택과 0 week 혜택을 반드시 분리
- VIP only 혜택 있으면 별도 섹션으로
- 각 섹션 items: 제휴처명 + 구체적 혜택 (예: "쉐이크쉑 20% 할인", "뚜레쥬르 300원 적립")
- {month}월 내용만, 최대 6개/섹션, 30자 이내
- 내용 없으면 빈 배열"""

        elif carrier == "kt":
            prompt = f"""아래 KT 멤버십 관련 텍스트에서 {year}년 {month}월 혜택을 섹션별로 추출해줘.

텍스트:
{raw_text[:4000]}

출력: JSON 배열만 (```없이)
[
  {{"title": "달달초이스 (택1) — 매월 15일~말일", "dot": "var(--kt)", "items": ["혜택1", "혜택2"]}},
  {{"title": "달달스페셜 (중복 적용)", "dot": "#ff4444", "items": ["혜택1", "혜택2"]}},
  {{"title": "고객보답 프로그램 (2026 한시)", "dot": "#bb0000", "items": ["혜택1"]}}
]

규칙:
- 달달초이스, 달달스페셜, 고객보답 프로그램을 반드시 분리
- 고객보답 프로그램: 매월 2회 새로운 혜택 제공, 데이터/OTT/보험 등 내용 포함
- {month}월 내용만, 최대 6개/섹션, 30자 이내
- 없으면 빈 배열"""

        elif carrier == "lgu":
            prompt = f"""아래 LG유플러스 유플투쁠 페이지 텍스트에서 {year}년 {month}월 혜택을 섹션별로 추출해줘.

텍스트:
{raw_text[:4000]}

출력: JSON 배열만 (```없이)
[
  {{"title": "투쁠데이 — 매월 특정일 오전 11시 선착순", "dot": "var(--lgu)", "items": ["혜택1", "혜택2"]}},
  {{"title": "스페셜데이 — 전 등급", "dot": "#dd44aa", "items": ["혜택1"]}},
  {{"title": "장기고객데이 — 4주차 목요일 · 5년↑ VIP", "dot": "#ff55cc", "items": ["혜택1"]}}
]

규칙:
- 투쁠데이, 스페셜데이, 장기고객데이 분리
- {month}월 내용만, 최대 6개/섹션, 30자 이내
- 없으면 빈 배열"""

        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        text = re.sub(r'```[^\n]*\n?', '', msg.content[0].text.strip()).strip()
        result = json.loads(text)
        print(f"    {carrier.upper()} sections ({month}월): {[s['title'] for s in result]}")
        return result
    except Exception as e:
        print(f"    [WARN] {carrier} 섹션 추출 실패: {e}")
        return []


def fetch_kt_news_article(month: int, year: int) -> str:
    """네이버 뉴스 API로 KT 달달혜택 + 고객보답 기사 수집"""
    queries = [
        f"KT 멤버십 {month}월 달달혜택 {year}",
        f"KT 달달혜택 {month}월 {year}",
        f"KT멤버십 달달초이스 {month}월",
    ]
    best_text = ""
    for query in queries:
        try:
            resp = requests.get(
                "https://openapi.naver.com/v1/search/news.json",
                headers={
                    "X-Naver-Client-Id":     NAVER_SEARCH_CLIENT_ID,
                    "X-Naver-Client-Secret": NAVER_SEARCH_CLIENT_SECRET,
                },
                params={"query": query, "display": 5, "sort": "date"},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if not items:
                continue

            month_str = f"{month}월"
            filtered = [i for i in items if month_str in i.get("title","") + i.get("description","")]
            if not filtered:
                filtered = items[:3]

            parts = []
            for item in filtered[:3]:
                title = BeautifulSoup(item.get("title",""), "html.parser").get_text()
                desc  = BeautifulSoup(item.get("description",""), "html.parser").get_text()
                parts.append(f"[기사] {title}\n{desc}")

            text = "\n\n".join(parts)
            if len(text) > len(best_text):
                best_text = text
            time.sleep(REQUEST_DELAY)
        except Exception as e:
            print(f"    [WARN] KT 뉴스 ({query}): {e}")

    # 고객보답 뉴스도 추가
    try:
        resp = requests.get(
            "https://openapi.naver.com/v1/search/news.json",
            headers={
                "X-Naver-Client-Id":     NAVER_SEARCH_CLIENT_ID,
                "X-Naver-Client-Secret": NAVER_SEARCH_CLIENT_SECRET,
            },
            params={"query": f"KT 고객보답 프로그램 {year}", "display": 3, "sort": "date"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        for item in resp.json().get("items", [])[:2]:
            title = BeautifulSoup(item.get("title",""), "html.parser").get_text()
            desc  = BeautifulSoup(item.get("description",""), "html.parser").get_text()
            best_text += f"\n\n[고객보답] {title}\n{desc}"
    except:
        pass

    print(f"    KT 기사: {len(best_text)}자")
    return best_text[:4000]


def fetch_skt_monthly() -> dict:
    month = datetime.today().month
    year  = datetime.today().year
    print("    SKT T day 공식 페이지 크롤링...")
    raw = playwright_get_main_content(
        "https://sktmembership.tworld.co.kr/mps/pc-bff/program/tday.do",
        wait_sec=7
    )
    print(f"    SKT content: {len(raw)}자")
    sections = extract_sections_with_api("skt", raw, month, year) if raw else []
    return {
        "carrier": "skt",
        "title": f"{month}월 T day + 0 week",
        "url": "https://sktmembership.tworld.co.kr/mps/pc-bff/program/tday.do",
        "content": raw,
        "sections": sections,
        "items": [],  # 하위 호환성
    }


def fetch_kt_monthly() -> dict:
    month = datetime.today().month
    year  = datetime.today().year
    print("    KT 달달혜택 뉴스 수집...")
    raw = fetch_kt_news_article(month, year)
    sections = extract_sections_with_api("kt", raw, month, year) if raw else []
    return {
        "carrier": "kt",
        "title": f"{month}월 달달혜택 + 고객보답",
        "url": "https://membership.kt.com/discount/benefit/DaldalBenefit.do",
        "content": raw,
        "sections": sections,
        "items": [],
    }


def fetch_lgu_monthly() -> dict:
    month = datetime.today().month
    year  = datetime.today().year
    print("    LGU+ 유플투쁠 공식 페이지 크롤링...")
    raw = playwright_get_main_content(
        "https://www.lguplus.com/benefit-plus",
        wait_sec=8
    )
    print(f"    LGU+ content: {len(raw)}자")
    sections = extract_sections_with_api("lgu", raw, month, year) if raw else []
    return {
        "carrier": "lgu",
        "title": f"{month}월 유플투쁠",
        "url": "https://www.lguplus.com/benefit-plus",
        "content": raw,
        "sections": sections,
        "items": [],
    }


def fetch_monthly() -> dict:
    return {
        "skt": fetch_skt_monthly(),
        "kt":  fetch_kt_monthly(),
        "lgu": fetch_lgu_monthly(),
    }
