# 업스트림 변경 이력 (한국어)

업스트림([derbruedi/ff14-accessibility](https://github.com/derbruedi/ff14-accessibility))은 **독일어로 개발된다.** 커밋 메시지도 릴리스 노트도 독일어라, 우리 저장소에 뭐가 들어왔는지 그대로는 읽을 수 없다. 여기에 한국어로 옮겨 둔다.

- **자리는 도구가 만들고, 번역은 사람이 채운다.** `--notes`가 원문과 함께 `(미번역)` 자리를 만들고, 그게 남아 있는 동안은 검사가 통과하지 않는다.
- **원문을 지우지 않는다.** 옮긴 것이 틀렸을 때 되짚을 자리가 그것뿐이다.
- **모르는 게임 용어는 지어내지 않는다.** 한국어판 표기를 확인하지 못한 것은 원문을 괄호로 병기하고 `용어 미확인`이라고 적는다. 근거 없는 표기를 한 번 박아 두면 그게 기준이 된다(2026-08-18 `Aetheryte` 건).
- 역순이다. 위가 최신.

핀 이전(v5.84까지)의 이력은 여기 없다. 우리가 그 위에서 시작했을 뿐 따라온 것이 아니라서다. 절차는 [upstream-sync.md](sync.md).

## v5.88 — 2026-08-18

**시스템 설정 창이 옆 줄 이름을 말하던 것을 고치고, 초당 프레임 표시가 다른 안내를 잘라먹던 것을 막는다.**

- `07e0769` v5.87을 냈고, 인게임 확인은 아직 안 했다고 적었다 (문서)
  원문: STATUS: Release v5.87 ist draussen, In-Game-Test steht noch aus
- `f343b1a` 시스템 설정 창의 결함 넷을 고쳤다. 전부 2026-08-18 로그와 노드 덤프에서 잡은 것이다 (릴리스 v5.88)
  원문: Release v5.88: Einstellungen richtig beschriftet, keine Bildfrequenz-Flut

고친 넷은 이렇다.

1. **이름을 노드 순서로 찾다가 옆 줄을 말했다.** 노드 목록은 화면 배치가 아니라 NodeId 내림차순이고 방향도 창마다 다르다. 그래픽 탭에서는 내내 **옆 설정의 이름**이 나갔다(`그림자 해상도` 자리에서 옆 줄 이름). 이제 화면 좌표로 찾는다 — 같은 줄에서 **왼쪽**에 있는 글자가 그 설정의 이름이다. 업스트림 실측 14곳 중 14곳 적중, 옛 방식으로 되떨어진 적 없음
2. **선택 항목이 어느 줄인지 안 말했다.** `흔들림 표현`(Addon 4155)은 자신·파티원·기타 플레이어·적 네 줄이 각각 세 값을 갖는데(적용 / 간략하게 적용 / 적용 안 함, 4160~4162), 버튼 자기 글자는 값뿐이라 열두 개가 다 똑같이 들렸다. 이제 줄 이름을 앞에 붙인다
3. **0.5초 중복 차단이 안내를 통째로 삼켰다.** 서로 다른 버튼이 같은 낱말을 달고 있으면 두 번째가 반복으로 잡혔다 — 위 네 줄을 오르내릴 때 아무 소리도 안 났다. 이제 어느 노드가 말하는지를 같이 넘겨서, **다른 노드면 같은 낱말이라도 말한다**
4. **선택 목록이 두 번 나갔고, 두 번째는 틀린 말이었다.** `스위치, 끔`이라고 했는데 실제로는 열린 목록이다. 시스템 설정 창에서는 조절바와 선택 목록을 전담 안내만 말하게 했다

그리고 **초당 프레임 표시**를 막았다. 창 구석에서 1초마다 바뀌는 숫자라 다른 안내를 계속 잘라먹었는데, 걸러내는 조건이 `fps`라는 **낱말**이었다 — 언어마다 다르고 소수점이 붙으면 독일어에서도 샌다. 이제 낱말을 안 본다. **3초 안에 세 번 바뀐 글자는 표시로 보고 그때부터 침묵**하고, 바뀐 글자가 숫자로 시작하면 변경 감시가 말하지 않는다.

덤 셋.

- **탭을 옮기면 그 페이지에 설정이 몇 개인지 같이 말한다** — 우리 빌드에서는 `그래픽 간단 설정, 설정 21개`로 나간다. 전에는 더 있는지 없는지 알 수가 없었다
- **F10이 설정 창에서 여덟 페이지를 통째로 읽던 것**을 열린 페이지만 읽게 했다. 숨은 페이지는 컨테이너만 감춰지고 글자는 보이는 상태로 남아 있어서 생긴 일이다
- **F5 노드 덤프에 좌표와 크기가 같이 찍힌다**

우리 쪽: 패치 **0001~0007은 그대로 붙었고**, 한국어 생성 패치(`0008`)는 붙이지 않고 카탈로그에서 **다시 만들었다**([upstream-sync.md](sync.md) §5.4). 카탈로그 669개가 소스에서 전부 제자리를 찾았다 — 업스트림이 우리가 옮긴 문장을 고친 것은 없다.

**새 안내 문장 1개**, 그런데 **골든 쌍은 688 그대로다.** 단수/복수 갈림길을 품은 보간 문자열이라 스냅샷 파서가 못 읽는 자리이기 때문이다(`unparsed` 41 → 42). 손 케이스로 옮겨 `overlay/patches/0009`가 35곳에서 36곳이 됐다.

| 독일어 | 영어 | 한국어 |
|--------|------|--------|
| `{heading}, {count} Einstellung(en)` | `{heading}, {count} setting(s)` | `{heading}, 설정 {count}개` |

## v5.87 — 2026-08-17

**사냥 목표를 고르면 지도 표식이 아니라 살아 있는 몬스터 자체로 달려간다.**

- `918c5f1` v5.86을 냈고, 라이선스 관련 파일을 릴리스에 같이 붙였다
  원문: STATUS: Release v5.86 ist draussen, Lizenz-Assets jetzt am Release
- `a8ac7c5` 개체 목록의 사냥 목표에서 Numpad3을 누르면, 그때까지는 서식지 지도 표식까지만 갔다. 살아 있는 개체가 개체 목록에 있으면 이제 그걸 대상으로 잡고 매 프레임 위치를 다시 읽으며 달린다 — 순찰하는 몬스터도 따라간다. 게임이 대상 지정을 거부하면 마지막으로 본 자리로 간다. 목록을 넘길 때 읽는 거리·방향도 지역이 아니라 몬스터 기준으로 바뀌었다
  원문: Release v5.87: Jagdziele laufen direkt zum Monster

우리 쪽: 패치 10건이 충돌 없이 다시 붙었다. **새 안내 문장 1개** — 번역 대기.

| 독일어 | 영어 |
|--------|------|
| `in der Nähe` | `nearby` |

## v5.86 — 2026-08-17

**개체 목록에 "사냥 목표" 갈래가 생기고, 등급 안내가 숫자만 읽지 않는다.**

- `cf7ee27` 게임패드로 모드를 조작할 수 있는지 조사만 하고 **아무것도 만들지 않았다.** 기술은 되는데 버튼이 모자란다 — 모드가 쓰는 조합이 52개인데 패드 버튼은 16개고 그마저 게임이 전부 쓰고 있다. 특정 버튼만 가로채는 것은 Dalamud 공개 API로 안 되고, 게임보다 먼저 잡을 수 있는지는 재 봐야 안다고 적어 뒀다
  원문: Controller-Bedienung: Machbarkeit geprueft, nichts gebaut
- `631e763` 라이선스 고지를 보냈고, PR 7에 남은 약속을 기록해 뒀다 (문서)
  원문: STATUS: Lizenz-Hinweise sind abgeschickt, offene Zusage zu PR 7 vermerkt
- `70d6ae3` 등급 목록이 "1, 10 중 10"이라고만 말하던 것을 "등급 1, 항목 10개 전부 끝냄"으로 고쳤다. 세는 대상이 처치 수가 아니라 항목 수라는 것을 시트로 검산했다. 개체 목록에 **사냥 목표**(`Jagdziele`, 용어 미확인) 갈래가 새로 생겨, 지금 등급에 남은 몬스터를 사는 지역과 함께 말한다 — 같은 지역이면 거리와 방향으로, 다른 지역이면 지역 이름과 가는 길로. 남은 게 없으면 갈래 자체가 안 나온다
  원문: Release v5.86: Jagdziele im Objekt-Browser, Bestiarium-Raenge benannt

우리 쪽: 패치 10건이 충돌 없이 다시 붙었다. **새 안내 문장 11개** — 번역이 그만큼 밀린다. 새 서비스 파일(`HuntingLogService.cs`)이 하나 생겼고, 우리 패치가 건드리는 파일과 겹치지 않는다.

| 독일어 | 영어 |
|--------|------|
| `Jagdziele` | `Hunting targets` |
| `lebt in {area}` | `lives in {area}` |
| `Rang {rank}, alle {total} Einträge erledigt` | `Rank {rank}, all {total} entries complete` |
| `Rang {rank}, {done} von {total} Einträgen erledigt` | `Rank {rank}, {done} of {total} entries done` |
| `{monster}, {killed} von {required} erlegt` | `{monster}, {killed} of {required} killed` |
| `Keine offenen Jagdziele in diesem Rang.` | `No open hunting targets in this rank.` |
| `Jagdziele: {total} offen, {here} in diesem Gebiet.` | `Hunting targets: {total} open, {here} in this area.` |
| `Jagdziele: {total} offen, keines in diesem Gebiet.` | `Hunting targets: {total} open, none in this area.` |
| `Für {monster} ist kein Ort bekannt.` | `No location known for {monster}.` |
| `{monster} lebt in {area}. Dieses Gebiet ist auf der Karte nicht verzeichnet.` | `{monster} lives in {area}. That area is not marked on the map.` |
| `{monster} lebt in {zone}. Dorthin führt kein Weg über Gebietsübergänge.` | `{monster} lives in {zone}. No route there over zone transitions.` |

**KR에서 확인해야 할 것 셋**(`W-15`). 업스트림 실측은 전부 독일어 클라이언트 기준이다.

1. **몬스터 이름 자리표시자** — `HuntingLogService.ResolveMonsterName`이 시트 이름에 `[`가 있으면 **독일어일 때만** 어미를 채우고 나머지 언어는 자리표시자를 지운다. KR 시트에 그런 표시가 있으면 이름이 어긋나고, `FindNearestLive`가 이름으로 찾으므로 **몬스터까지 걸어가는 기능이 죽는다**
2. **등급 줄 모양** — `TryFormatBestiaryRank`가 노드 id가 아니라 "숫자 하나 + 진행 토큰 하나"로 줄을 알아본다. KR 창이 같은 모양으로 그리는지는 인게임에서만 안다
3. **서식지 표** — "647개 전부 해석되고 590개가 마커를 갖는다"는 업스트림 실측이다. KR 시트에서 같은 수치인지 미확인

## v5.85 — 2026-08-16

**숫자만 덩그러니 읽히던 창 세 곳이 그 숫자가 무슨 뜻인지 말한다.**

우리가 처음 올라탄 자리다. 핀은 이 태그보다 커밋 하나 앞서 있다(`3051202`) — 클론한 시점의 `main`이 거기였고, 그 하나는 라이선스 고지다. 다음 동기화부터는 핀이 태그와 정확히 맞는다.

- `e12fce0` v5.84를 냈고, 테스트 브랜치에 있던 것이 전부 공개됐다
  원문: STATUS: v5.84 released, alles aus dem Testzweig ist jetzt oeffentlich
- `488ebd2` README가 외부 기여자 bladestorm360의 기여 여섯 건을 이름으로 밝힌다
  원문: READMEs nennen bladestorm360 bei seinen sechs Beitraegen
- `0ff280d` 교환 창이 가격과 설명을 읽는다 (`Marken`, 용어 미확인)
  원문: Tauschfenster nennt Preis in Marken und die Beschreibung
- `d0c9cda` 교환 창이 지금 얼마나 갖고 있는지도 말한다
  원문: Tauschfenster sagt auch, wie viele Marken man hat
- `d1cee70` 숫자만 나오던 창 세 곳이 뜻을 말한다 (릴리스 v5.85)
  원문: Release v5.85: drei Fenster, in denen nur nackte Zahlen standen
- `3051202` 라이선스를 AGPL-3.0으로 밝히고, 동봉한 외부 소프트웨어를 고지한다
  원문: Lizenz: AGPL-3.0 und Hinweise auf die mitgelieferte Fremdsoftware
