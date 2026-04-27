"""
collectors/trend.py
네이버 DataLab API → 검색어 트렌드 수집
(update_trend.py 통합 버전)
"""
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from config import DATALAB_CLIENT_ID, DATALAB_CLIENT_SECRET, REQUEST_TIMEOUT, BASE_DIR


def fetch_trend() -> dict:
    """최근 90일 주간 검색 트렌드 수집"""
    end   = datetime.today()
    start = end - timedelta(days=90)

    body = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate":   end.strftime("%Y-%m-%d"),
        "timeUnit":  "week",
        "keywordGroups": [
            {
                "groupName": "SKT",
                "keywords": [
                    "T멤버십", "T 멤버십", "t멤버십",
                    "T데이", "T day", "티데이",
                    "0week", "0위크",
                    "VIP pick"
                ]
            },
            {
                "groupName": "KT",
                "keywords": [
                    "KT멤버십", "KT 멤버십", "kt멤버십",
                    "달달혜택", "KT 달달혜택",
                    "VIP 초이스"
                ]
            },
            {
                "groupName": "LGU+",
                "keywords": [
                    "U+멤버십", "유플러스 멤버십",
                    "유플투쁠", "유플 투쁠",
                    "VIP 콕"
                ]
            }
        ],
    }

    resp = requests.post(
        "https://openapi.naver.com/v1/datalab/search",
        headers={
            "X-Naver-Client-Id":     DATALAB_CLIENT_ID,
            "X-Naver-Client-Secret": DATALAB_CLIENT_SECRET,
            "Content-Type":          "application/json",
        },
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if len(results) < 3:
        raise ValueError(f"DataLab 응답 이상: {results}")

    def fmt(date_str):
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{d.month}/{d.day:02d}"

    labels = [fmt(p["period"]) for p in results[0]["data"]]
    skt    = [round(p["ratio"], 1) for p in results[0]["data"]]
    kt     = [round(p["ratio"], 1) for p in results[1]["data"]]
    lgu    = [round(p["ratio"], 1) for p in results[2]["data"]]

    trend_data = {
        "collected_at": datetime.now().strftime("%Y.%m.%d %H:%M"),
        "period": {
            "start": results[0]["data"][0]["period"],
            "end":   results[0]["data"][-1]["period"],
        },
        "labels": labels,
        "skt":    skt,
        "kt":     kt,
        "lgu":    lgu,
    }

    # trend_data.json도 별도 저장 (기존 update_trend.py 호환)
    trend_path = BASE_DIR / "trend_data.json"
    trend_path.write_text(
        json.dumps(trend_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return trend_data
