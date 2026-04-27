---
name: membership-dashboard
description: "T멤버십팀 준호를 위한 통신 3사(SKT·KT·LGU+) 멤버십 경쟁사 모니터링 HTML 대시보드 생성·수정 스킬. '멤버십 대시보드', '통신사 멤버십 비교', '경쟁사 모니터링 대시보드', '대시보드 업데이트', '대시보드 갱신', '대시보드 갱신해줘' 요청 시 이 스킬을 사용할 것."
---

# 통신 3사 멤버십 대시보드 스킬 v3 (최종 완전판)

> **새 채팅 시작 시**: Filesystem MCP로 `/Users/1113755/Downloads/tmembership/SKILL_membership_dashboard_v3.md` 읽기 → 컨텍스트 로드 후 작업 시작

---

## 자동화 파이프라인 연동

### 이 대화창 정보
- **대화 URL**: `https://claude.ai/chat/bffa0705-84a8-4d17-ac1d-c81b57bb886d`
- 매주 월요일 9:30 Python 스크립트가 이 대화창으로 접속해서 "대시보드 갱신해줘" 자동 입력

### 갱신 요청 수신 시 동작 순서
1. `Filesystem:read_text_file('/Users/1113755/Downloads/tmembership/data/collected_data.json')` 읽기
2. 수집 데이터 기반으로 대시보드 HTML 생성
3. **HTML을 두 곳에 동시 저장**:
   - `/mnt/user-data/outputs/membership_dashboard.html` → `present_files` (채팅창 표시)
   - `/Users/1113755/Downloads/tmembership/deploy/index.html` → Filesystem MCP 저장 (Netlify 배포용)
4. 저장 완료 메시지: `✅ HTML 저장 완료: /Users/1113755/Downloads/tmembership/deploy/index.html`

---

## 기본 정보

| 항목 | 값 |
|---|---|
| 최신 HTML | `/mnt/user-data/outputs/membership_dashboard.html` (v13) |
| 로컬 경로 | `/Users/1113755/Downloads/tmembership/` |
| 렌더링 방식 | HTML 파일 → `present_files` (**show_widget 사용 금지**) |
| Filesystem MCP 허용 경로 | `/Users/1113755/Downloads/tmembership` |
| Chart.js CDN | `https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js` |

---

## 헤더 구조

```html
<div class="hdr">
  <div class="hdr-l">
    <div class="htag">Copyright by T 멤버십팀</div>
    <h1>통신 3사 멤버십 현황 대시보드</h1>
    <div class="hdr-meta"><span class="hdr-dot"></span><span id="lastUpdated">기준일</span></div>
  </div>
</div>
```

- **"Copyright by T 멤버십팀"** 태그라인 필수
- **AI 업데이트 버튼 없음** (완전 제거됨)
- 헤더 그라디언트: `linear-gradient(135deg,#120d32 0%,#1e1260 30%,#3617ce 65%,#5533ee 100%)`

---

## CSS 토큰 (전체)

```css
:root{
  --p:#4422e0;--pl:#ece8ff;--pd:#1a1240;--pm:#6644ff;
  --skt:#5B0F8A;--skt-bg:#f3edff;--skt-t:#3d0a5c;--skt-bd:#c8a0f0;
  --kt:#c41a1a;--kt-bg:#fff1f1;--kt-t:#8a1010;--kt-bd:#f5aaaa;
  --lgu:#b5006a;--lgu-bg:#fff0f8;--lgu-t:#7a0047;--lgu-bd:#f5aad8;
  --bg:#ffffff;--bg2:#fafafa;--bg3:#f3f2fa;--bg4:#ede9ff;
  --tx:#18182a;--tx2:#52527a;--tx3:#9494b8;
  --bd:#e8e6f4;--bd2:#d0ccee;
  --pos:#15803d;--pos-bg:#dcfce7;--pos-bd:#86efac;
  --neg:#dc2626;--neg-bg:#fee2e2;--neg-bd:#fca5a5;
  --neu:#64748b;--neu-bg:#f1f5f9;
  --warn:#d97706;--warn-bg:#fef3c7;
  --r:10px;--rl:16px;--rxl:22px;
  --sh:0 1px 3px rgba(68,34,224,.06),0 4px 16px rgba(68,34,224,.06);
  --sh-hover:0 2px 6px rgba(68,34,224,.1),0 8px 28px rgba(68,34,224,.1);
}
body{background:#eceaf5;}
.page{max-width:1160px;margin:0 auto;padding:22px 16px 64px;}
```

---

## 11개 섹션 구조 + 업데이트 주기 배지

| 섹션 | id | 배지 | 텍스트 |
|---|---|---|---|
| 개요 | `ov` | `upd-1m` | ↻ 월 갱신 |
| 상시 혜택 | `rg` | `upd-chg` | ⚡ 변경 시 업데이트 |
| 월별 혜택 | `mo` | `upd-chg` | ⚡ 변경 시 업데이트 |
| VIP 특화 | `vp` | `upd-chg` | ⚡ 변경 시 업데이트 |
| 변경 이력 | `hs` | `upd-1m` | ↻ 월 갱신 (주요 변경 즉시) |
| 뉴스 스크랩 | `nw` | `upd-3m` | ↻ 주 단위 갱신 |
| 고객 반응 | `sn` | `upd-3m` | ↻ 주 단위 갱신 |
| 검색 트렌드 | `tr` | `upd-3m` | ↻ 주 단위 갱신 |
| 비통신 멤버십 | `nt` | `upd-1m` | ↻ 월 갱신 |
| 제휴 제안 | `pr` | `upd-1m` | ↻ 월 갱신 |
| AI 인사이트 | `ai` | `upd-1m` | ↻ 월 갱신 |

```css
.upd-badge{display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px;margin-left:auto;flex-shrink:0;}
.upd-3m{background:#dbeafe;color:#1d4ed8;}
.upd-1m{background:#d1fae5;color:#065f46;}
.upd-chg{background:var(--warn-bg);color:var(--warn);}
.sh{display:flex;align-items:baseline;gap:8px;margin-bottom:1.1rem;padding-bottom:.75rem;border-bottom:1px solid var(--bd);justify-content:space-between;flex-wrap:wrap;}
.st{font-size:15px;font-weight:800;color:var(--tx);}
.ss{font-size:11px;color:var(--tx3);font-weight:400;}
```

---

## 개요 섹션 데이터 (2026.04 기준)

### 핵심 동향 카드 4개

```html
<div class="og">
  <div class="oc cs"><div class="ol"><span class="cb bs">SKT</span></div>
    <div class="ov">0 week 신설</div>
    <div class="od">0 day → 0 week 개편 2026.04.01<br>만 13~34세, 매월 첫째 주 5일</div></div>
  <div class="oc ck"><div class="ol"><span class="cb bk">KT</span></div>
    <div class="ov">고객보답 프로그램</div>
    <div class="od">2026 한시 운영<br>데이터 100GB + OTT 6개월</div></div>
  <div class="oc cl"><div class="ol"><span class="cb bl">LGU+</span></div>
    <div class="ov">배민클럽 2개월 무료</div>
    <div class="od">통신사 최초 2026.01~<br>유플투쁠 투쁠데이 경유</div></div>
  <div class="oc cg"><div class="ol" style="font-size:11px;color:var(--tx3)">주요 변경</div>
    <div class="ov" style="font-size:13px">롯데시네마 제휴 종료</div>
    <div class="od"><span class="cb bs">SKT</span> 2026.02.01 종료<br>KT만 3사 중 유지</div></div>
</div>
```

### 트렌드 리스트
- **SKT**: 0 week 4월 — 뚜레쥬르 브라우니 30만명 · 공차 50% · 노브랜드버거 1+1 · 요기요 8,000원↓
- **KT**: 달달혜택 3월 — 롯데리아 51% or 빽다방 2잔 무료 택1 · 고객보답프로그램 2026 한시
- **LGU+**: 장기고객데이 4월 화담숲 초청 4/13 · 투쁠데이 배민클럽 2개월 무료 지속

---

## 네비게이션 (sticky + 스크롤 감지)

```css
.nav-wrap{position:sticky;top:0;z-index:100;padding:8px 0 0;margin-bottom:10px;}
.nav a.on{background:var(--p);color:#fff;font-weight:700;}
```

---

## JS 전체 코드 (누락 금지)

```javascript
const secIds=['ov','rg','mo','vp','hs','nw','sn','tr','nt','pr','ai'];
function setActiveNav(id){document.querySelectorAll('.nav a').forEach(a=>{a.classList.toggle('on',a.dataset.sec===id)});}
function onScroll(){const scrollY=window.scrollY+80;let current=secIds[0];secIds.forEach(id=>{const el=document.getElementById(id);if(el&&el.offsetTop<=scrollY)current=id;});setActiveNav(current);}
window.addEventListener('scroll',onScroll,{passive:true});
onScroll();
function go(id){document.getElementById(id)?.scrollIntoView({behavior:'smooth'});setTimeout(()=>setActiveNav(id),400);}
function switchNews(c,el){['skt','kt','lgu'].forEach(x=>{document.getElementById('np-'+x).classList.add('hidden');document.getElementById('ntab-'+x).className='ntab'});document.getElementById('np-'+c).classList.remove('hidden');el.className='ntab '+{skt:'as',kt:'ak',lgu:'al'}[c];}
function C(c,el){['skt','kt','lgu'].forEach(x=>document.getElementById('sent-'+x).classList.add('hidden'));document.querySelectorAll('.ctab').forEach(b=>b.className='ctab');el.className='ctab '+{skt:'cs',kt:'ck',lgu:'cl'}[c];document.getElementById('sent-'+c).classList.remove('hidden');}
function K(c,kw,el){const p=c+'-';document.querySelectorAll('[id^="'+p+'"]').forEach(d=>d.classList.add('hidden'));document.getElementById(p+kw)?.classList.remove('hidden');el.closest('.tr2').querySelectorAll('.kw').forEach(b=>b.classList.remove('on'));el.classList.add('on');}
function todayStr(){const d=new Date();return d.getFullYear()+'.'+(d.getMonth()+1).toString().padStart(2,'0')+'.'+d.getDate().toString().padStart(2,'0');}
document.getElementById('lastUpdated').textContent=todayStr()+' 기준';

window.addEventListener('load',()=>{
  const ctx=document.getElementById('trendChart')?.getContext('2d');
  if(!ctx)return;
  const labels=['1/12','1/19','1/26','2/02','2/09','2/16','2/23','3/02','3/09','3/16','3/23','3/30','4/06','4/13'];
  const skt=[2.4,2.1,2.7,2.5,2.4,2.3,2.8,3.0,2.5,2.3,2.0,2.6,2.4,1.4];
  const kt=[4.8,3.4,6.7,14.6,11.9,9.5,10.4,8.2,6.8,7.9,6.2,7.7,4.6,4.3];
  const lgu=[76.8,71.6,3.5,40.9,53.6,20.1,1.6,1.3,22.1,100,47.1,28.6,32.2,11.4];
  const yMax=Math.ceil(Math.max(...skt,...kt,...lgu)*1.1);
  new Chart(ctx,{type:'line',data:{labels,datasets:[
    {label:'SKT (T멤버십 외)',data:skt,borderColor:'#5B0F8A',backgroundColor:'rgba(91,15,138,.08)',tension:.4,pointRadius:4,pointHoverRadius:6,pointBackgroundColor:'#5B0F8A',borderWidth:2.5,fill:true},
    {label:'KT (KT멤버십 외)',data:kt,borderColor:'#c41a1a',backgroundColor:'rgba(196,26,26,.07)',tension:.4,pointRadius:4,pointHoverRadius:6,pointBackgroundColor:'#c41a1a',borderWidth:2.5,fill:true},
    {label:'LGU+ (U+멤버십 외)',data:lgu,borderColor:'#b5006a',backgroundColor:'rgba(181,0,106,.1)',tension:.4,pointRadius:4,pointHoverRadius:6,pointBackgroundColor:'#b5006a',borderWidth:2.5,fill:true},
  ]},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
    plugins:{legend:{display:false},tooltip:{backgroundColor:'rgba(26,18,64,.92)',titleColor:'#fff',bodyColor:'rgba(255,255,255,.8)',padding:10,
      callbacks:{title:items=>'2026년 '+items[0].label+' 주간',label:item=>'  '+item.dataset.label+': '+item.parsed.y}}},
    scales:{y:{min:0,max:yMax,grid:{color:'rgba(0,0,0,.04)'},ticks:{font:{size:11},color:'#aaa'},title:{display:true,text:'검색량 지수 (100 = 기간 내 최고값)',font:{size:10},color:'#bbb'}},
      x:{grid:{display:false},ticks:{font:{size:11},color:'#aaa'}}}}});
});
```

---

## 테이블 디자인

```css
table.ct{table-layout:fixed;width:100%;}
table.ct th.th-skt{background:var(--skt-bg);color:var(--skt-t);}
table.ct th.th-kt{background:var(--kt-bg);color:var(--kt-t);}
table.ct th.th-lgu{background:var(--lgu-bg);color:var(--lgu-t);}
.m3{display:grid;grid-template-columns:repeat(3,1fr);border:1px solid var(--bd);border-radius:var(--rl);overflow:hidden;}
.mch.ms{background:var(--skt-bg);color:var(--skt-t);}
.mch.mk{background:var(--kt-bg);color:var(--kt-t);}
.mch.ml{background:var(--lgu-bg);color:var(--lgu-t);}
```

---

## 상시 혜택 주요 데이터 (2026.04 기준)

### 영화관
| 제휴처 | SKT | KT | LGU+ |
|---|---|---|---|
| CGV | 전 고객 최대 4,000원↓ (11→1천/12→2천/13→3천/14↑→4천원), 최대 5매 | 전 등급 최대 5,000원↓ (본인+동반3인, 월3회) | 기본 없음 · 영화콕(VIP↑) **연3회** |
| 메가박스 | 전 고객 최대 4,000원↓, 최대 5매 | 전 등급 최대 5,000원↓ | 기본 없음 |
| 롯데시네마 | **2026.02.01 종료** | 전 등급 최대 5,000원↓ / VVIP 초이스 2인 무료 | 기본 없음 |

### 베이커리
| 제휴처 | SKT | KT | LGU+ |
|---|---|---|---|
| 파리바게뜨 | VIP/Gold: 100원 · Silver: 50원 | VVIP/VIP/골드: 100원 · 일반: 50원 | VIP↑: **10%** · 이외: **5%** |
| 뚜레쥬르 | VIP/Gold: 150원 · Silver: 50원 | VVIP/VIP/골드: 150원 · 일반: 100원 | **전 등급 100원** |

### 패밀리레스토랑
| 제휴처 | SKT | KT | LGU+ |
|---|---|---|---|
| 아웃백 | VIP/Gold: 15% · Silver: 5% | VVIP/VIP/골드: 15% · 화이트/일반: 5% | 상시 없음 |
| VIPS | VIP/Gold: 15% · Silver: 5% | VVIP/VIP/골드: 15% | **VVIP/VIP: 10%** · 우수: 5% |

### 피자 ⚠️ LGU+ 상시 (유플투쁠 경유 아님)
| 제휴처 | SKT | KT | LGU+ |
|---|---|---|---|
| 도미노 | VIP: 30% · Gold/Silver: 20% | VVIP/VIP: 20% · 일반: 15% | **VIP↑: 20% · 이외: 15% 상시** |
| 피자헛 | VIP: 30% · Gold/Silver: 20% | 전 등급: 15% | **VIP↑: 20% · 이외: 15% 상시** |

### 카페·디저트
| 제휴처 | SKT | KT | LGU+ |
|---|---|---|---|
| 배스킨라빈스 | VIP/Gold: **1,000원당 100원** · Silver: 50원 | 상시 없음 | 전 등급: 쿼터 4,000원↓ |
| 스타벅스 | 상시 없음 | **전 등급 월1회 사이즈업 (3사 유일)** | 상시 없음 |

### 편의점
| 제휴처 | SKT | KT | LGU+ |
|---|---|---|---|
| GS25 | 전 등급: 매주 화요일 프레시푸드 200원 | VVIP/VIP/골드: 100원 · 실버/일반: 50원 | VIP↑: 100원 · 이외: 50원 (매일) |
| CU | VIP/Gold: 100원 · Silver: 50원 | 오전5~9시 간편식 200원 | 기본 없음 |
| 세븐일레븐 | VIP/Gold: 100원 · Silver: 50원 | 없음 | 없음 |

---

## VIP 특화 혜택

### SKT VIP Pick (월 1회 PICK + 별도 PLUS)
- CGV: 무료관람 연3회 / 1+1 연9회 (택1)
- T우주패스: 9,900원 쿠폰 연3회 / 4,900원 쿠폰 연9회
- PLUS(횟수 미차감): CGV 특별관 연12회, JAJU, TMAP 렌터카 등

### KT VIP·VVIP 초이스 (2026)
- VIP: 연 최대 6회 / VVIP: 연 최대 12회
- VVIP 전용: VIPS 스테이크 무료, 도미노 3만원↓, 노보텔 조식 2인 무료
- 생일혜택: VVIP(꾸까·스벅케이크·롯시 택1) · VIP(던킨·할리스·롯시1+1 택1)

### LGU+ VIP콕 (월 1회, 연 12회, 분기별 택1)
- 영화콕: CGV 월1회 무료, **연3회** ← 연12회 아님
- 라이프콕: 할리스 아메리카노 무료 등 ~30종
- 구독콕: 네이버 플러스 멤버십 1개월 무료 등

---

## 월별 혜택 (2026.04 기준)

### SKT
- **T day**: 배달의민족×처갓집양념치킨, 다운타우너, 그리팅, 아떼, 매드포갈릭
- **0 week** (2026.04.01 신설): 만 13~34세, 매월 첫째 주 5일 (화 이후 시작 시 둘째 주)
  - 4월: 뚜레쥬르 브라우니 30만명, 공차 50%, 노브랜드버거 1+1, 요기요 8,000원↓
- **VIP 찬스**: T day 기간 VIP 추가 할인
- **VIP only 해피아워**: 파리바게뜨 오후 8시~자정 1만원↑ 4,000원↓

### KT
- **달달초이스** (택1): 매월 15일~말일 / 3월: 롯데리아 51% or 빽다방 2잔 무료
- **달달스페셜** (중복): 쉐이크쉑, 팀홀튼, 폴바셋, 파리바게뜨 등
- **고객보답** (2026 한시): 데이터 100GB + OTT 6개월 + 보험 2년 + 로밍 50%
- **포인트 한도 폐지**: 2025.05.08~

### LGU+
- **투쁠데이**: 매월 특정일 오전 11시 선착순 — 배민클럽 2개월 무료, 공차 50%, CGV세트 무료
- **장기고객데이**: 4주차 목요일, 5년↑ VIP — 화담숲·뮤지컬·전시 등
- **유독 구독**: VVIP/VIP, 넷플릭스·유튜브·디즈니+·티빙 등 4,000원↓

---

## 공식 링크

| | URL |
|---|---|
| SKT T day+0week | https://sktmembership.tworld.co.kr/mps/pc-bff/sktmembership/tday.do |
| KT 달달혜택 | https://event.kt.com/html/event/ongoing_event_view.html?page=1&searchCtg=ALL&sort=&pcEvtNo=13783 |
| LGU+ 유플투쁠 | https://www.lguplus.com/benefit/uplustobeul |
| SKT VIP Pick | https://sktmembership.tworld.co.kr/mps/pc-bff/program/vippick.do |
| KT 초이스 | https://membership.kt.com/mmbr/choice.do |
| LGU+ VIP콕 | https://www.lguplus.com/benefit/membership/vip |

---

## 고객 반응 섹션

### 핵심 원칙
1. **최근 3개월**만 (2026.01.17~04.17)
2. **멤버십 혜택** 관련만 (앱 오류·보안 사태 제외)
3. **0week와 T day 구분** — 0week = 2026.04.01 신설, 첫째 주 5일, 4/15 = T day (0week 아님)
4. 긍정→부정→중립 순서 / 없는 키워드 탭 제거

### 커뮤니티 현황
에펨코리아·루리웹·뽐뿌·SKT뉴스룸·LG뉴스룸 ✅ / 더쿠·인스티즈 ❌(글없음) / 삼공스·디미토리 ❌(차단)

### 검증된 실제 댓글 (재사용 가능)

**SKT #VIP 혜택** (에펨코리아 2026.01.03):
- 긍정: "우주패스 무료 3회, CGV 무료 3회는 쓸만함" (추천2)
- 부정: "우주패스 유튜브 프리미엄 말곤 쓰는 것도 없음" (추천2)
- 부정(뽐뿌): "kt→sk 이동했는데 뭐 쓸게없어요. 위약금 65만"
- 중립: "몇 년째 VIP인데 쓰는 적이 거의 없음"

**SKT #0week·0day** (SKT뉴스룸 2026.04.01):
- 긍정: 뚜레쥬르 30만명, 공차 50%, T day 통합으로 편의성 개선 호평
- 중립: 0day 고객감사제 재개 여부 문의

**KT #고객보답** (루리웹 2026.02.01, 댓글63개):
- 긍정: "디즈니가 낫습니다." (추천22)
- 중립: "티빙은 720p라 별로, 디즈니플러스는 1080p" (추천17)

**KT #달달혜택** (에펨코리아 2026.03.30):
- 부정: "갈 일 없는 두 개네" (추천1) / "ㄹㅇ 노맛임" (추천1)

**LGU+ #배민클럽** (루리웹 2026.01.17, 댓글35개):
- 부정: "혜택이 없다시피 한 거 같던데." (추천35)

**LGU+ #유플투쁠 인기** (우먼타임스 2025.10.12):
- 긍정: 누적 참여 1,500만 돌파. 1위 CGV, 2위 컴포즈, 3위 다이소

---

## 검색어 트렌드 — 네이버 DataLab 자동화

### 플로우
매주 월요일 9:30 → launchd → pipeline/main.py → 크롤링 → collected_data.json → claude_auto_trigger.py → 이 대화창에 "대시보드 갱신해줘" 자동 입력 → HTML 생성 → deploy/index.html 저장 → Netlify 배포

### DataLab 토큰 (Claude 메모리 저장됨)
- client_id: `kWZuYiDh4bePpyvvJ1Fx` / client_secret: `We38EQBjzj`
- 키워드: SKT(T멤버십+T데이+0day+T멤버십혜택) / KT(KT멤버십+달달혜택+KT고객보답) / LGU+(U+멤버십+유플투쁠+유플러스멤버십)

### trend_data.json 구조
```json
{"collected_at":"YYYY.MM.DD HH:MM","period":{"start":"YYYY-MM-DD","end":"YYYY-MM-DD"},
 "labels":["M/DD",...],"skt":[...],"kt":[...],"lgu":[...]}
```

### 갱신 시 Claude 절차
1. `Filesystem:read_text_file('/Users/1113755/Downloads/tmembership/data/collected_data.json')`
2. labels/skt/kt/lgu/collected_at 추출
3. yMax = `Math.ceil(Math.max(...skt,...kt,...lgu)*1.1)`
4. 출처 표기: `출처: 네이버 DataLab API · {collected_at} 수집`
5. HTML 생성 후 **두 곳에 저장**:
   - `present_files('/mnt/user-data/outputs/membership_dashboard.html')`
   - `Filesystem:write_file('/Users/1113755/Downloads/tmembership/deploy/index.html', html)`

### 실제 수집 데이터 (2026.04.17 기준)
```
labels: ['1/12','1/19','1/26','2/02','2/09','2/16','2/23','3/02','3/09','3/16','3/23','3/30','4/06','4/13']
skt:  [2.4,2.1,2.7,2.5,2.4,2.3,2.8,3.0,2.5,2.3,2.0,2.6,2.4,1.4]
kt:   [4.8,3.4,6.7,14.6,11.9,9.5,10.4,8.2,6.8,7.9,6.2,7.7,4.6,4.3]
lgu:  [76.8,71.6,3.5,40.9,53.6,20.1,1.6,1.3,22.1,100,47.1,28.6,32.2,11.4]
```

---

## 작업 원칙 (필수 13가지)

1. **파일 출력**: `/mnt/user-data/outputs/membership_dashboard.html` → `present_files`  
   **+ 동시에** Filesystem MCP로 `/Users/1113755/Downloads/tmembership/deploy/index.html` 저장
2. show_widget 사용 금지
3. table-layout:fixed 필수
4. 통신사 컬러 헤더: .th-skt .th-kt .th-lgu
5. 스티키 네비게이션 + 스크롤 감지 JS
6. Chart.js CDN: `https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js`
7. 0week: 신설 2026.04.01, 첫째 주 5일, 화 이후 시작 시 둘째 주, 4/15=T day
8. 고객 반응: 최근 3개월, 혜택 관련만, 긍정→부정→중립
9. 검색 트렌드: collected_data.json 읽어서 실제 데이터 반영
10. LGU+ 피자: 상시 (유플투쁠 경유 아님)
11. LGU+ 영화콕: 연3회
12. 헤더: "Copyright by T 멤버십팀" / 업데이트 버튼 없음
13. 업데이트 배지: 각 섹션 .sh 우측에 배치

---

## 오류 수정 이력 (16건)

LGU+ 영화콕 연12회→**연3회** / LGU+ 파리바게뜨→**10%/5% 할인** / LGU+ 뚜레쥬르→**전 등급 100원** / LGU+ GS25→**전 등급 차등** / LGU+ 피자→**상시** / LGU+ VIPS→**10%/5%** / SKT 배스킨→**1,000원당100원** / 트렌드 키워드→**U+멤버십** / 트렌드→**네이버DataLab** / AI버튼→**제거** / 헤더→**Copyright** / 네비→**스크롤감지** / 테이블→**통신사컬러** / 고객반응→**3개월/주갱신** / 0week→**첫째주만** / 변경이력버튼→**제거**

---

*최종 업데이트: 2026.04.20 · v3 Final Complete · 작성자: Claude (T멤버십팀 준호 요청)*
