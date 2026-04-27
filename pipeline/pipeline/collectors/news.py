"""
collectors/news.py
뉴스 크롤링 — 갱신일 기준 최근 3개월 이내만 수집
"""
import time
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from config import REQUEST_HEADERS, REQUEST_DELAY, REQUEST_TIMEOUT
from config import NAVER_SEARCH_CLIENT_ID, NAVER_SEARCH_CLIENT_SECRET


def is_within_3months(date_str: str) -> bool:
    """날짜 문자열이 오늘 기준 최근 3개월 이내인지 확인"""
    if not date_str:
        return True  # 날짜 없으면 일단 포함
    cutoff = datetime.today() - timedelta(days=90)
    # 다양한 날짜 포맷 처리
    for fmt in ["%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"]:
        try:
            d = datetime.strptime(date_str[:10], fmt)
            return d >= cutoff
        except:
            continue
    # RFC 2822 포맷 (Mon, 20 Apr 2026 형식)
    try:
        from email.utils import parsedate
        parsed = parsedate(date_str)
        if parsed:
            d = datetime(*parsed[:6])
            return d >= cutoff
    except:
        pass
    return True  # 파싱 실패 시 포함


def naver_news_search(query: str, display: int = 10) -> list:
    """네이버 뉴스 검색 API — 최근 3개월 이내만 반환"""
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
        results = []
        for item in items:
            pub_date = item.get("pubDate", "")
            # 3개월 이내 필터링
            if not is_within_3months(pub_date):
                continue
            title = BeautifulSoup(item.get("title", ""), "html.parser").get_text()
            desc  = BeautifulSoup(item.get("description", ""), "html.parser").get_text()
            results.append({
                "title":   title,
                "url":     item.get("link", ""),
                "date":    pub_date[:16],
                "summary": desc[:200],
            })
        time.sleep(REQUEST_DELAY)
        return results
    except Exception as e:
        print(f"    [WARN] 네이버 뉴스 API ({query}): {e}")
        return []


def fetch_skt_news() -> list:
    """SKT 뉴스룸 — WordPress REST API, 3개월 이내만"""
    results = []
    seen = set()
    cutoff = (datetime.today() - timedelta(days=90)).strftime("%Y-%m-%d")

    for kw in ["T멤버십", "0week", "T day"]:
        try:
            # after 파라미터로 3개월 이내만 요청
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
                # 날짜 재확인
                post_date = post.get("date", "")[:10]
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
    return results[:5]


def fetch_kt_news() -> list:
    """KT 뉴스 — 네이버 검색 API, 3개월 이내만"""
    items = naver_news_search("KT멤버십 달달혜택", display=10)
    return [{"carrier": "kt", **item} for item in items[:5]]


def fetch_lg_news() -> list:
    """LGU+ 뉴스 — 네이버 검색 API, 3개월 이내만"""
    items = naver_news_search("유플러스 유플투쁠 멤버십", display=10)
    return [{"carrier": "lgu", **item} for item in items[:5]]


def fetch_all_news() -> dict:
    return {
        "skt": fetch_skt_news(),
        "kt":  fetch_kt_news(),
        "lgu": fetch_lg_news(),
    }
