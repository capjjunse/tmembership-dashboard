"""
collectors/benefit.py — 상시 혜택 + 월별 혜택 수집
SKT: Playwright + 공식 페이지 직접 크롤링
KT:  네이버 뉴스 API로 이달 달달혜택 기사 수집 → API 정리
LGU: Playwright + 공식 페이지 직접 크롤링
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


def playwright_get_main_content(url: str, wait_sec: int = 5) -> str:
    """Playwright로 JS 렌더링 페이지에서 nav/header/footer 제거 후 본문 추출"""
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
                 '.share', '.sns-wrap', '[class*="share"]', '[class*="nav"]',
                 '[class*="header"]', '[class*="footer"]'].forEach(function(sel) {
                    document.querySelectorAll(sel).forEach(function(el) { el.remove(); });
                });
                return document.body.innerText;
            }""")
            browser.close()
            return (text or "")[:5000]
    except Exception as e:
        print(f"    [WARN] Playwright ({url}): {e}")
        return ""


def fetch_kt_news_article(month: int, year: int) -> str:
    """네이버 뉴스 API로 KT 달달혜택 기사 전문 가져오기"""
    queries = [
        f"KT 멤버십 {month}월 달달혜택 {year}",
        f"KT 달달혜택 {month}월",
        f"KT멤버십 달달혜택 {month}월",
    ]
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
            # 이달 기사만 필터 (제목에 해당 월 포함)
            month_str = f"{month}월"
            filtered = [i for i in items if month_str in i.get("title", "") or month_str in i.get("description", "")]
            if not filtered:
                filtered = items  # 없으면 그냥 다 사용

            parts = []
            for item in filtered[:3]:
                title = BeautifulSoup(item.get("title", ""), "html.parser").get_text()
                desc  = BeautifulSoup(item.get("description", ""), "html.parser").get_text()
                # 기사 본문 fetch 시도
                link = item.get("link", "")
                if link and "news.naver.com" in link:
                    try:
                        article_resp = requests.get(link, headers=REQUEST_HEADERS, timeout=8)
                        article_soup = BeautifulSoup(article_resp.text, "html.parser")
                        body = article_soup.select_one("#newsct_article, #articeBody, .news_end")
                        if body:
                            desc = body.get_text(separator=" ", strip=True)[:500]
                    except:
                        pass
                parts.append(f"[기사] {title}\n{desc}")

            text = "\n\n".join(parts)
            if len(text) > 100:
                print(f"    KT 기사 수집: {len(text)}자 ({query})")
                return text[:3000]
            time.sleep(REQUEST_DELAY)
        except Exception as e:
            print(f"    [WARN] KT 뉴스 ({query}): {e}")
    return ""


def extract_items_with_api(carrier: str, raw_text: str, month: int, year: int) -> list:
    """Anthropic API로 텍스트에서 혜택 항목만 추출"""
    if not raw_text or not ANTHROPIC_API_KEY:
        return []
    try:
        import anthropic, json, re
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        carrier_names = {
            "skt": "SKT T멤버십 T day",
            "kt":  "KT 달달혜택",
            "lgu": "LG유플러스 유플투쁠"
        }
        prompt = f"""아래 텍스트에서 {carrier_names.get(carrier, carrier)} {year}년 {month}월 실제 멤버십 혜택 항목만 추출해줘.

텍스트:
{raw_text[:3000]}

출력: JSON 배열만 (```없이)
["혜택1", "혜택2", ...]

규칙:
- 반드시 {year}년 {month}월 혜택만 (다른 달 내용 제외)
- 제휴처명 + 구체적 할인/혜택 내용 (예: "쉐이크쉑 쉑버거 1+1", "빕스 40% 할인", "파리바게뜨 500원 할인")
- 네비게이션, 공유버튼, 법적고지, SNS 등 제외
- 최대 8개, 항목당 30자 이내
- {month}월 해당 내용이 없으면 []"""

        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = re.sub(r'```[^\n]*\n?', '', msg.content[0].text.strip()).strip()
        result = json.loads(text)
        print(f"    {carrier.upper()} items ({month}월): {result}")
        return result
    except Exception as e:
        print(f"    [WARN] {carrier} 추출 실패: {e}")
        return []


def fetch_skt_monthly() -> dict:
    month = datetime.today().month
    year  = datetime.today().year
    print("    SKT T day 공식 페이지 크롤링...")
    raw = playwright_get_main_content(
        "https://sktmembership.tworld.co.kr/mps/pc-bff/program/tday.do",
        wait_sec=5
    )
    print(f"    SKT content: {len(raw)}자")
    items = extract_items_with_api("skt", raw, month, year) if raw else []
    return {
        "carrier": "skt",
        "title": f"{month}월 T day + 0 week",
        "url": "https://sktmembership.tworld.co.kr/mps/pc-bff/program/tday.do",
        "content": raw,
        "items": items,
    }


def fetch_kt_monthly() -> dict:
    month = datetime.today().month
    year  = datetime.today().year
    print("    KT 달달혜택 뉴스 기사 수집...")
    raw = fetch_kt_news_article(month, year)
    items = extract_items_with_api("kt", raw, month, year) if raw else []
    return {
        "carrier": "kt",
        "title": f"{month}월 달달혜택",
        "url": "https://membership.kt.com/discount/benefit/DaldalBenefit.do",
        "content": raw,
        "items": items,
    }


def fetch_lgu_monthly() -> dict:
    month = datetime.today().month
    year  = datetime.today().year
    print("    LGU+ 유플투쁠 공식 페이지 크롤링...")
    raw = playwright_get_main_content(
        "https://www.lguplus.com/benefit-plus",
        wait_sec=6
    )
    print(f"    LGU+ content: {len(raw)}자")
    items = extract_items_with_api("lgu", raw, month, year) if raw else []
    return {
        "carrier": "lgu",
        "title": f"{month}월 유플투쁠",
        "url": "https://www.lguplus.com/benefit-plus",
        "content": raw,
        "items": items,
    }


def fetch_monthly() -> dict:
    return {
        "skt": fetch_skt_monthly(),
        "kt":  fetch_kt_monthly(),
        "lgu": fetch_lgu_monthly(),
    }
