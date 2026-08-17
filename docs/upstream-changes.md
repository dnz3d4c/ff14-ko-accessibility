# 업스트림 변경 이력 (한국어)

업스트림([derbruedi/ff14-accessibility](https://github.com/derbruedi/ff14-accessibility))은 **독일어로 개발된다.** 커밋 메시지도 릴리스 노트도 독일어라, 우리 저장소에 뭐가 들어왔는지 그대로는 읽을 수 없다. 여기에 한국어로 옮겨 둔다.

- **자리는 도구가 만들고, 번역은 사람이 채운다.** `--notes`가 원문과 함께 `(미번역)` 자리를 만들고, 그게 남아 있는 동안은 검사가 통과하지 않는다.
- **원문을 지우지 않는다.** 옮긴 것이 틀렸을 때 되짚을 자리가 그것뿐이다.
- **모르는 게임 용어는 지어내지 않는다.** 한국어판 표기를 확인하지 못한 것은 원문을 괄호로 병기하고 `용어 미확인`이라고 적는다. 근거 없는 표기를 한 번 박아 두면 그게 기준이 된다(2026-08-18 `Aetheryte` 건).
- 역순이다. 위가 최신.

핀 이전(v5.84까지)의 이력은 여기 없다. 우리가 그 위에서 시작했을 뿐 따라온 것이 아니라서다. 절차는 [upstream-sync.md](upstream-sync.md).

## v5.87 — 2026-08-17

**사냥 목표를 고르면 지도 표식이 아니라 살아 있는 몬스터 자체로 달려간다.**

- `918c5f1` v5.86을 냈고, 라이선스 관련 파일을 릴리스에 같이 붙였다
  원문: STATUS: Release v5.86 ist draussen, Lizenz-Assets jetzt am Release
- `a8ac7c5` 개체 목록의 사냥 목표에서 Numpad3을 누르면, 그때까지는 서식지 지도 표식까지만 갔다. 살아 있는 개체가 개체 목록에 있으면 이제 그걸 대상으로 잡고 매 프레임 위치를 다시 읽으며 달린다 — 순찰하는 몬스터도 따라간다. 게임이 대상 지정을 거부하면 마지막으로 본 자리로 간다. 목록을 넘길 때 읽는 거리·방향도 지역이 아니라 몬스터 기준으로 바뀌었다
  원문: Release v5.87: Jagdziele laufen direkt zum Monster

우리 쪽: 패치 10건이 그대로 붙는다. 새 안내 문장 없음.

## v5.86 — 2026-08-17

**개체 목록에 "사냥 목표" 갈래가 생기고, 등급 안내가 숫자만 읽지 않는다.**

- `cf7ee27` 게임패드로 모드를 조작할 수 있는지 조사만 하고 **아무것도 만들지 않았다.** 기술은 되는데 버튼이 모자란다 — 모드가 쓰는 조합이 52개인데 패드 버튼은 16개고 그마저 게임이 전부 쓰고 있다. 특정 버튼만 가로채는 것은 Dalamud 공개 API로 안 되고, 게임보다 먼저 잡을 수 있는지는 재 봐야 안다고 적어 뒀다
  원문: Controller-Bedienung: Machbarkeit geprueft, nichts gebaut
- `631e763` 라이선스 고지를 보냈고, PR 7에 남은 약속을 기록해 뒀다 (문서)
  원문: STATUS: Lizenz-Hinweise sind abgeschickt, offene Zusage zu PR 7 vermerkt
- `70d6ae3` 등급 목록이 "1, 10 중 10"이라고만 말하던 것을 "등급 1, 항목 10개 전부 끝냄"으로 고쳤다. 세는 대상이 처치 수가 아니라 항목 수라는 것을 시트로 검산했다. 개체 목록에 **사냥 목표**(`Jagdziele`, 용어 미확인) 갈래가 새로 생겨, 지금 등급에 남은 몬스터를 사는 지역과 함께 말한다 — 같은 지역이면 거리와 방향으로, 다른 지역이면 지역 이름과 가는 길로. 남은 게 없으면 갈래 자체가 안 나온다
  원문: Release v5.86: Jagdziele im Objekt-Browser, Bestiarium-Raenge benannt

우리 쪽: 패치 10건이 그대로 붙는다. **새 안내 문장 5개** — 번역이 그만큼 밀린다.

| 독일어 | 영어 |
|--------|------|
| `Jagdziele` | `Hunting targets` |
| `in der Nähe` | `nearby` |
| `lebt in {area}` | `lives in {area}` |
| `Rang {rank}, alle {total} Einträge erledigt` | `Rank {rank}, all {total} entries complete` |
| `Rang {rank}, {done} von {total} Einträgen erledigt` | `Rank {rank}, {done} of {total} entries done` |

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
