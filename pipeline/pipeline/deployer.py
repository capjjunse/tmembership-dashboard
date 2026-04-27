"""
deployer.py
생성된 HTML → git push → Netlify 자동 배포
"""
import subprocess
from datetime import datetime
from pathlib import Path
from config import DEPLOY_DIR

# Netlify 사이트 URL (확인용)
NETLIFY_URL = "https://profound-bienenstitch-f41a8a.netlify.app/"


def deploy_to_netlify(html: str) -> str:
    """HTML을 deploy 폴더에 저장 후 git push → Netlify 자동 배포"""

    # HTML 저장
    DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
    html_path = DEPLOY_DIR / "index.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  HTML 저장 완료: {html_path}")

    # git add + commit + push
    today = datetime.now().strftime("%Y-%m-%d %H:%M")

    cmds = [
        ["git", "-C", str(DEPLOY_DIR), "add", "index.html"],
        ["git", "-C", str(DEPLOY_DIR), "commit", "-m", f"Auto update {today}"],
        ["git", "-C", str(DEPLOY_DIR), "push"],
    ]

    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # "nothing to commit"은 정상 — 무시
            if "nothing to commit" in result.stdout + result.stderr:
                print("  변경사항 없음 (이미 최신)")
                return NETLIFY_URL
            raise RuntimeError(
                f"git 명령 실패: {' '.join(cmd)}\n"
                f"stderr: {result.stderr}"
            )

    print(f"  git push 완료 → Netlify 자동 배포 시작")
    print(f"  배포 URL: {NETLIFY_URL}")
    return NETLIFY_URL
