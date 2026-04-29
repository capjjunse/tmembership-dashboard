"""
collectors/benefit.py — 상시 혜택 + 월별 혜택 수집
월별혜택은 Anthropic API로 뉴스 기사를 항목별 리스트로 정리
"""
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


def naver_news_api(query: str, display: int = 5) -> str:
    """네이버 뉴스 API로 기사 텍스트 수집"""
    try:
        resp = requests.get(
            "https://openapi.naver.com/v1/search/news.json",
            headers={
                "X-Naver-Client-Id":     NAVER_SEARCH_CLIENT_ID,
                "X-Naver-Client-Secret": NAVER_SEARCH_CLIENT_SECRET,
            },
            params={"query": query, "display": display, "sort": "date"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        parts = []
        for item in resp.json().get("items", []):
            title = BeautifulSoup(item.get("title", ""), "html.parser").get_text()
            desc  = BeautifulSoup(item.get("description", ""), "html.parser").get_text()
            parts.append(f"{title}\n{desc}")
        time.sleep(REQUEST_DELAY)
        return "\n\n".join(parts)[:3000]
    except Exception as e:
        print(f"    [WARN] 네이버 뉴스 API ({query}): {e}")
        return ""


def summarize_monthly_benefits(carrier: str, raw_text: str, month: int) -> list:
    """
    Anthropic API로 뉴스 기사에서 월별 혜택 항목 추출
    Returns: ["혜택1", "혜택2", ...] 형태의 리스트
    """
    if not raw_text or not ANTHROPIC_API_KEY:
        return []
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        carrier_names = {"skt": "SKT T멤버십", "kt": "KT 달달혜택", "lgu": "LG유플러스 유플투쁠"}
        carrier_name = carrier_names.get(carrier, carrier)

        prompt = f"""아래 뉴스 기사에서 {carrier_name}의 {month}월 멤버십 혜택 항목만 추출해줘.

뉴스 내용:
{raw_text}

출력 형식: JSON 배열만 (```없이)
["혜택 항목1", "혜택 항목2", "혜택 항목3", ...]

규칙:
- 실제 혜택 항목만 (예: "뚜레쥬르 브라우니 선착순 30만명", "공차 50% 할인", "노브랜드버거 1+1")
- 최대 6개
- 항목당 20자 이내로 간결하게
- 혜택 정보가 없으면 빈 배열 []"""

        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        import json, re
        text = re.sub(r'```[^\n]*\n?', '', msg.content[0].text.strip()).strip()
        return json.loads(text)
    except Exception as e:
        print(f"    [WARN] 월별혜택 API 요약 실패 ({carrier}): {e}")
        return []


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


def fetch_skt_monthly() -> dict:
    month = datetime.today().month
    raw = naver_news_api(f"SKT T멤버십 T데이 {month}월 혜택 0week", display=5)
    if not raw:
        raw = naver_news_api(f"T멤버십 {month}월 혜택", display=5)
    items = summarize_monthly_benefits("skt", raw, month)
    return {
        "carrier": "skt",
        "title":   f"{month}월 T day + 0 week",
        "url":     "https://sktmembership.tworld.co.kr/mps/pc-bff/sktmembership/tday.do",
        "content": raw,
        "items":   items,  # API로 정리된 혜택 리스트
    }


def fetch_kt_monthly() -> dict:
    month = datetime.today().month
    raw = naver_news_api(f"KT {month}월 달달혜택 멤버십")
    items = summarize_monthly_benefits("kt", raw, month)
    return {
        "carrier": "kt",
        "title":   f"{month}월 달달혜택",
        "url":     "https://event.kt.com/html/event/ongoing_event_view.html?pcEvtNo=13783",
        "content": raw,
        "items":   items,
    }


def fetch_lgu_monthly() -> dict:
    month = datetime.today().month
    raw = naver_news_api(f"LG유플러스 유플투쁠 {month}월")
    items = summarize_monthly_benefits("lgu", raw, month)
    return {
        "carrier": "lgu",
        "title":   f"{month}월 유플투쁠",
        "url":     "https://www.lguplus.com/benefit/uplustobeul",
        "content": raw,
        "items":   items,
    }


def fetch_monthly() -> dict:
    return {
        "skt": fetch_skt_monthly(),
        "kt":  fetch_kt_monthly(),
        "lgu": fetch_lgu_monthly(),
    }
