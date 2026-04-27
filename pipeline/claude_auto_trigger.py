"""
claude_auto_trigger.py
AppleScript로 이미 열려있는 Chrome에서 Claude.ai 대화창을 열고
"대시보드 갱신해줘." 메시지를 자동 입력 + 전송
"""

import time
import subprocess
import json
from pathlib import Path

# ★ 이 대화창 URL (절대 변경 금지)
CLAUDE_CHAT_URL = "https://claude.ai/chat/c49d48b6-6b27-4a5c-8e9c-129d900648cb"

BASE_DIR = Path.home() / "Downloads" / "tmembership"
MESSAGE = "대시보드 갱신해줘."


def send_via_applescript():
    """AppleScript — 새 탭으로 열기 + 메시지 전송"""

    # 1단계: 새 탭으로 열기
    open_script = f'''
tell application "Google Chrome"
    activate
    open location "{CLAUDE_CHAT_URL}"
end tell
'''
    result = subprocess.run(["osascript", "-e", open_script], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"탭 열기 실패: {result.stderr.strip()}")

    print("  Claude.ai 탭 열림, 로딩 대기 중 (6초)...")
    time.sleep(6)

    # 2단계: 메시지 입력 + 전송
    send_script = '''
tell application "Google Chrome"
    tell active tab of front window
        execute javascript "
            (function() {
                var editor = document.querySelector('.ProseMirror');
                if (!editor) return 'no_editor';
                editor.focus();
                document.execCommand('selectAll', false, null);
                document.execCommand('delete', false, null);
                document.execCommand('insertText', false, '대시보드 갱신해줘.');
                editor.dispatchEvent(new Event('input', {bubbles: true}));
                setTimeout(function() {
                    var btn = document.querySelector('button[aria-label*=\\"메시지 보내기\\"]');
                    if (btn) btn.click();
                }, 1000);
                return 'sent';
            })();
        "
    end tell
end tell
'''
    result = subprocess.run(["osascript", "-e", send_script], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"메시지 전송 실패: {result.stderr.strip()}")

    output = result.stdout.strip()
    if "no_editor" in output:
        raise RuntimeError("입력창 없음 — 아직 로딩 중")

    print("  ✅ 메시지 전송 완료!")
    return True


def trigger_claude():
    """메인 트리거"""
    print("=" * 50)
    print("Claude.ai 자동 트리거 시작")
    print(f"대화창: {CLAUDE_CHAT_URL}")
    print("=" * 50)

    data_path = BASE_DIR / "data" / "collected_data.json"
    if not data_path.exists():
        raise FileNotFoundError(f"수집 데이터 없음: {data_path}")

    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"  수집 데이터 확인: {data.get('collected_at', '알 수 없음')}")

    for attempt, extra_wait in enumerate([0, 4, 8], 1):
        try:
            if extra_wait:
                print(f"  {extra_wait}초 추가 대기...")
                time.sleep(extra_wait)
            print(f"  시도 {attempt}/3...")
            send_via_applescript()
            return
        except RuntimeError as e:
            print(f"  실패: {e}")

    print(f"\n  ⚠️ 자동 입력 실패. 직접 입력해주세요: {CLAUDE_CHAT_URL}")
    subprocess.run(["open", CLAUDE_CHAT_URL])


if __name__ == "__main__":
    trigger_claude()
