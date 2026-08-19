# PR — 서식지와 지역이 붙어 읽히던 것

- 보낸 날: 2026-08-18
- 보낸 곳: [derbruedi/ff14-accessibility PR #8](https://github.com/derbruedi/ff14-accessibility/pull/8) (base `main`)
- 브랜치: `upstream-habitat-separator` — 업스트림 `07e0769` 위에 커밋 하나
- 바뀌는 것: `FF14Accessibility/Services/NavigationService.cs` 한 파일, `+4 -1`
- 우리 쪽 변경: `kr-port`의 해당 커밋 — [patches/README.md](README.md) 항목 `0001` (보낸 시점에는 패치 파일 `patches/0001`이었고, 시리즈 정리 전에는 `0003`이었다. 패치 파일은 W-11에서 없앴다)

**§2와 §3이 GitHub에 올라간 문장 그대로다.** 한국어는 §4에만 있고 PR에는 안 들어갔다.

## 1. 왜 이 문장들로 썼나

**표를 안 썼다.** 유지관리자가 시각장애인이고 커밋을 TTS로 읽는다. 업스트림 `CLAUDE.md`에 자기 도구 출력 규칙으로 *"NO `|` tables, use lists"*를 박아 뒀다 — 그 사람이 읽기 편한 모양이 그거다. 목록과 짧은 문단만 쓴다.

**증상을 맨 앞에 놨다.** 이 결함은 보이는 사람에게는 안 보인다. 글자로는 그냥 읽히기 때문이다. 그래서 "무엇이 잘못 발음되는가"를 먼저 보여주고 원인을 뒤에 놓는다.

**우리가 KR 클라뿐이라는 것을 숨기지 않는다.** 독일어·영어 문장은 소스에서 읽은 것이지 들은 것이 아니다. 그 경계를 본문에 적었다.

## 2. PR 제목 (이 한 줄 그대로)

Hunting targets no longer run the habitat into the area name

## 3. PR 본문 (여기부터 §4 앞까지 그대로)

When a hunting log target lives in another zone, the announcement joins the
habitat clause and the area clause with nothing between them:

```
lives in Sandgate Ridgein the area Eastern Thanalan
lebt in Kaktusgrundim Gebiet Ost-Thanalan
```

A screen reader pronounces `Ridgein` and `Kaktusgrundim` as one unknown word.
Sighted players never notice, because the text still reads.

The cause is a missing separator in `NavigationService.CycleHuntTarget`:

```csharp
text += ", " + AccessibilityStrings.HuntingArea(target.AreaName) + zone;
```

`HuntingArea` ends without a space (`lebt in {area}` / `lives in {area}`), and
`InArea` and `InAnotherArea` start without one (`im Gebiet {zone}.` /
`in the area {zone}.`). So the two clauses fuse.

### Why the call site and not the string

The other two `InArea` call sites are the cross-zone quest goal and the
cross-zone leve. Both prepend their own `", "` and read correctly today.
Putting the space into `InArea` itself would give those two a double
separator. The call site is where it is missing.

### Rows without a habitat

`HuntingArea` returns an empty string when the hunting log names no habitat,
and `HuntingAreaUnknown` shows that such rows exist. Adding the space
unconditionally would open the sentence on a gap:

```
,  in the area Eastern Thanalan
```

So the separator is only added when there is something to separate. Rows
without a habitat keep exactly the wording they had before.

### Verification

- Build: 0 warnings, 0 errors.
- In game, 2026-08-18: the line now reads `lives in <habitat> in the area
  <zone>`, with the pause between the two clauses.
- I only have a Korean client, so the German and English wording is read from
  the string definitions rather than heard. The defect is in the
  concatenation and not in any one language, so it is present in every locale
  - the German example above comes from the same two strings.

## 4. 한국어 대역 (PR에는 안 들어간다)

§3이 말하는 것을 그대로 옮기면 이렇다. 주장마다 근거 파일을 붙였다.

- 사냥수첩 목표가 **다른 지역에 있을 때** 서식지와 지역이 구분자 없이 붙는다. `NavigationService.cs`의 `CycleHuntTarget`
- `HuntingArea`는 공백 없이 끝나고(`AccessibilityStrings.cs:473-476`) `InArea`·`InAnotherArea`는 공백 없이 시작한다(`:736-741`). 그래서 `가장자리in`, `Kaktusgrundim`이 된다
- **문자열이 아니라 호출부를 고치는 이유**: 다른 `InArea` 호출부 둘(`NavigationService.cs:806` 퀘스트, `:954` 임무)은 자기가 `", "`를 앞에 붙인다. 문자열에 공백을 넣으면 그 둘이 구분자 두 겹이 된다
- **서식지가 빈 행**: `HuntingArea`는 `area.Length == 0`이면 빈 문자열이다. 그런 행이 실재한다는 것은 `HuntingAreaUnknown`이 그 경우를 따로 갈라 놓은 것으로 안다(`:483-490`). 공백을 무조건 넣으면 문장이 빈칸으로 열려서, 붙일 것이 있을 때만 넣는다
- **검증 범위**: 빌드는 업스트림이 쓰는 글로벌 참조(ClientStructs 7.55)로 0경고 0오류. 인게임은 KR에서 확인. 독일어·영어는 **소스를 읽은 것이고 들은 것이 아니라고 본문에 적었다**

## 5. 보냈다

**[PR #8](https://github.com/derbruedi/ff14-accessibility/pull/8)** — 2026-08-18, base `main`, 파일 1개 `+4 -1`, 상태 OPEN.

- fork: `dnz3d4c/ff14-accessibility` (공개. `gh` 토큰에 `delete_repo`가 있어 나중에 지울 수 있다)
- 브랜치: `upstream-habitat-separator` (`0e2d932`, 업스트림 `07e0769` 위)

§2·§3의 문장이 그대로 올라갔다. **여기 남겨 두는 이유는 답이 오면 무엇을 근거로 뭘 주장했는지 되짚기 위해서다** — PR 본문은 나중에 편집될 수 있고, 이 파일은 보낸 시점의 것이다.

### 답이 오면

- **병합되면**: 다음 동기화 rebase에서 `kr-port`의 이 커밋이 저절로 비어 사라지고 나머지가 그대로 얹혀야 한다. `upstream.json` 핀을 옮긴다 ([upstream-sync.md](../docs/upstream/sync.md))
- **고쳐 달라면**: `vendor`의 `upstream-habitat-separator`에서 고치고 force push한다. `kr-port`의 같은 커밋도 같이 고친 뒤 미러에 밀고 `git add vendor/ff14-accessibility`로 기록을 옮긴다 — 안 옮기면 `patch-check`가 잡는다
- **거절되면**: 커밋은 `kr-port`에 그대로 남는다 — 로컬에는 계속 적용된다

## 6. 안 보내는 것

같이 검토했던 나머지는 전부 뺐다. 이유는 [README.md](README.md)의 기준 4·5와 [docs/status.md](../docs/status.md) §6에 있다. 요약하면 `0001`은 클라를 켜야 판정되고, `0002`는 고친 오류가 없고, "빈 갈림길 정리"는 전제가 틀렸다.
