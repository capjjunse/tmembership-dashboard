"""
collectors/benefit.py
상시 혜택 + 월별 혜택 수집
"""
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from config import REQUEST_HEADERS, REQUEST_DELAY, REQUEST_TIMEOUT
from config import NAVER_SEARCH_CLIENT_ID, NAVER_SEARCH_CLIENT_SECRET

NAMU_URLS = {
    "skt": "https://namu.wiki/w/T%20Membership",
    "kt":  "https://namu.wiki/w/KT%20%EB%A9%A4%EB%B2%84%EC%8B%AD",
    "lgu": "https://namu.wiki/w/U%2B%EB%A9%A4%EB%B2%84%EC%8B%AD",
}


def naver_news_api(query: str, display: int = 5) -> str:
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
        items = resp.json().get("items", [])
        parts = []
        for item in items:
            title = BeautifulSoup(item.get("title", ""), "html.parser").get_text()
            desc  = BeautifulSoup(item.get("description", ""), "html.parser").get_text()
            parts.append(f"{title}\n{desc}")
        time.sleep(REQUEST_DELAY)
        return "\n\n".join(parts)[:3000]
    except Exception as e:
        print(f"    [WARN] 네이버 뉴스 API ({query}): {e}")
        return ""


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
    """SKT 월별 혜택 — 네이버 뉴스 API로 수집"""
    month = datetime.today().month
    content = naver_news_api(f"SKT T멤버십 T데이 {month}월 혜택", display=5)
    if not content:
        content = naver_news_api("T멤버십 0week T day 혜택", display=5)
    return {
        "carrier": "skt",
        "title":   f"{month}월 T day + 0 week",
        "url":     "https://sktmembership.tworld.co.kr/mps/pc-bff/sktmembership/tday.do",
        "content": content,
    }


def fetch_kt_monthly() -> dict:
    month = datetime.today().month
    content = naver_news_api(f"KT {month}월 달달혜택 멤버십")
    return {
        "carrier": "kt",
        "title":   f"{month}월 달달혜택",
        "url":     "https://event.kt.com/html/event/ongoing_event_view.html?pcEvtNo=13783",
        "content": content,
    }


def fetch_lgu_monthly() -> dict:
    month = datetime.today().month
    content = naver_news_api(f"LG유플러스 유플투쁠 {month}월")
    return {
        "carrier": "lgu",
        "title":   f"{month}월 유플투쁠",
        "url":     "https://www.lguplus.com/benefit/uplustobeul",
        "content": content,
    }


def fetch_monthly() -> dict:
    return {
        "skt": fetch_skt_monthly(),
        "kt":  fetch_kt_monthly(),
        "lgu": fetch_lgu_monthly(),
    }
