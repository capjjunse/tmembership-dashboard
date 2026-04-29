"""
collectors/news.py — 뉴스 크롤링, 날짜 YYYY-MM-DD 통일, 최신순 정렬
"""
import time
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from email.utils import parsedate
from config import REQUEST_HEADERS, REQUEST_DELAY, REQUEST_TIMEOUT
from config import NAVER_SEARCH_CLIENT_ID, NAVER_SEARCH_CLIENT_SECRET

CUTOFF = datetime.today() - timedelta(days=90)


def normalize_date(date_str: str) -> str:
    """다양한 날짜 형식 → YYYY-MM-DD"""
    if not date_str:
        return ""
    for fmt in ["%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"]:
        try:
            return datetime.strptime(date_str[:10], fmt).strftime("%Y-%m-%d")
        except:
            continue
    # RFC 2822: Thu, 16 Apr 2026 ...
    try:
        parsed = parsedate(date_str)
        if parsed:
            return datetime(*parsed[:6]).strftime("%Y-%m-%d")
    except:
        pass
    return date_str[:10]


def is_within_3months(date_str: str) -> bool:
    normalized = normalize_date(date_str)
    if not normalized:
        return True
    try:
        return datetime.strptime(normalized, "%Y-%m-%d") >= CUTOFF
    except:
        return True


def naver_news_search(query: str, display: int = 10) -> list:
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
        results = []
        for item in resp.json().get("items", []):
            pub_date = item.get("pubDate", "")
            if not is_within_3months(pub_date):
                continue
            title = BeautifulSoup(item.get("title", ""), "html.parser").get_text()
            desc  = BeautifulSoup(item.get("description", ""), "html.parser").get_text()
            results.append({
                "title":   title,
                "url":     item.get("link", ""),
                "date":    normalize_date(pub_date),  # ← YYYY-MM-DD 통일
                "summary": desc[:200],
            })
        time.sleep(REQUEST_DELAY)
        results.sort(key=lambda x: x["date"], reverse=True)
        return results
    except Exception as e:
        print(f"    [WARN] 네이버 뉴스 API ({query}): {e}")
        return []


def fetch_skt_news() -> list:
    results = []
    seen = set()
    cutoff = (datetime.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    for kw in ["T멤버십", "0week", "T day"]:
        try:
            url = (
                f"https://news.sktelecom.com/wp-json/wp/v2/posts"
                f"?search={requests.utils.quote(kw)}"
                f"&per_page=5&_fields=title,link,date,excerpt"
                f"&after={cutoff}T00:00:00"
            )
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            for post in resp.json():
                link = post.get("link", "")
                if link in seen:
                    continue
                post_date = normalize_date(post.get("date", "")[:10])
                if not is_within_3months(post_date):
                    continue
                seen.add(link)
                title   = BeautifulSoup(post.get("title", {}).get("rendered", ""), "html.parser").get_text()
                excerpt = BeautifulSoup(post.get("excerpt", {}).get("rendered", ""), "html.parser").get_text()
                results.append({
                    "carrier": "skt",
                    "title":   title,
                    "url":     link,
                    "date":    post_date,
                    "summary": excerpt[:200],
                })
            time.sleep(REQUEST_DELAY)
        except Exception as e:
            print(f"    [WARN] SKT 뉴스 ({kw}): {e}")
    results.sort(key=lambda x: x["date"], reverse=True)
    return results[:5]


def fetch_kt_news() -> list:
    items = naver_news_search("KT멤버십 달달혜택", display=10)
    return [{"carrier": "kt", **item} for item in items[:5]]


def fetch_lg_news() -> list:
    items = naver_news_search("유플러스 유플투쁠 멤버십", display=10)
    return [{"carrier": "lgu", **item} for item in items[:5]]


def fetch_all_news() -> dict:
    return {
        "skt": fetch_skt_news(),
        "kt":  fetch_kt_news(),
        "lgu": fetch_lg_news(),
    }
