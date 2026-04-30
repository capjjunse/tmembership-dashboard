"""
collectors/benefit.py — 상시 혜택 + 월별 혜택 수집
SKT: Playwright + 공식 페이지 본문만 크롤링
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


def playwright_get_main_content(url: str, content_selector: str = None, wait_sec: int = 5) -> str:
    """Playwright로 JS 렌더링 페이지에서 본문 텍스트만 추출"""
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

            if content_selector:
                try:
                    # 특정 영역만 추출
                    elements = page.query_selector_all(content_selector)
                    text = "\n".join([el.inner_text() for el in elements])
                except:
                    text = page.inner_text("body")
            else:
                # nav, header, footer 제거 후 본문만
                text = page.evaluate("""() => {
                    var remove = ['nav', 'header', 'footer', '.nav', '.header', '.footer',
                                  '.gnb', '.lnb', '.snb', '.share', '.sns'];
                    remove.forEach(function(sel) {
                        document.querySelectorAll(sel).forEach(function(el) { el.remove(); });
                    });
                    return document.body.innerText;
                }""")

            browser.close()
            return text[:5000] if text else ""
    except Exception as e:
        print(f"    [WARN] Playwright ({url}): {e}")
        return ""


def playwright_kt_login_and_get() -> str:
    """Playwright로 KT 로그인 후 달달혜택 페이지 크롤링"""
    kt_id = os.environ.get("KT_USERNAME", "")
    kt_pw = os.environ.get("KT_PASSWORD", "")
    if not kt_id or not kt_pw:
        print("    [WARN] KT_USERNAME/KT_PASSWORD 없음")
        return ""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
            )
            page = context.new_page()

            # KT 로그인 페이지
            target = "https://membership.kt.com/discount/benefit/DaldalBenefit.do"
            login_url = f"https://accounts.kt.com/wamui/AthWeb.do?urlcd={requests.utils.quote(target)}"
            try:
                page.goto(login_url, wait_until="domcontentloaded", timeout=20000)
            except:
                pass
            time.sleep(3)

            print(f"    KT 로그인 페이지: {page.url}")

            # 아이디/비밀번호 입력
            try:
                page.fill("input#id", kt_id)
                time.sleep(0.5)
                page.fill("input#password", kt_pw)
                time.sleep(0.5)
                # 로그인 버튼
                page.keyboard.press("Enter")
                time.sleep(4)
            except Exception as e:
                print(f"    [WARN] KT 입력 실패: {e}")

            print(f"    KT 로그인 후 URL: {page.url}")

            # 달달혜택 페이지 이동
            try:
                page.goto(target, wait_until="domcontentloaded", timeout=20000)
                time.sleep(4)
            except:
                pass

            print(f"    KT 달달혜택 URL: {page.url}")

            # 본문만 추출
            try:
                text = page.evaluate("""() => {
                    var remove = ['nav', 'header', 'footer', '.gnb', '.lnb'];
                    remove.forEach(function(sel) {
                        document.querySelectorAll(sel).forEach(function(el) { el.remove(); });
                    });
                    return document.body.innerText;
                }""")
            except:
                text = page.inner_text("body")

            browser.close()
            print(f"    KT 크롤링: {len(text)}자")
            return text[:5000]
    except Exception as e:
        print(f"    [WARN] KT 로그인 크롤링 실패: {e}")
        return ""


def extract_items_with_api(carrier: str, raw_text: str, month: int) -> list:
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
        prompt = f"""아래 텍스트에서 {carrier_names.get(carrier, carrier)} {month}월 실제 멤버십 혜택 항목만 추출해줘.

텍스트:
{raw_text[:3000]}

출력: JSON 배열만 (```없이)
["혜택1", "혜택2", ...]

규칙:
- 제휴처명 + 구체적 할인/혜택 내용만 (예: "쉐이크쉑 20% 할인", "뚜레쥬르 300원 적립")
- 네비게이션, 공유버튼, 법적고지 등 제외
- 최대 8개, 항목당 30자 이내
- 없으면 []"""

        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = re.sub(r'```[^\n]*\n?', '', msg.content[0].text.strip()).strip()
        result = json.loads(text)
        print(f"    {carrier.upper()} items: {result}")
        return result
    except Exception as e:
        print(f"    [WARN] {carrier} 추출 실패: {e}")
        return []


def fetch_skt_monthly() -> dict:
    month = datetime.today().month
    print("    SKT T day 크롤링...")
    # T day 혜택 목록 영역만 선택
    raw = playwright_get_main_content(
        "https://sktmembership.tworld.co.kr/mps/pc-bff/program/tday.do",
        wait_sec=5
    )
    print(f"    SKT content: {len(raw)}자")
    items = extract_items_with_api("skt", raw, month) if raw else []
    return {
        "carrier": "skt",
        "title": f"{month}월 T day + 0 week",
        "url": "https://sktmembership.tworld.co.kr/mps/pc-bff/program/tday.do",
        "content": raw,
        "items": items,
    }


def fetch_kt_monthly() -> dict:
    month = datetime.today().month
    print("    KT 달달혜택 크롤링...")
    raw = playwright_kt_login_and_get()
    items = extract_items_with_api("kt", raw, month) if raw else []
    return {
        "carrier": "kt",
        "title": f"{month}월 달달혜택",
        "url": "https://membership.kt.com/discount/benefit/DaldalBenefit.do",
        "content": raw,
        "items": items,
    }


def fetch_lgu_monthly() -> dict:
    month = datetime.today().month
    print("    LGU+ 유플투쁠 크롤링...")
    raw = playwright_get_main_content(
        "https://www.lguplus.com/benefit-plus",
        wait_sec=6
    )
    print(f"    LGU+ content: {len(raw)}자")
    items = extract_items_with_api("lgu", raw, month) if raw else []
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
