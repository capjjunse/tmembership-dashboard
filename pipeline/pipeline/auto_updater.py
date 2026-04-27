#!/usr/bin/env python3
"""
auto_updater.py — 섹션별 조각 생성 방식 완전 자동화
AppleScript를 직접 호출 (subprocess 권한 문제 해결)
"""
import json
import time
import subprocess
import re
import base64
from pathlib import Path
from datetime import datetime

BASE_DIR   = Path.home() / "Downloads" / "tmembership"
DATA_DIR   = BASE_DIR / "data"
DEPLOY_DIR = BASE_DIR / "deploy"
HTML_PATH  = DEPLOY_DIR / "index.html"
CLAUDE_CHAT_URL = "https://claude.ai/chat/c49d48b6-6b27-4a5c-8e9c-129d900648cb"


def send_and_get_response(message: str, wait_sec: int = 120) -> str:
    """
    AppleScript로 Claude.ai에 메시지 전송 후 응답 반환
    Base64 인코딩으로 특수문자 문제 완전 해결
    """
    # Base64 인코딩으로 특수문자 이스케이프
    msg_b64 = base64.b64encode(message.encode("utf-8")).decode("ascii")

    send_script = f"""tell application "Google Chrome"
    tell active tab of front window
        execute javascript "
            (function() {{
                try {{
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
                }} catch(e) {{
                    return 'error: ' + e.message;
                }}
            }})();
        "
    end tell
end tell"""

    result = subprocess.run(["osascript", "-e", send_script], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"전송 실패: {result.stderr.strip()}")
    if "no_editor" in result.stdout:
        raise RuntimeError("입력창 없음")
    if "error:" in result.stdout:
        raise RuntimeError(f"JS 오류: {result.stdout.strip()}")

    print(f"  전송 완료. 응답 대기 중 (최대 {wait_sec}초)...")

    # 응답 완료 대기 (전송 버튼 재활성화 감지)
    for _ in range(wait_sec // 2):
        time.sleep(2)
        check = subprocess.run(["osascript", "-e", """tell application "Google Chrome"
    tell active tab of front window
        execute javascript "(function(){ var btn = document.querySelector('button[aria-label*=\\"메시지 보내기\\"]'); return (btn && !btn.disabled) ? 'done' : 'waiting'; })();"
    end tell
end tell"""], capture_output=True, text=True)
        if "done" in check.stdout:
            break

    time.sleep(1)

    # 마지막 응답 추출
    extract = subprocess.run(["osascript", "-e", """tell application "Google Chrome"
    tell active tab of front window
        execute javascript "(function(){ var msgs = document.querySelectorAll('[data-testid=\\"assistant-message\\"], .font-claude-message'); if(!msgs.length) return ''; return msgs[msgs.length-1].innerText || ''; })();"
    end tell
end tell"""], capture_output=True, text=True)

    return extract.stdout.strip()


def replace_js_data(html: str, key: str, new_data: list) -> str:
    pattern = rf'const {key}\s*=\s*\[.*?\];'
    replacement = f'const {key} = {json.dumps(new_data)};'
    return re.sub(pattern, replacement, html, flags=re.DOTALL)


def update_trend(html: str, data: dict) -> str:
    t = data.get("trend", {})
    if not t.get("labels"):
        print("  ⚠️ 트렌드 데이터 없음 — 건너뜀")
        return html
    html = replace_js_data(html, "labels", t.get("labels", []))
    html = replace_js_data(html, "skt",    t.get("skt", []))
    html = replace_js_data(html, "kt",     t.get("kt", []))
    html = replace_js_data(html, "lgu",    t.get("lgu", []))
    skt = t.get("skt", [0]); kt = t.get("kt", [0]); lgu = t.get("lgu", [0])
    y_max = int(max(max(skt), max(kt), max(lgu)) * 1.1) + 1
    html = re.sub(r'const yMax\s*=\s*[^;]+;', f'const yMax = {y_max};', html)
    collected_at = data.get("collected_at", "")
    html = re.sub(
        r'출처: 네이버 DataLab API · [\d\.\s:]+수집',
        f'출처: 네이버 DataLab API · {collected_at} 수집',
        html
    )
    print("  ✅ 트렌드 완료")
    return html


def update_news(html: str, data: dict) -> str:
    news = data.get("news", {})
    if not any(news.values()):
        print("  ⚠️ 뉴스 없음 — 건너뜀")
        return html

    msg = (
        f"[자동화] 수집일: {data['collected_at']}\n"
        f"뉴스 데이터:\n{json.dumps(news, ensure_ascii=False)}\n\n"
        "위 데이터로 뉴스 섹션 HTML 조각만 생성해줘.\n"
        "형식: <div id=\"np-skt\">...</div><div id=\"np-kt\" class=\"hidden\">...</div><div id=\"np-lgu\" class=\"hidden\">...</div>\n"
        "각 카드: <div class=\"nc\"><div class=\"nct\"><span class=\"nb nb신규\">신규</span><span class=\"ntitle\">제목</span></div><div class=\"nsum\">요약</div><div class=\"nmeta\">날짜 · 출처</div></div>\n"
        "배지: nb신규/nb변경/nb종료/nb이슈. HTML만, 설명 없이."
    )

    try:
        response = send_and_get_response(msg, wait_sec=90)
        if response and "<div" in response:
            for sid in ["np-skt", "np-kt", "np-lgu"]:
                m = re.search(rf'(<div\s+id="{sid}"[^>]*>)(.*?)(</div>)', response, re.DOTALL)
                if m:
                    html = re.sub(rf'<div\s+id="{sid}"[^>]*>.*?</div>',
                                  m.group(), html, count=1, flags=re.DOTALL)
            print("  ✅ 뉴스 완료")
        else:
            print("  ⚠️ 응답 없음 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ 뉴스 실패: {e} — 기존 유지")
    return html


def update_sentiment(html: str, data: dict) -> str:
    sentiment = data.get("sentiment", {})
    if not any(sentiment.values()):
        print("  ⚠️ 고객반응 없음 — 건너뜀")
        return html

    msg = (
        f"[자동화] 수집일: {data['collected_at']}, 최근 3개월, 긍정→부정→중립 순서.\n"
        f"고객반응 데이터:\n{json.dumps(sentiment, ensure_ascii=False)}\n\n"
        "위 데이터로 고객반응 섹션 HTML 조각만 생성해줘.\n"
        "형식: <div id=\"sent-skt\">...</div><div id=\"sent-kt\" class=\"hidden\">...</div><div id=\"sent-lgu\" class=\"hidden\">...</div>\n"
        "각 통신사 내부: .srcs 출처배지 + .tr2 키워드탭 + .rc 반응카드 (.rbg rpos/rneg/rneu). HTML만, 설명 없이."
    )

    try:
        response = send_and_get_response(msg, wait_sec=120)
        if response and "<div" in response:
            for sid in ["sent-skt", "sent-kt", "sent-lgu"]:
                m = re.search(rf'(<div\s+id="{sid}"[^>]*>)(.*?)(</div>)', response, re.DOTALL)
                if m:
                    html = re.sub(rf'<div\s+id="{sid}"[^>]*>.*?</div>',
                                  m.group(), html, count=1, flags=re.DOTALL)
            print("  ✅ 고객반응 완료")
        else:
            print("  ⚠️ 응답 없음 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ 고객반응 실패: {e} — 기존 유지")
    return html


def update_monthly(html: str, data: dict) -> str:
    monthly = data.get("monthly", {})
    if not any(v.get("content") for v in monthly.values()):
        print("  ⚠️ 월별혜택 없음 — 건너뜀")
        return html

    msg = (
        f"[자동화] 수집일: {data['collected_at']}\n"
        f"월별혜택 데이터:\n{json.dumps(monthly, ensure_ascii=False)}\n\n"
        "위 데이터로 월별혜택 섹션 HTML 조각만 생성해줘.\n"
        "형식: <div class=\"m3\"><div class=\"mc\"><div class=\"mch ms\">SKT...</div><div class=\"mcb\">...</div></div>"
        "<div class=\"mc\"><div class=\"mch mk\">KT...</div><div class=\"mcb\">...</div></div>"
        "<div class=\"mc\"><div class=\"mch ml\">LGU+...</div><div class=\"mcb\">...</div></div></div>\n"
        "HTML만, 설명 없이."
    )

    try:
        response = send_and_get_response(msg, wait_sec=90)
        if response and 'class="m3"' in response:
            m = re.search(r'<div\s+class="m3">.*?</div>\s*</div>\s*</div>', response, re.DOTALL)
            if m:
                html = re.sub(r'<div\s+class="m3">.*?</div>\s*</div>\s*</div>',
                              m.group(), html, count=1, flags=re.DOTALL)
            print("  ✅ 월별혜택 완료")
        else:
            print("  ⚠️ 응답 없음 — 기존 유지")
    except Exception as e:
        print(f"  ⚠️ 월별혜택 실패: {e} — 기존 유지")
    return html


def update_date(html: str, collected_at: str) -> str:
    date_str = collected_at.split(" ")[0]
    html = re.sub(r'\d{4}\.\d{2}\.\d{2} 기준', f'{date_str} 기준', html)
    print(f"  ✅ 기준일: {date_str}")
    return html


def deploy(html: str) -> str:
    HTML_PATH.write_text(html, encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    for cmd in [
        ["git", "-C", str(DEPLOY_DIR), "add", "index.html"],
        ["git", "-C", str(DEPLOY_DIR), "commit", "-m", f"Auto update {today}"],
        ["git", "-C", str(DEPLOY_DIR), "push"],
    ]:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 and "nothing to commit" not in r.stdout + r.stderr:
            raise RuntimeError(f"git 실패: {r.stderr}")
    url = "https://profound-bienenstitch-f41a8a.netlify.app/"
    print(f"  ✅ 배포 완료 → {url}")
    return url


def open_claude_tab():
    """Claude.ai 대화창 열기"""
    script = f"""tell application "Google Chrome"
    activate
    open location "{CLAUDE_CHAT_URL}"
end tell"""
    subprocess.run(["osascript", "-e", script])
    print("  Claude.ai 탭 열림, 6초 대기...")
    time.sleep(6)


def main():
    print("=" * 55)
    print("T멤버십 대시보드 섹션별 자동 업데이트 시작")
    print("=" * 55)

    data = json.loads((DATA_DIR / "collected_data.json").read_text(encoding="utf-8"))
    html = HTML_PATH.read_text(encoding="utf-8")
    print(f"수집 데이터: {data['collected_at']} | HTML: {len(html):,}자")

    # Claude.ai 탭 열기
    open_claude_tab()

    print("\n[1/4] 검색 트렌드...")
    html = update_trend(html, data)

    print("\n[2/4] 뉴스 스크랩...")
    html = update_news(html, data)

    print("\n[3/4] 고객 반응...")
    html = update_sentiment(html, data)

    print("\n[4/4] 월별 혜택...")
    html = update_monthly(html, data)

    html = update_date(html, data["collected_at"])

    print("\n[배포] git push → Netlify...")
    url = deploy(html)

    print(f"\n{'='*55}")
    print(f"✅ 완료! {url}")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
