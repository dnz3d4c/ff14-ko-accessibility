# loc-check — 설치 프로그램 문구가 한국어로 나가는지 지킨다

`tools/ko-speech`가 **모드**의 발화를 지킨다면, 이쪽은 **설치 프로그램**을 본다. 둘로 나눈 이유는 하나다 — `ko-speech`의 `SOURCE_ROOT`가 `FF14Accessibility/`(플러그인)라서 `Installer/`는 어느 검사에도 안 걸렸다.

## 왜 생겼나

`Installer/Loc.cs`의 `Get`은 세 번 조용하다.

- 현재 언어에 키가 없으면 **영어로 떨어진다**(`Loc.cs:29`). 로그도 예외도 없다
- 영어에도 없으면 **키 이름을 그대로 돌려준다**. 사용자는 `InstallerAssetMissing` 같은 식별자를 듣는다
- 키가 있어도 값이 비면 **접두만 붙은 빈 줄**이 나간다. 실제로 `ConfigNotExist4`가 그 모양이었다

셋 다 오류가 아니라서, 드러나는 자리는 사용자 화면뿐이다.

**2026-08-19 실측으로 새는 자리는 0건이었다** — 부르는 키가 전부 한국어를 갖고 있었다. 그래서 지금 못박는다. 이 검사가 막는 것은 이미 난 사고가 아니라 **다음에 영어 키만 더하는 순간**이다.

지금 몇 개인지는 여기 적지 않는다. 도구가 돌 때마다 세어서 말한다 — 손으로 옮겨 적은 숫자는 낡는다(현황판 §8-1).

## 무엇을 보나

| 검사 | 무엇이 걸리나 | 사용자가 겪는 것 |
|------|--------------|-----------------|
| 번역 없음 | 부르는 키에 한국어가 없다 | 영어 문장이 나간다 |
| 정의 없음 | 부르는 키가 어느 사전에도 없다 | **키 이름**이 그대로 나간다 |
| 빈 값 | 어느 언어든 값이 비었다 | `경고: ` 한 줄만 나간다 |
| 맨 리터럴 | `Loc.Get`을 안 거치는 문자열 | 어느 언어로도 안 갈린다 |
| 죽은 키 | 번역 없는 키가 골든보다 늘었다 | (아직 아무 일도 안 일어난다) |

**맨 리터럴은 두 갈래로 잡는다.** 움라우트(`[äöüßÄÖÜ]`)를 가진 것은 어디 있든 잡고, 그 밖에는 사람에게 말하는 호출(`Info`/`Warn`/`Error`)의 인자일 때만 잡는다. 라틴 문자만으로는 문장인지 파일 이름인지 안 갈려서, `ko-speech`가 형제 대조로 푸는 문제를 여기서는 **호출 자리**로 푼다.

글자가 하나도 없는 리터럴은 안 잡는다. `Info("  " + path)`의 `"  "`는 들여쓰기지 문장이 아니다.

## 죽은 키는 골든에 담는다

영어 사전에만 있고 아무도 안 부르는 키가 28개 있다. 글로벌 설치 프로그램에서 온 `XivLauncher` 잔재라 한국어를 지어낼 이유가 없다. 지우는 것은 업스트림 소스를 건드리는 일이라 여기서 안 하고, **늘어나는 것만 막는다.**

그 키를 누가 부르기 시작하면 골든이 아니라 `번역 없음`으로 걸린다 — 죽은 키의 정의가 "안 불린다"이기 때문이다.

## 주석은 남의 것을 쓴다

문자열 안의 `//`를 주석으로 읽으면 안 된다. 안내 문구에 `https://goatcorp.github.io/`가 들어 있어서, 그 줄이 통째로 지워지면 멀쩡한 값이 비었다고 잡힌다. 이미 `tools/strings-golden`의 `strip_comments`가 그 문제를 풀어 놨으므로 가져다 쓴다 (선례: `tools/docs-check`가 `ko_words`를 그렇게 쓴다).

## 한계 — 이 검사가 안 보는 자리

**초록이라고 "안내 문구가 다 한국어다"가 아니다.** 아래는 이 도구가 판정하지 않는 것이고, 각각 무엇으로 확인하는지 같이 적는다.

한계를 적어 두는 것만으로는 모자란다는 것이 이 저장소의 경험이다. `ko-words` README가 "지명은 `PlaceName` 시트라 여기 밖"이라고 적어 뒀는데, 번역 검수가 그 문장을 **인용까지 해 놓고** 결론에는 반영하지 않아 멀쩡한 낱말을 결함으로 판정할 뻔했다. 그래서 여기는 **확인 명령까지** 둔다.

### 1. 맨 리터럴은 세 호출만 본다

`Info`·`Warn`·`Error`의 인자만 본다(움라우트를 가진 것은 예외로 어디서든 잡는다). **사용자에게 문자열이 닿는 길은 그 셋만이 아니다.**

- `MessageBox.Show(...)` — 대화 상자
- `Text = ...` — 창 제목과 버튼 글자
- `AccessibleName = ...` — **스크린리더가 읽는 이름**
- `Console.WriteLine(...)` — `--check`/`--install`의 출력

2026-08-19 기준 이 자리들은 전부 `Loc.Get`을 거치고 있다. **우연이 아니라 지금까지 그렇게 써 온 것뿐이고, 이 검사가 그걸 지키지는 않는다.** `AccessibleName = "직접 쓴 문자열"`이 들어와도 조용하다.

확인 (`Loc.Get`을 안 거치고 대입된 자리를 센다):

uv run --no-project python -c "import re,sys;sys.path.insert(0,'tools/loc-check');import loc_check;from pathlib import Path;p=Path('vendor/ff14-accessibility/Installer');rx=re.compile(r'(MessageBox\.Show|Console\.WriteLine)\s*\(\s*\"|(?<![A-Za-z0-9_.])(Text|AccessibleName|AccessibleDescription)\s*=\s*\"');print([(c.name,m.group(0)) for c in p.rglob('*.cs') if c.name!='Loc.cs' for m in rx.finditer(loc_check._strip_comments(c.read_text(encoding='utf-8')))])"

빈 목록이 아니면 그 자리를 눈으로 본다. 진단 출력(`KrCheck.cs`의 `--check` 줄)은 사용자 안내가 아니라 여기 걸려도 결함이 아니다.

### 2. 죽은 키 골든은 "지금 안 불린다"만 말한다

**골든이 구멍이 되지는 않는다.** 골든에 담긴 키에 호출부가 생기면 `번역 없음`과 `골든에만 남은 키` 두 갈래로 걸린다(합성 소스로 실증했다). 통과시키지 않는다.

다만 골든이 **말하지 않는 것**이 둘이다.

- **그 키를 지워야 하는지 아닌지.** 28개는 글로벌 설치 프로그램 잔재라는 한 문장으로 묶여 있을 뿐, 항목마다 왜 남았는지가 없다. `ko-speech`는 `why`가 비면 빨개지는데 여기는 그렇지 않다 — **W-53(`ko-words` 골든에 항목별 판단이 없다)과 같은 부류다**
- **영어 문구가 맞는지.** 이 도구는 키가 있나 없나만 본다

확인: `tools/loc-check/golden/dead-keys.json`을 열어 28개를 눈으로 훑는다. 한 줄씩 판단이 필요하면 W-53과 같이 처리한다.

### 3. `Loc.Get(변수)`는 못 센다

키 집계는 `Loc.Get("리터럴")`만 잡는다. `Loc.Get(key)`처럼 변수를 넘기면 **그 키는 "안 불린다"로 분류되고**, 한국어가 없어도 죽은 키 골든이 통과시킨다. 조용히 새는 유일한 갈래다.

2026-08-19 기준 183개 호출이 전부 리터럴이라 지금은 0건이다.

확인 (0이 아니면 그만큼 집계에서 빠진 것이다):

uv run --no-project python -c "import re,sys;sys.path.insert(0,'tools/loc-check');import loc_check;from pathlib import Path;p=Path('vendor/ff14-accessibility/Installer');print(sum(len(re.findall(r'Loc\.Get\(\s*(?!\")',loc_check._strip_comments(c.read_text(encoding='utf-8')))) for c in p.rglob('*.cs')))"

### 4. 사전 파싱은 정규식이라 모양에 기댄다

`[English] = new Dictionary<string, string> { ... }` 꼴을 찾고, 그 안에서 `["키"] =` 꼴을 센다. `Loc.cs`가 초기화 구문을 바꾸면 못 읽는다.

**다만 못 읽는다고 조용해지지는 않는다.** 합성 소스로 확인했다.

- 사전 블록 자체를 못 찾으면 → `ValueError`로 죽는다
- 블록은 찾고 항목 모양만 바뀌면 → 사전이 0개가 되고, 부르는 키가 **전부 `정의 없음`으로** 걸린다

조용해지는 경우는 하나뿐이다 — **사전과 호출부를 동시에 못 읽을 때**다(`Loc.Get` 표기까지 바뀌는 경우). 그때는 0 대 0이라 아무 말도 안 한다. 그 자리를 `test_실물에서_사전을_실제로_읽는다`가 막는다: 한국어 100개 미만이거나 부르는 키 100개 미만이면 빨개진다. **이 테스트를 지우면 위 검사 넷이 조용히 무의미해진다.**

### 5. 모드 쪽은 안 본다

`Installer/`만 본다. 플러그인(`FF14Accessibility/`)의 발화는 `tools/ko-speech`·`tools/ko-apply`·`tools/strings-golden`이 나눠 갖는다. 두 검사망은 겹치지 않으므로, 어느 쪽이 초록이라고 다른 쪽을 말해 주지 않는다.

## 쓰는 법

    uv run --no-project python tools/loc-check/loc_check.py           # 대조
    uv run --no-project python tools/loc-check/loc_check.py --write   # 죽은 키 골든 갱신

`run\check.bat`의 테스트 단계에서 pytest가 같이 돌린다.

## 테스트

    uv run --no-project --with pytest pytest tools/loc-check -q
