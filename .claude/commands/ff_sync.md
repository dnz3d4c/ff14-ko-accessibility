---
description: 원본 접근성 모드(derbruedi/ff14-accessibility) 따라잡기 - 재고, 올리기, 이력 자리, 기록 정리
argument-hint: check | up <태그> | notes | patches
---

# /ff_sync — 원본 모드 따라잡기

받은 인자: `$ARGUMENTS` — 비었으면 `check`로 친다.

**규칙의 단일 원천은 [docs/upstream-sync.md](../../docs/upstream-sync.md)다.** 이 파일은 순서와 멈출 자리만 갖는다. 판정 기준을 여기 베끼지 않는다 — 베끼면 그게 두 번째 사본이 되고, `tools/docs-check`가 안 보는 자리라 조용히 낡는다.

## 멈추는 조건 — 먼저 읽는다

아래가 하나라도 나오면 **커밋하지 않고 멈춰서 보고한다.** 되돌릴 수 없어서가 아니라, 사람이 정해야 할 것이 섞여 들어왔기 때문이다.

- 생성 커밋이 **아닌** 커밋이 충돌한다 → 업스트림이 우리 커밋이 하려던 일을 이미 했는지 판단해야 한다 (§5.3)
- 골든 대조에서 **사라진 문장**이 있다 → 업스트림이 우리가 옮긴 문장을 고쳤거나 우리가 떨어뜨린 것이다. `--write`를 먼저 누르면 증거가 사라진다
- `tools/ko-apply`가 **카탈로그 고아**를 댄다 → 위와 같은 원인이고, 어느 문장인지까지 나온다
- 골든의 `unparsed`가 **늘었다** → 손으로 옮길 자리가 생겼다. 번역과 용어 판단이 필요하다
- 쓸 게임 용어를 `overlay/ko/terms.json`이나 Addon 덤프에서 **못 찾았다** → 지어내지 않는다. 못 찾았다고 적고 묻는다
- `run\check.bat`이 빨갛다
- 우리 저장소나 `vendor/`에 **커밋 안 된 변경**이 남아 있다 (시작 전에 본다)

멈출 때는 어디까지 갔고 무엇이 되돌릴 수 있는지 같이 적는다. `kr-port-<이전태그>` 브랜치가 되돌릴 자리다 — 미러에도 같이 밀려 있다.

## check (기본)

    cmd //c "set FF14_NOPAUSE=1 && run\sync.bat"

아무것도 안 옮긴다. 읽을 것 넷: 새 태그, 겹치는 파일, **`kr-port`가 새 태그에 아직 얹히는가**, 이력에 빠진 판.

얹히는지 여부가 조기 경보다. 겹치는 파일이 있어도 얹히면 대개 문제없고, 안 얹히면 그때가 손이 필요한 시점이다.

## up \<태그\>

태그를 안 주면 **여기서 멈추고 `check` 결과를 보여준 뒤 어느 태그로 갈지 묻는다.** 최신에 자동으로 끌려가지 않는 것이 이 도구의 방침이다.

1. **선행 확인.** 우리 저장소와 `vendor/` 둘 다 `git status`가 깨끗한가. 아니면 멈춘다.
2. **재고.** `run\sync.bat`으로 얹히는지 본다.
3. **깨끗하면 도구가 다 한다.**

       cmd //c "set FF14_NOPAUSE=1 && run\sync.bat <태그>"

   되돌릴 자리 생성, `git rebase --onto`로 `kr-port` 재적재, `main` 이동, 핀 갱신, **미러 push**까지가 도구 몫이다. 미러에 못 밀었다고 나오면 gitlink을 커밋하지 않고, 도구가 알려 준 push부터 다시 한다.
4. **생성 커밋에서 멈추면 그게 정상 경로다.** 한국어 커밋은 생성물이라 **충돌을 풀지 않고 버리고 다시 만든다** (§5.4, [overlay/patches/README.md](../../overlay/patches/README.md)). 순서:
   - `git rebase --skip`으로 그 커밋만 버리고 끝까지 얹는다
   - `uv run --no-project python tools/ko-apply/ko_apply.py --write`
   - vendor에 **같은 제목으로** 커밋한다 — 제목은 고정형(`Korean: the mod's own strings, generated from the catalogue`)이라 바꾸지 않는다. `tools/ko-apply`가 그 제목으로 커밋을 찾는다
   - 미러로 밀고(§5.2의 push), 핀은 손으로 고치지 않는다 — `upstream_sync.write_pin`을 쓴다 (§5.3)
5. **새 자리를 저장소에 기록한다.**

       git add vendor/ff14-accessibility

6. **이력을 한국어로.** `docs/upstream-changes.md`에 자리를 만들고 채운다. **핀을 옮긴 뒤에 돌려도 된다** — 핀 태그 자신도 대상이다.

       uv run --no-project python tools/upstream-sync/upstream_sync.py --notes

   원문을 지우지 않고, 기계 번역을 붙이지 않고, 모르는 게임 용어는 원문 병기 + `용어 미확인`. `(미번역)`이 남으면 테스트와 훅 C10이 막는다.
7. **문장이 늘었는지 잰다.**

       uv run --no-project python tools/strings-golden/strings_golden.py
       uv run --no-project python tools/ko-apply/ko_apply.py

   **쌍 수만 보면 놓친다.** 갈림길이 보간 문자열 안에 들어 있으면 파서가 아예 못 세서, 문장이 늘어도 쌍은 그대로다(v5.88 `ConfigPageWithCount`가 그랬다). `unparsed`가 움직였는지 같이 본다 — 늘었으면 손 케이스이고, [ko-localization 스킬](../skills/ko-localization/SKILL.md)과 [docs/ko-hand-cases.md](../../docs/ko-hand-cases.md)를 따라 손 케이스 커밋(`0009`)에 넣는다.
8. `cmd //c "set FF14_NOPAUSE=1 && run\check.bat"` — 전부 통과할 것.
9. **문서를 옮긴다.** [docs/status.md](../../docs/status.md)(핀, §1 직전, §9 한 줄, 인용 숫자), `docs/upstream-changes.md`, 손 케이스가 늘었으면 `docs/ko-hand-cases.md`·`README.md`. 숫자를 새로 손으로 적으면 `tools/docs-check`의 `CITATIONS`에 등록한다.
10. **배포물이 뒤졌으면 다시 낸다.** 소스 판이 올라갔는데 `dist/`가 옛 판이면 그 자체가 결함이다(실제로 5.85 압축을 5.87 소스라고 들고 있었다).

        cmd //c "set FF14_NOPAUSE=1 && run\pack.bat"

11. **커밋.** [docs/commit-rules.md](../../docs/commit-rules.md) §2.5 — 핀·gitlink 이동은 `[벤더]`(`Upstream-Range` 필수, `upstream-changes.md`를 같이 건드려야 C10 통과, gitlink 갈래는 C11이 본다). 충돌을 풀며 우리 커밋의 내용을 다시 썼으면 본문에 밝힌다([upstream-sync.md](../../docs/upstream-sync.md) §8). 그다음 push.
12. **인게임 판정은 사용자 몫이다.** 기계는 여기까지 못 온다. 실행 대상은 [CLAUDE.md](../../CLAUDE.md) `## 확정된 실행 대상`에서 그대로 주고, **무엇을 귀로 확인하고 무엇을 알려줘야 하는지**까지 적는다.

## notes

`docs/upstream-changes.md`에 빠진 판의 자리를 만들고 한국어로 채운다. `up`의 6단계만 따로 돌리는 것이다.

    uv run --no-project python tools/upstream-sync/upstream_sync.py --notes

## patches (기록 정리)

`vendor/ff14-accessibility`의 `kr-port`에 커밋해 놓고 저장소 기록(gitlink)을 안 옮긴 상태를 정리한다. 기록을 안 옮기면 **우리 저장소에는 아무 증상도 안 남는다.** 이름이 `patches`인 것은 패치 재추출 시절의 인터페이스를 그대로 받기 때문이고, 하는 일은 기록 정리다.

1. `uv run --no-project python tools/patch-check/patch_check.py` — 기록이 `kr-port` 팁인지, 핀이 그 조상인지, vendor에 커밋 안 된 변경이 있는지
2. vendor가 더러우면 `kr-port`에 커밋부터 한다
3. 미러로 민다 — 이 머신(전체 클론)의 원격 이름은 `mirror`다: `git -C vendor/ff14-accessibility push mirror kr-port`
4. `git add vendor/ff14-accessibility`로 기록을 옮겨 같이 커밋한다 — 갈래는 커밋 내용대로 (`[벤더]`·`[업스트림]`·`[한국전용]`만 포인터를 옮길 수 있다, C11)
5. 생성 커밋을 손으로 고쳤으면 pytest가 잡는다. 고쳤다면 되돌리고 `ko-apply`로 다시 만든다
