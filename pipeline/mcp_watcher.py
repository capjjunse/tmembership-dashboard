#!/usr/bin/env python3
"""
mcp_watcher.py — MCP 브리지 감시자
auto_updater.py가 mcp_message.txt 파일을 생성하면
Claude in Chrome MCP를 통해 Claude.ai에 자동 전송하고 응답을 저장

실행: python3 mcp_watcher.py (파이프라인과 별도 터미널에서 실행)
"""
import time
import json
import subprocess
from pathlib import Path

BASE_DIR  = Path.home() / "Downloads" / "tmembership"
DATA_DIR  = BASE_DIR / "data"
MSG_FILE  = DATA_DIR / "mcp_message.txt"
RESP_FILE = DATA_DIR / "mcp_response.txt"
DONE_FILE = DATA_DIR / "mcp_done.flag"

CLAUDE_TAB_ID = 328826247  # 이 대화창 탭 ID


def send_to_claude_and_get_response(message: str) -> str:
    """Claude.ai 탭에 메시지 전송 후 응답 반환"""

    # 메시지를 Base64로 인코딩해서 특수문자 문제 완전 해결
    import base64
    msg_b64 = base64.b64encode(message.encode("utf-8")).decode("ascii")

    send_script = f"""
tell application "Google Chrome"
    tell active tab of front window
        execute javascript "
            (function() {{
                var b64 = '{msg_b64}';
                var msg = decodeURIComponent(escape(atob(b64)));
                var editor = document.querySelector('.ProseMirror');
                if (!editor) return 'no_editor';
                editor.focus();
                document.execCommand('selectAll', false, null);
                document.execCommand('delete', false, null);
                document.execCommand('insertText', false, msg);
                editor.dispatchEvent(new Event('input', {{bubbles: true}}));
                setTimeout(function() {{
                    var btn = document.querySelector('button[aria-label*=\\"메시지 보내기\\"]');
                    if (btn) btn.click();
                }}, 1000);
                return 'sent';
            }})();
        "
    end tell
end tell
"""
    r = subprocess.run(["osascript", "-e", send_script], capture_output=True, text=True)
    if r.returncode != 0 or "no_editor" in r.stdout:
        print(f"  전송 실패: {r.stderr.strip()}")
        return ""

    print("  전송 완료. 응답 대기 중...")

    # 응답 완료 대기 (최대 3분)
    for _ in range(90):
        time.sleep(2)
        check = subprocess.run(["osascript", "-e", """
tell application "Google Chrome"
    tell active tab of front window
        execute javascript "
            (function() {
                var btn = document.querySelector('button[aria-label*=\\"메시지 보내기\\"]');
                return (btn && !btn.disabled) ? 'done' : 'waiting';
            })();
        "
    end tell
end tell
"""], capture_output=True, text=True)
        if "done" in check.stdout:
            break

    time.sleep(1)

    # 응답 추출
    extract = subprocess.run(["osascript", "-e", """
tell application "Google Chrome"
    tell active tab of front window
        execute javascript "
            (function() {
                var msgs = document.querySelectorAll('[data-testid=\\"assistant-message\\"], .font-claude-message');
                if (!msgs.length) return '';
                return msgs[msgs.length - 1].innerText || '';
            })();
        "
    end tell
end tell
"""], capture_output=True, text=True)

    return extract.stdout.strip()


def watch():
    print("=" * 50)
    print("MCP 브리지 감시자 시작")
    print(f"감시 경로: {MSG_FILE}")
    print("Ctrl+C로 종료")
    print("=" * 50)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    while True:
        if MSG_FILE.exists():
            message = MSG_FILE.read_text(encoding="utf-8")
            MSG_FILE.unlink()  # 메시지 파일 삭제
            print(f"\n메시지 감지 ({len(message)}자). Claude.ai 전송 중...")

            response = send_to_claude_and_get_response(message)

            # 응답 저장
            RESP_FILE.write_text(response, encoding="utf-8")
            DONE_FILE.write_text("done", encoding="utf-8")
            print(f"응답 저장 완료 ({len(response)}자)")

        time.sleep(1)


if __name__ == "__main__":
    watch()
