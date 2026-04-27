#!/usr/bin/env python3
"""
main.py — T멤버십 대시보드 완전 자동화 파이프라인
매주 월요일 09:30 launchd로 실행

흐름:
  1. 데이터 수집 (크롤링 + DataLab API)
  2. Anthropic API → HTML 스트리밍 생성 (계속버튼 없음, MCP 불필요)
  3. deploy/index.html 저장 → git push → Netlify 자동 배포
"""
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import BASE_DIR, DATA_DIR, LOG_DIR, ANTHROPIC_API_KEY
from collectors.trend     import fetch_trend
from collectors.news      import fetch_all_news
from collectors.sentiment import fetch_all_sentiment
from collectors.benefit   import fetch_all_namu, fetch_monthly

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


def run():
    log.info("=" * 60)
    log.info("T멤버십 대시보드 자동화 파이프라인 시작")
    log.info(f"실행 시각: {datetime.now().strftime('%Y.%m.%d %H:%M:%S')}")
    log.info("=" * 60)

    # API 키 확인
    if not ANTHROPIC_API_KEY:
        log.error("ANTHROPIC_API_KEY 미설정! config.py에 API 키를 입력하세요.")
        sys.exit(1)

    collected = {"collected_at": datetime.now().strftime("%Y.%m.%d %H:%M")}

    # ── STEP 1: 데이터 수집 ──────────────────────────────
    log.info("[1/3] 데이터 수집")

    log.info("  ▸ 검색어 트렌드...")
    try:
        collected["trend"] = fetch_trend()
        log.info(f"    → {len(collected['trend']['labels'])}주 수집")
    except Exception as e:
        log.error(f"    실패: {e}")
        collected["trend"] = {"labels": [], "skt": [], "kt": [], "lgu": []}

    log.info("  ▸ 뉴스 스크랩...")
    try:
        collected["news"] = fetch_all_news()
        for c, items in collected["news"].items():
            log.info(f"    → {c.upper()}: {len(items)}건")
    except Exception as e:
        log.error(f"    실패: {e}")
        collected["news"] = {"skt": [], "kt": [], "lgu": []}

    log.info("  ▸ 고객 반응...")
    try:
        collected["sentiment"] = fetch_all_sentiment()
        for c, items in collected["sentiment"].items():
            log.info(f"    → {c.upper()}: {len(items)}건")
    except Exception as e:
        log.error(f"    실패: {e}")
        collected["sentiment"] = {"skt": [], "kt": [], "lgu": []}

    log.info("  ▸ 상시 혜택 (나무위키)...")
    try:
        collected["namu"] = fetch_all_namu()
        for c, d in collected["namu"].items():
            log.info(f"    → {c.upper()}: {len(d['text'])}자")
    except Exception as e:
        log.error(f"    실패: {e}")
        collected["namu"] = {c: {"carrier": c, "text": "", "url": ""} for c in ["skt","kt","lgu"]}

    log.info("  ▸ 월별 혜택...")
    try:
        collected["monthly"] = fetch_monthly()
        log.info("    → 수집 완료")
    except Exception as e:
        log.error(f"    실패: {e}")
        collected["monthly"] = {"skt": {}, "kt": {}, "lgu": {}}

    data_path = DATA_DIR / "collected_data.json"
    data_path.write_text(json.dumps(collected, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"  수집 데이터 저장: {data_path}")

    # ── STEP 2: Anthropic API → HTML 생성 ──────────────
    log.info("[2/3] Anthropic API로 HTML 생성")
    try:
        from generator import generate_dashboard
        html = generate_dashboard(collected)
        log.info(f"  HTML 생성 완료 ({len(html):,}자)")
    except Exception as e:
        log.error(f"  HTML 생성 실패: {e}", exc_info=True)
        sys.exit(1)

    # ── STEP 3: 저장 + git push + Netlify 배포 ─────────
    log.info("[3/3] 저장 및 배포")
    try:
        from generator import save_and_deploy
        url = save_and_deploy(html)
        log.info(f"  배포 완료: {url}")
        print(f"\n✅ 완료! 대시보드: {url}\n")
    except Exception as e:
        log.error(f"  배포 실패: {e}", exc_info=True)
        sys.exit(1)

    log.info("=" * 60)
    log.info("파이프라인 완료")
    log.info("=" * 60)


if __name__ == "__main__":
    run()
