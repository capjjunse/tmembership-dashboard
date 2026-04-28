"""
collectors/sentiment.py
고객 반응 수집 — 멀티 소스 + 최근 4주 필터 + 슬라이딩 키워드 윈도우
키워드 관리: 3개 유지, 새 동향 발견 시 가장 오래된 키워드 교체
"""
import json
import time
import re
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import quote
from pathlib import Path
from config import (
    REQUEST_HEADERS, REQUEST_DELAY, REQUEST_TIMEOUT,
    NAVER_SEARCH_CLIENT_ID, NAVER_SEARCH_CLIENT_SECRET,
    ANTHROPIC_API_KEY, CLAUDE_MODEL, DATA_DIR,
)

# 최근 4주 기준
CUTOFF_DATE = datetime.today() - timedelta(weeks=4)

# 키워드 히스토리 파일 (실행마다 유지)
KEYWORD_HISTORY_PATH = DATA_DIR / "keyword_history.json"


def is_within_4weeks(date_str: str) -> bool:
    if not date_str:
        return True
    for fmt in ["%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S"]:
        try:
            d = datetime.strptime(date_str[:10], fmt[:10])
            return d >= CUTOFF_DATE
        except:
            continue
    try:
        from email.utils import parsedate
        parsed = parsedate(date_str)
        if parsed:
            return datetime(*parsed[:6]) >= CUTOFF_DATE
    except:
        pass
    return True


# ── 키워드 히스토리 관리 ──────────────────────────────────

def load_keyword_history() -> dict:
    """저장된 키워드 히스토리 로드"""
    default = {
        "skt": [
            {"keyword": "T멤버십 혜택", "added_at": "2026.01.01"},
            {"keyword": "0week", "added_at": "2026.01.01"},
            {"keyword": "메가커피 T멤버십", "added_at": "2026.01.01"},
        ],
        "kt": [
            {"keyword": "KT멤버십 달달혜택", "added_at": "2026.01.01"},
            {"keyword": "KT 고객보답", "added_at": "2026.01.01"},
            {"keyword": "KT멤버십 혜택", "added_at": "2026.01.01"},
        ],
        "lgu": [
            {"keyword": "유플투쁠 혜택", "added_at": "2026.01.01"},
            {"keyword": "투쁠데이 후기", "added_at": "2026.01.01"},
            {"keyword": "유플러스 멤버십", "added_at": "2026.01.01"},
        ],
    }
    try:
        if KEYWORD_HISTORY_PATH.exists():
            return json.loads(KEYWORD_HISTORY_PATH.read_text(encoding="utf-8"))
    except:
        pass
    return default


def save_keyword_history(history: dict):
    """키워드 히스토리 저장"""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        KEYWORD_HISTORY_PATH.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"    [WARN] 키워드 히스토리 저장 실패: {e}")


def get_new_keywords(collected_at: str, existing_keywords: dict) -> dict:
    """
    Anthropic API로 신규 키워드 후보 생성
    기존 키워드와 다른 것만 반환
    """
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        existing_flat = {
            c: [k["keyword"] for k in kws]
            for c, kws in existing_keywords.items()
        }

        prompt = f"""T멤버십 대시보드 고객반응 수집용 신규 검색 키워드를 제안해줘.
기준일: {collected_at}

현재 사용 중인 키워드 (중복 제안 금지):
- SKT: {existing_flat['skt']}
- KT: {existing_flat['kt']}
- LGU+: {existing_flat['lgu']}

각 통신사별로 현재 키워드와 다른 신규 키워드를 1~2개 제안해줘.
기준: 최근 1개월 내 신설/변경된 혜택, 이슈가 된 프로모션, 고객 관심도가 높은 키워드.
예시: VIP찬스, 숲캉스데이, 파파존스 KT, 유플투쁠 2주년 등

JSON만 출력:
{{"skt": ["키워드1", "키워드2"],
  "kt":  ["키워드1", "키워드2"],
  "lgu": ["키워드1", "키워드2"]}}"""

        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        text = re.sub(r'```[^\n]*\n?', '', msg.content[0].text.strip()).strip()
        candidates = json.loads(text)
        print(f"    신규 키워드 후보 — SKT: {candidates['skt']} | KT: {candidates['kt']} | LGU: {candidates['lgu']}")
        return candidates
    except Exception as e:
        print(f"    [WARN] 신규 키워드 생성 실패: {e}")
        return {"skt": [], "kt": [], "lgu": []}


def update_keyword_window(history: dict, new_candidates: dict, new_results: dict) -> dict:
    """
    슬라이딩 윈도우 키워드 업데이트
    - 새 키워드로 수집된 동향이 있으면 → 가장 오래된 키워드 교체
    - 없으면 → 기존 유지
    """
    today = datetime.today().strftime("%Y.%m.%d")
    updated = {c: list(kws) for c, kws in history.items()}

    for carrier in ["skt", "kt", "lgu"]:
        candidates = new_candidates.get(carrier, [])
        for new_kw in candidates:
            # 이미 있는 키워드면 건너뜀
            existing_kws = [k["keyword"] for k in updated[carrier]]
            if new_kw in existing_kws:
                continue

            # 이 키워드로 수집된 결과가 있는지 확인
            kw_results = new_results.get(carrier, {}).get(new_kw, [])
            if not kw_results:
                print(f"    [{carrier.upper()}] '{new_kw}' — 수집 결과 없음, 유지")
                continue

            # 가장 오래된 키워드 제거 + 새 키워드 추가
            oldest = updated[carrier][0]["keyword"]
            updated[carrier].pop(0)
            updated[carrier].append({"keyword": new_kw, "added_at": today})
            print(f"    [{carrier.upper()}] 키워드 교체: '{oldest}' → '{new_kw}' (새 동향 {len(kw_results)}건)")
            break  # 한 번에 하나씩만 교체

    return updated


# ── 소스별 크롤러 ─────────────────────────────────────────

def naver_cafe_search(query: str, display: int = 5) -> list:
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
        results = []
        for item in resp.json().get("items", []):
            date = item.get("datetime", "")[:10]
            if not is_within_4weeks(date):
                continue
            title = BeautifulSoup(item.get("title", ""), "html.parser").get_text()
            desc  = BeautifulSoup(item.get("description", ""), "html.parser").get_text()
            cafe  = item.get("cafename", "")
            results.append({
                "source": f"네이버카페({cafe})" if cafe else "네이버카페",
                "title": title, "url": item.get("link", ""),
                "date": date, "text": desc[:300],
            })
        time.sleep(REQUEST_DELAY)
        return results
    except Exception as e:
        print(f"    [WARN] 네이버카페 ({query}): {e}")
        return []


def naver_web_search(query: str, site: str = "", display: int = 5) -> list:
    """네이버 웹 검색 API — 사이트 지정 가능"""
    try:
        q = f"site:{site} {query}" if site else query
        resp = requests.get(
            "https://openapi.naver.com/v1/search/webkr.json",
            headers={
                "X-Naver-Client-Id":     NAVER_SEARCH_CLIENT_ID,
                "X-Naver-Client-Secret": NAVER_SEARCH_CLIENT_SECRET,
            },
            params={"query": q, "display": display, "sort": "date"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        results = []
        for item in resp.json().get("items", []):
            title = BeautifulSoup(item.get("title", ""), "html.parser").get_text()
            desc  = BeautifulSoup(item.get("description", ""), "html.parser").get_text()
            results.append({
                "source": site.split(".")[0] if site else "웹",
                "title": title, "url": item.get("link", ""),
                "date": "", "text": desc[:300],
            })
        time.sleep(REQUEST_DELAY)
        return results
    except Exception as e:
        print(f"    [WARN] 웹 검색 ({query} @ {site}): {e}")
        return []


def fetch_ppomppu(keyword: str) -> list:
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
        for a in soup.select('a[href*="no="]')[:8]:
            title = a.get_text(strip=True)
            if len(title) < 5 or "광고" in title:
                continue
            href = a.get("href", "")
            if not href.startswith("http"):
                href = "https://www.ppomppu.co.kr" + href
            row = a.find_parent("tr")
            tds = row.select("td") if row else []
            date = tds[6].get_text(strip=True) if len(tds) > 6 else ""
            if not is_within_4weeks(date):
                continue
            results.append({"source": "뽐뿌", "title": title, "url": href, "date": date, "text": ""})
        time.sleep(REQUEST_DELAY)
        return results
    except Exception as e:
        print(f"    [WARN] 뽐뿌 ({keyword}): {e}")
        return []


def fetch_arca(keyword: str) -> list:
    try:
        url = f"https://arca.live/b/mobile?target=title&keyword={quote(keyword)}&sort=date"
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for item in soup.select("a.title")[:6]:
            title = item.get_text(strip=True)
            href = "https://arca.live" + item.get("href", "")
            row = item.find_parent("div") or item.find_parent("tr")
            date_el = row.select_one("time") if row else None
            date = date_el.get("datetime", "")[:10] if date_el else ""
            if not is_within_4weeks(date):
                continue
            results.append({"source": "아카라이브", "title": title, "url": href, "date": date, "text": ""})
        time.sleep(REQUEST_DELAY)
        return results
    except Exception as e:
        print(f"    [WARN] 아카라이브 ({keyword}): {e}")
        return []


def collect_by_keyword(keyword: str) -> list:
    """단일 키워드로 전 소스 수집"""
    results = []
    results += naver_cafe_search(keyword, display=4)
    results += fetch_ppomppu(keyword)
    results += naver_web_search(keyword, site="theqoo.net", display=3)
    results += fetch_arca(keyword)
    results += naver_web_search(keyword, site="dcinside.com", display=3)
    results += naver_web_search(keyword, site="damoang.net", display=3)
    results += naver_web_search(keyword, site="gaesbd.com", display=3)
    results += naver_cafe_search(f"아사모 {keyword}", display=3)
    return results


# ── 메인 수집 함수 ────────────────────────────────────────

def fetch_all_sentiment(collected_at: str = "") -> dict:
    output = {"skt": [], "kt": [], "lgu": []}

    # 1. 키워드 히스토리 로드
    history = load_keyword_history()
    current_keywords = {c: [k["keyword"] for k in kws] for c, kws in history.items()}
    print(f"    현재 키워드 — SKT: {current_keywords['skt']} | KT: {current_keywords['kt']} | LGU: {current_keywords['lgu']}")

    # 2. 신규 키워드 후보 생성 (API)
    new_candidates = get_new_keywords(collected_at, history)

    # 3. 기존 키워드 + 신규 후보 키워드로 수집
    all_results_by_kw = {"skt": {}, "kt": {}, "lgu": {}}

    carrier_map = {
        "skt": ["T멤버십", "T데이", "0week", "SKT"],
        "kt":  ["KT멤버십", "달달혜택", "KT"],
        "lgu": ["유플투쁠", "유플러스", "LG유플"],
    }

    for carrier in ["skt", "kt", "lgu"]:
        # 기존 키워드 수집
        for kw in current_keywords[carrier]:
            results = collect_by_keyword(kw)
            all_results_by_kw[carrier][kw] = results
            output[carrier] += results

        # 신규 후보 키워드 수집
        for kw in new_candidates.get(carrier, []):
            if kw not in current_keywords[carrier]:
                results = collect_by_keyword(kw)
                all_results_by_kw[carrier][kw] = results
                # 신규 키워드 결과는 output에는 포함 (슬라이딩 후 반영)
                output[carrier] += results

    # 4. 슬라이딩 윈도우 업데이트
    updated_history = update_keyword_window(history, new_candidates, all_results_by_kw)
    save_keyword_history(updated_history)

    # 5. 중복 제거 + 4주 필터 + 최대 10개
    for c in output:
        seen = set()
        unique = []
        for item in output[c]:
            url = item.get("url", "")
            if url and url not in seen:
                seen.add(url)
                if is_within_4weeks(item.get("date", "")):
                    unique.append(item)
        output[c] = unique[:10]

    return output
