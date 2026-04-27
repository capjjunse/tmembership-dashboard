"""
T멤버십 대시보드 자동화 파이프라인 설정
"""
import os
from pathlib import Path

# ── 디렉토리 경로 ──────────────────────────────────────────
BASE_DIR    = Path.home() / "Downloads" / "tmembership"
DATA_DIR    = BASE_DIR / "data"
DEPLOY_DIR  = BASE_DIR / "deploy"
LOG_DIR     = BASE_DIR / "logs"
SKILL_PATH  = BASE_DIR / "SKILL_membership_dashboard_v3.md"

# ── 네이버 DataLab API (검색어 트렌드) ────────────────────
DATALAB_CLIENT_ID     = "kWZuYiDh4bePpyvvJ1Fx"
DATALAB_CLIENT_SECRET = "We38EQBjzj"

# ── 네이버 검색 API (뉴스/카페 검색) ─────────────────────
NAVER_SEARCH_CLIENT_ID     = "msn4kD7_A7EmM1IX9mMs"
NAVER_SEARCH_CLIENT_SECRET = "df_9VRsw3X"

# ── Anthropic API ─────────────────────────────────────────
# 발급: https://console.anthropic.com/settings/keys
# 환경변수 또는 직접 입력
ANTHROPIC_API_KEY = "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"
CLAUDE_MODEL      = "claude-sonnet-4-5"  # 빠르고 저렴 / opus-4-5는 더 정교하지만 느림

# ── Netlify ───────────────────────────────────────────────
NETLIFY_SITE_ID = "profound-bienenstitch-f41a8a"

# ── 크롤링 공통 설정 ──────────────────────────────────────
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
REQUEST_DELAY   = 1.0
REQUEST_TIMEOUT = 12
