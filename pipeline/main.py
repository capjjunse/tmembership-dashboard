#!/usr/bin/env python3
"""
main.py — T멤버십 대시보드 자동화 파이프라인
- 트렌드, 뉴스, 고객반응: GitHub Actions 자동 수집
- 월별혜택: MCP 담당 (기존 collected_data.json 값 유지)
"""
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_DIR, LOG_DIR, DEPLOY_DIR, ANTHROPIC_API_KEY, IS_GITHUB_ACTIONS
from collectors.trend     import fetch_trend
from collectors.news      import fetch_all_news
from collectors.sentiment import fetch_all_sentiment
from collectors.benefit   import fetch_all_namu

LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

JSON_PATH = DEPLOY_DIR / "collected_data.json"


def load_existing_data() -> dict:
    """기존 collected_data.json 로드 (월별혜택 등 MCP 담당 데이터 유지용)"""
    try:
        if JSON_PATH.exists():
            return json.loads(JSON_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning(f"기존 데이터 로드 실패: {e}")
    return {}


def run():
    log.info("=" * 60)
    log.info("T멤버십 대시보드 자동화 파이프라인 시작")
    log.info(f"실행 환경: {'GitHub Actions' if IS_GITHUB_ACTIONS else '로컬'}")
    log.info(f"실행 시각: {datetime.now().strftime('%Y.%m.%d %H:%M:%S')}")
    log.info("=" * 60)

    if not ANTHROPIC_API_KEY:
        log.error("ANTHROPIC_API_KEY 미설정!")
        sys.exit(1)

    # 기존 데이터 로드 (월별혜택 등 MCP 담당 섹션 유지)
    existing = load_existing_data()
    collected = {"collected_at": datetime.now().strftime("%Y.%m.%d %H:%M")}

    # ── STEP 1: API 담당 섹션 수집 ───────────────────────
    log.info("[1/2] 데이터 수집 (API 담당)")

    log.info("  ▸ 검색어 트렌드...")
    try:
        collected["trend"] = fetch_trend()
        log.info(f"    → {len(collected['trend']['labels'])}주 수집")
    except Exception as e:
        log.error(f"    실패: {e}")
        collected["trend"] = existing.get("trend", {"labels": [], "skt": [], "kt": [], "lgu": []})

    log.info("  ▸ 뉴스 스크랩...")
    try:
        collected["news"] = fetch_all_news()
        for c, items in collected["news"].items():
            log.info(f"    → {c.upper()}: {len(items)}건")
    except Exception as e:
        log.error(f"    실패: {e}")
        collected["news"] = existing.get("news", {"skt": [], "kt": [], "lgu": []})

    log.info("  ▸ 고객 반응...")
    try:
        collected["sentiment"] = fetch_all_sentiment(collected["collected_at"])
        for c, items in collected["sentiment"].items():
            log.info(f"    → {c.upper()}: {len(items)}건")
    except Exception as e:
        log.error(f"    실패: {e}")
        collected["sentiment"] = existing.get("sentiment", {"skt": [], "kt": [], "lgu": []})

    log.info("  ▸ 상시 혜택 (나무위키)...")
    try:
        collected["namu"] = fetch_all_namu()
        for c, d in collected["namu"].items():
            log.info(f"    → {c.upper()}: {len(d['text'])}자")
    except Exception as e:
        log.error(f"    실패: {e}")
        collected["namu"] = existing.get("namu", {c: {"carrier": c, "text": "", "url": ""} for c in ["skt","kt","lgu"]})

    # ── MCP 담당 섹션: 기존 값 유지 ─────────────────────
    log.info("  ▸ 월별혜택 — MCP 담당, 기존 값 유지")
    collected["monthly"] = existing.get("monthly", {"skt": {}, "kt": {}, "lgu": {}})

    # ── STEP 2: JSON 저장 ────────────────────────────────
    log.info("[2/2] collected_data.json 저장")
    try:
        from generator import generate_dashboard
        generate_dashboard(collected)
        log.info("  저장 완료")
    except Exception as e:
        log.error(f"  저장 실패: {e}", exc_info=True)
        sys.exit(1)

    log.info("=" * 60)
    log.info("파이프라인 완료")
    log.info("=" * 60)


if __name__ == "__main__":
    run()
