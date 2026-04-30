"""
collectors/benefit.py — 상시 혜택 + 월별 혜택 수집
SKT: Playwright + 공식 페이지 직접 크롤링
KT:  Playwright + 로그인 후 달달혜택 크롤링
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


def playwright_get_text(url: str, wait_sec: int = 3) -> str:
    """Playwright로 JS 렌더링 페이지 텍스트 추출"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(wait_sec)
            text = page.inner_text("body")
            browser.close()
            return text[:5000]
    except Exception as e:
        print(f"    [WARN] Playwright ({url}): {e}")
        return ""


def playwright_kt_login_and_get(url: str) -> str:
    """Playwright로 KT 로그인 후 달달혜택 페이지 크롤링"""
    kt_id = os.environ.get("KT_USERNAME", "")
    kt_pw = os.environ.get("KT_PASSWORD", "")
    if not kt_id or not kt_pw:
        print("    [WARN] KT_USERNAME/KT_PASSWORD 환경변수 없음")
        return ""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # KT 로그인 페이지 직접 접근
            login_url = "https://accounts.kt.com/wamui/AthWeb.do?urlcd=https%3A%2F%2Fmembership.kt.com%2Fmain%2FMainInfo.do"
            page.goto(login_url, wait_until="networkidle", timeout=30000)
            time.sleep(2)

            # 아이디/비밀번호 입력
            page.fill("#id", kt_id)
            page.fill("#password", kt_pw)
            time.sleep(1)

            # 로그인 버튼 클릭
            page.click("button[type='submit'], input[type='submit'], .btn-login, #loginBtn")
            time.sleep(3)

            # 달달혜택 페이지로 이동
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(3)

            text = page.inner_text("body")
            browser.close()
            return text[:5000]
    except Exception as e:
        print(f"    [WARN] KT 로그인 크롤링 실패: {e}")
        return ""


def extract_items_with_api(carrier: str, raw_text: str, month: int) -> list:
    """Anthropic API로 텍스트에서 혜택 항목 추출"""
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
        prompt = f"""아래 텍스트에서 {carrier_names.get(carrier, carrier)} {month}월 실제 혜택 항목만 추출해줘.

텍스트:
{raw_text[:3000]}

출력: JSON 배열만 (```없이)
["혜택1", "혜택2", ...]

규칙:
- 실제 제휴처 + 할인 내용 (예: "쉐이크쉑 20% 할인", "뚜레쥬르 300원 적립", "공차 50% 할인")
- 최대 8개, 항목당 30자 이내
- 없으면 []"""
        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        text = re.sub(r'```[^\n]*\n?', '', msg.content[0].text.strip()).strip()
        return json.loads(text)
    except Exception as e:
        print(f"    [WARN] 항목 추출 실패 ({carrier}): {e}")
        return []


def fetch_skt_monthly() -> dict:
    month = datetime.today().month
    print("    SKT T day 공식 페이지 크롤링...")
    raw = playwright_get_text("https://sktmembership.tworld.co.kr/mps/pc-bff/program/tday.do")
    items = extract_items_with_api("skt", raw, month) if raw else []
    print(f"    SKT 혜택 {len(items)}개 추출")
    return {
        "carrier": "skt",
        "title":   f"{month}월 T day + 0 week",
        "url":     "https://sktmembership.tworld.co.kr/mps/pc-bff/program/tday.do",
        "content": raw,
        "items":   items,
    }


def fetch_kt_monthly() -> dict:
    month = datetime.today().month
    print("    KT 달달혜택 로그인 후 크롤링...")
    raw = playwright_kt_login_and_get("https://membership.kt.com/discount/benefit/DaldalBenefit.do")
    if not raw:
        # 로그인 없이 접근 가능한 페이지 시도
        raw = playwright_get_text("https://app.membership.kt.com/eventpage/evn1044/daldal_web.html")
    items = extract_items_with_api("kt", raw, month) if raw else []
    print(f"    KT 혜택 {len(items)}개 추출")
    return {
        "carrier": "kt",
        "title":   f"{month}월 달달혜택",
        "url":     "https://membership.kt.com/discount/benefit/DaldalBenefit.do",
        "content": raw,
        "items":   items,
    }


def fetch_lgu_monthly() -> dict:
    month = datetime.today().month
    print("    LGU+ 유플투쁠 공식 페이지 크롤링...")
    raw = playwright_get_text("https://www.lguplus.com/benefit-plus")
    items = extract_items_with_api("lgu", raw, month) if raw else []
    print(f"    LGU+ 혜택 {len(items)}개 추출")
    return {
        "carrier": "lgu",
        "title":   f"{month}월 유플투쁠",
        "url":     "https://www.lguplus.com/benefit-plus",
        "content": raw,
        "items":   items,
    }


def fetch_monthly() -> dict:
    return {
        "skt": fetch_skt_monthly(),
        "kt":  fetch_kt_monthly(),
        "lgu": fetch_lgu_monthly(),
    }
