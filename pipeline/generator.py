"""
generator.py — JSON 저장 방식 (index.html 절대 건드리지 않음)
수집 데이터를 collected_data.json에 저장하면
index.html의 JS가 자동으로 읽어서 화면 렌더링
"""
import json
import subprocess
from datetime import datetime
from config import DEPLOY_DIR

PAGES_URL = "https://capjjunse.github.io/tmembership-dashboard/"


def generate_dashboard(collected: dict) -> str:
    """
    HTML 교체 없음 — collected_data.json 저장이 전부.
    index.html의 loadDynamicData() JS가 자동으로 렌더링.
    """
    # collected_data.json을 레포 루트에 저장
    json_path = DEPLOY_DIR / "collected_data.json"
    DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(collected, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  ✅ collected_data.json 저장: {json_path} ({len(json.dumps(collected))/1024:.1f}KB)")

    # index.html은 건드리지 않음 — 그대로 반환
    html_path = DEPLOY_DIR / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"index.html 없음: {html_path}")


def save_and_deploy(html: str) -> str:
    """index.html은 건드리지 않고 collected_data.json만 커밋"""
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    json_path = DEPLOY_DIR / "collected_data.json"

    for cmd in [
        ["git", "-C", str(DEPLOY_DIR), "add", str(json_path)],
        ["git", "-C", str(DEPLOY_DIR), "commit", "-m", f"Data update {today}"],
        ["git", "-C", str(DEPLOY_DIR), "push"],
    ]:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 and "nothing to commit" not in r.stdout + r.stderr:
            raise RuntimeError(f"git 실패: {r.stderr}")

    print(f"  배포 완료 → {PAGES_URL}")
    return PAGES_URL
