"""
config.py — T멤버십 대시보드 자동화 파이프라인 설정
로컬 실행 / GitHub Actions 모두 지원
"""
import os
from pathlib import Path

# ── 실행 환경 감지 ────────────────────────────────────────
# GitHub Actions에서는 GITHUB_ACTIONS=true 환경변수가 자동 설정됨
IS_GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"

if IS_GITHUB_ACTIONS:
    # GitHub Actions: 레포 루트 기준
    BASE_DIR   = Path(os.environ.get("GITHUB_WORKSPACE", "/github/workspace"))
    DEPLOY_DIR = BASE_DIR / "deploy"
    DATA_DIR   = BASE_DIR / "data"
    LOG_DIR    = BASE_DIR / "logs"
    SKILL_PATH = BASE_DIR / "SKILL_membership_dashboard_v3.md"
else:
    # 로컬 실행
    BASE_DIR   = Path.home() / "Downloads" / "tmembership"
    DEPLOY_DIR = BASE_DIR / "deploy"
    DATA_DIR   = BASE_DIR / "data"
    LOG_DIR    = BASE_DIR / "logs"
    SKILL_PATH = BASE_DIR / "SKILL_membership_dashboard_v3.md"

# ── API 키 (환경변수 우선, 없으면 직접 입력값) ────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "여기에_로컬용_키_입력")

DATALAB_CLIENT_ID     = os.environ.get("DATALAB_CLIENT_ID",     "kWZuYiDh4bePpyvvJ1Fx")
DATALAB_CLIENT_SECRET = os.environ.get("DATALAB_CLIENT_SECRET", "We38EQBjzj")

NAVER_SEARCH_CLIENT_ID     = os.environ.get("NAVER_SEARCH_CLIENT_ID",     "msn4kD7_A7EmM1IX9mMs")
NAVER_SEARCH_CLIENT_SECRET = os.environ.get("NAVER_SEARCH_CLIENT_SECRET", "df_9VRsw3X")

# ── Claude 모델 ───────────────────────────────────────────
CLAUDE_MODEL = "claude-sonnet-4-5"

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
}
REQUEST_DELAY   = 1.0
REQUEST_TIMEOUT = 12
