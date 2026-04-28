#!/usr/bin/env python3
"""
main.py — T멤버십 대시보드 완전 자동화 파이프라인
로컬(launchd) / GitHub Actions 모두 지원
"""
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import BASE_DIR, DATA_DIR, LOG_DIR, DEPLOY_DIR, ANTHROPIC_API_KEY, IS_GITHUB_ACTIONS
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
    log.info(f"실행 환경: {'GitHub Actions' if IS_GITHUB_ACTIONS else '로컬'}")
    log.info(f"실행 시각: {datetime.now().strftime('%Y.%m.%d %H:%M:%S')}")
    log.info("=" * 60)

    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "여기에_로컬용_키_입력":
        log.error("ANTHROPIC_API_KEY 미설정!")
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
        # collected_at 전달 → API가 이달 핵심 동향 기반으로 키워드 자동 확장
        collected["sentiment"] = fetch_all_sentiment(collected["collected_at"])
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
    log.info("  수집 데이터 저장 완료")

    # ── STEP 2: HTML 생성 ────────────────────────────────
    log.info("[2/3] Anthropic API로 HTML 생성")
    try:
        from generator import generate_dashboard
        html = generate_dashboard(collected)
        log.info(f"  HTML 생성 완료 ({len(html):,}자)")
    except Exception as e:
        log.error(f"  HTML 생성 실패: {e}", exc_info=True)
        sys.exit(1)

    # ── STEP 3: 저장 ─────────────────────────────────────
    log.info("[3/3] HTML 저장")
    try:
        DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
        html_path = DEPLOY_DIR / "index.html"
        html_path.write_text(html, encoding="utf-8")
        log.info(f"  저장 완료: {html_path} ({len(html):,}자)")

        if not IS_GITHUB_ACTIONS:
            from generator import save_and_deploy
            url = save_and_deploy(html)
            log.info(f"  배포 완료: {url}")
            print(f"\n✅ 완료! 대시보드: {url}\n")
        else:
            log.info("  GitHub Actions가 git push를 담당합니다.")
            print(f"\n✅ HTML 생성 완료! GitHub Actions가 배포합니다.\n")

    except Exception as e:
        log.error(f"  저장 실패: {e}", exc_info=True)
        sys.exit(1)

    log.info("=" * 60)
    log.info("파이프라인 완료")
    log.info("=" * 60)


if __name__ == "__main__":
    run()
