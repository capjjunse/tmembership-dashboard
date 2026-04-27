"""
collectors/sentiment.py
고객 반응 — 네이버 카페 검색 API + 뽐뿌 직접 크롤링
"""
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from config import REQUEST_HEADERS, REQUEST_DELAY, REQUEST_TIMEOUT
from config import NAVER_SEARCH_CLIENT_ID, NAVER_SEARCH_CLIENT_SECRET


def naver_cafe_search(query: str, display: int = 5) -> list:
    """네이버 카페 검색 API — 커뮤니티 반응"""
    try:
        resp = requests.get(
            "https://openapi.naver.com/v1/search/cafearticle.json",
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
            title = BeautifulSoup(item.get("title", ""), "html.parser").get_text()
            desc  = BeautifulSoup(item.get("description", ""), "html.parser").get_text()
            cafe  = item.get("cafename", "")
            results.append({
                "source": f"네이버카페({cafe})" if cafe else "네이버카페",
                "title":  title,
                "url":    item.get("link", ""),
                "date":   item.get("datetime", "")[:10],
                "text":   desc[:300],
            })
        time.sleep(REQUEST_DELAY)
        return results
    except Exception as e:
        print(f"    [WARN] 네이버 카페 검색 ({query}): {e}")
        return []


def fetch_ppomppu(keyword: str) -> list:
    """뽐뿌 — requests + EUC-KR"""
    try:
        keyword_enc = quote(keyword.encode("euc-kr"))
        url = (
            f"https://www.ppomppu.co.kr/zboard/zboard.php"
            f"?id=phone&keyword={keyword_enc}&sn=on&sc=on&so=on&ft=1"
        )
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.encoding = "euc-kr"
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for a in soup.select('a[href*="no="]')[:6]:
            title = a.get_text(strip=True)
            if len(title) < 5 or "광고" in title or "AD" in title:
                continue
            href = a.get("href", "")
            if not href.startswith("http"):
                href = "https://www.ppomppu.co.kr" + href
            row = a.find_parent("tr")
            tds = row.select("td") if row else []
            date = tds[6].get_text(strip=True) if len(tds) > 6 else ""
            results.append({
                "source": "뽐뿌",
                "title":  title,
                "url":    href,
                "date":   date,
                "text":   "",
            })
        time.sleep(REQUEST_DELAY)
        return results
    except Exception as e:
        print(f"    [WARN] 뽐뿌 ({keyword}): {e}")
        return []


def fetch_all_sentiment() -> dict:
    output = {"skt": [], "kt": [], "lgu": []}

    # 네이버 카페 검색
    queries = {
        "skt": ["T멤버십 혜택", "0week T멤버십"],
        "kt":  ["KT멤버십 달달혜택"],
        "lgu": ["유플투쁠 혜택"],
    }
    for carrier, kws in queries.items():
        for kw in kws:
            output[carrier] += naver_cafe_search(kw, display=4)

    # 뽐뿌 직접 크롤링
    for kw in ["T멤버십", "KT멤버십", "유플투쁠"]:
        items = fetch_ppomppu(kw)
        for item in items:
            t = item["title"]
            if any(k in t for k in ["T멤버십", "T데이", "0week"]):
                output["skt"].append(item)
            elif any(k in t for k in ["KT", "달달"]):
                output["kt"].append(item)
            elif any(k in t for k in ["유플", "LG"]):
                output["lgu"].append(item)

    # 중복 제거 + 최대 8개
    for c in output:
        seen = set()
        unique = []
        for item in output[c]:
            if item["url"] not in seen:
                seen.add(item["url"])
                unique.append(item)
        output[c] = unique[:8]

    return output
