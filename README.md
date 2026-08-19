# ff14-ko-accessibility

FFXIV 글로벌 서버용 접근성 플러그인([derbruedi/ff14-accessibility](https://github.com/derbruedi/ff14-accessibility))을 한국 공식 서버 클라이언트에서 쓸 수 있게 포팅하는 작업의 저장소.

## 지금 어디까지 왔나

**[프로젝트 현황판](docs/status.md)이 답을 갖는다.** 여기에 다시 적지 않는다 — 두 벌로 적으면 한 벌이 낡고, 실제로 그렇게 됐다([status.md](docs/status.md) §8-1).

뭘 고치기 전에 현황판을 먼저 연다. 남은 일도, 알려진 결함도, 사용자 판단을 기다리는 것도 전부 거기 있다.

## 문서

| 문서 | 무엇을 갖는가 |
|------|---------------|
| **[프로젝트 현황판](docs/status.md)** | **남은 일의 기준.** 다른 문서는 근거만 갖는다 |
| **[한국어 README](overlay/ko/README.ko.md)** | **사용자가 읽는 문서.** 설치·실행·키·명령어·문제 해결 |
| [한국 클라이언트 포팅 타당성 조사](docs/frozen/port-feasibility.md) | 착수 전 조사. **당시 표현 그대로 동결**했다 |
| [개발 환경 실측과 설치 결과](docs/dev/environment.md) | 경로·버전·빌드 함정 |
| [KR 실행 환경 구축 절차](docs/dev/kr-runtime.md) | 손으로 세울 때의 절차. 설치기가 이걸 대신한다 |
| [단축키 한국어 표](docs/korean/keys.md) | 독일어 키 이름 대응과 KR에서 겹치는 키 |
| [커밋 규칙](docs/dev/commit-rules.md) | 갈래·트레일러와 검사기가 막는 것 |
| [손으로 옮긴 36곳](docs/korean/hand-cases.md) | 생성기가 못 읽는 문장 모양과 조심할 것 |
| [한국어 전수 검수](docs/frozen/ko-review-2026-08-18.md) | 50곳을 고친 기록과 대장을 못 믿게 된 이유 |
| [업스트림 동기화](docs/upstream/sync.md) | 핀을 옮기는 절차 |
| [업스트림 변경 이력 (한국어)](docs/upstream/changes.md) | 원문이 독일어라 옮겨 둔다 |

## 왜 포팅이 가능한가 — 조사 결론

- 플러그인 소스에 리전 제한은 **없다.** 업스트림이 독일 클라이언트로만 개발·테스트했을 뿐이다.
- 실제 장벽은 그 아래 Dalamud 계층이고, 한국 서버용 Dalamud 배포 파이프라인이 제3자에 의해 이미 존재한다.
- 그래서 경로는 fork가 아니라 **업스트림엔 언어 일반화를 보내고, KR 전용은 얇게 따로 두는 것**이다.
- 설치된 KR 클라이언트 버전이 KR Dalamud 지원 버전과 **정확히 일치**한다.
- 업스트림 소스를 KR 호환 CS로 빌드했을 때 오류가 **정확히 1건**이었다 — 53,971줄에서 `RaptureGearsetModule.IsItemRegisteredToGearset` 하나. 확장 메서드 shim으로 메웠고(`overlay/patches/0001`), **글로벌 빌드의 바인딩은 바뀌지 않는다**(실증 완료).
- 게임 `sqpack`이 있으므로 **게임을 실행하지 않고 Lumina로 KR 시트를 읽을 수 있다.** 한국어 용어를 지어내지 않는 근거가 여기서 나온다.

## 매일 쓰는 것

게임과 모드를 켜는 것부터 로그 판정까지 배치가 갖고 있다. 자세한 건 [run/README.md](run/README.md).

C:\project\games\ff14-ko-accessibility\run\play.bat

## 구조

### 소스와 vendor

- `vendor/ff14-accessibility/` — 비공개 미러의 **submodule**. 소스 변경의 원본은 `kr-port` 브랜치의 커밋이고, 우리 저장소는 그 팁을 gitlink으로 기록한다. 왜 이 구조인지는 [vendor-submodule.md](docs/upstream/vendor.md)
- `patches/` — **업스트림에 보낼** 변경의 기준과 기록. 코드는 `kr-port`에 있다. 기각된 후보는 [rejected.md](patches/rejected.md)에 남고 다시 만들지 않는다
- `overlay/patches/` — **한국 전용** 변경의 명세. 코드는 역시 `kr-port`에 있다 ([README](overlay/patches/README.md))
- `overlay/ko/` — 한국어의 원본. `ko.json`이 `(독일어, 영어) → 한국어` 표이고, `terms.json`이 게임 한국어판에서 뽑은 용어 대장, `guide-quotes.json`이 공식 가이드에서 인용한 문장 대장, `README.ko.md`가 사용자에게 주는 문서다. **소스는 여기서 생성된다**
- `upstream.json` — **우리 커밋이 어느 업스트림 판 위에 얹혀 있는지.** gitlink은 `kr-port` 팁만 가리키므로 밑동은 이 핀이 기록한다

### 도구 (`tools/`)

한국어화:

- `ko-apply/` — 카탈로그를 소스에 써 넣어 `kr-port`의 생성 커밋을 만든다. **그 커밋은 생성물이라 손으로 고치면 테스트가 빨개진다** ([overlay/patches/README.md](overlay/patches/README.md))
- [`ko-terms/`](tools/ko-terms/README.md) — 게임을 켜지 않고 KR `sqpack`의 Addon 시트를 Lumina로 읽는다. 용어 대장의 출처
- [`ko-words/`](tools/ko-words/README.md) — 번역이 **실제로 쓴** 낱말을 전부 모아 게임 덤프와 대조한다. 대장에 적는 것을 잊어도 잡힌다
- `strings-golden/` — 한국어화 전 독일어·영어 688쌍 스냅샷. 옮기다 건드리면 빨개진다

사용자 문서:

- `ko-guide/` — 파판14 **공식 가이드**를 받아 두고 우리가 베낄 형식을 뽑는다. 문체 규약과 "눈으로 읽는 자리"의 근거가 여기서 나온다. 원문은 저장소 밖이다 ([코퍼스 안내](docs/korean/guide-corpus.md), [스킬](.claude/skills/ko-user-guide/SKILL.md))

저장소 규율:

- `commit-lint/` — 커밋 메시지 검증기 (`.githooks/commit-msg`가 호출, 규칙 C1~C11)
- `patch-check/` — 저장소가 기록한 vendor 자리(gitlink)가 `kr-port` 팁이고 핀이 그 조상인지, vendor에 커밋 안 된 변경이 없는지 (`.githooks/pre-commit`과 `run\check.bat`이 돌린다)
- `docs-check/` — 문서가 인용한 숫자를 산출물에서 다시 계산해 대조하고, 현황판의 절끼리 어긋난 것을 잡는다
- `upstream-sync/` — 업스트림이 얼마나 앞서 갔는지 재고, 깨끗할 때 `kr-port`를 새 태그 위에 다시 얹어 미러로 민다. 변경 이력을 한국어로 남길 자리도 여기가 만든다

KR 검증 (전부 게임을 켜지 않고 돈다):

- `kr-setup/` — 개발용 배포를 KR 프로필 설정에 심고, 로그를 기계로 판정한다
- [`pack-check/`](tools/pack-check/README.md) — 배포 산출물이 바닐라인지, 설치 결과가 Dalamud가 읽는 모양인지 잰다. 설치기를 버리는 프로필에 대고 실제로 돌려 본다 (`run\pack.bat` 마지막 단계)
- `cs-api-diff/` — 두 FFXIVClientStructs 어셈블리의 API 차이. `sigs` 인자를 주면 시그니처 문자열과 필드 오프셋을 뽑는다
- `sig-probe/` — `ffxiv_dx11.exe`에서 시그니처를 해석한다. 우리가 박아 넣은 KR 시그니처가 아직 유일하게 잡히는지 테스트가 확인한다
- [`asmref-check/`](tools/asmref-check/README.md) — 플러그인 어셈블리가 부르는 타입·멤버가 KR이 깐 FFXIVClientStructs에 실제로 있는지 대조한다
- [`asmstr/`](tools/asmstr/README.md) — 어셈블리에 박힌 시그니처 문자열을 뽑는다. `#US` 힙(`ScanText`)과 `#Blob` 힙(`[Signature]` 특성) 양쪽

### 그 밖

- `docs/` — 조사·설계 문서. **`status.md`가 남은 일의 기준**
- `run/` — 실행 배치 (게임·빌드·검사·로그·동기화·용어·가이드·최초설정·배포)
- `.claude/skills/` — 프로젝트 스킬. 한국어화 규칙은 `ko-localization`이 갖는다
- `.claude/commands/` — 동기화 절차를 순서로 고정한 커맨드. `/ff_help`가 목록을 낸다

### 커맨드 (`/ff_`)

배치가 **한 가지 일**을 한다면, 커맨드는 **그 일들을 어떤 순서로 엮고 어디서 멈출지**를 갖는다. 절차는 `docs/`에 다 적혀 있는데 읽고 순서대로 실행하는 것은 매번 사람이 했고, 그 자리를 메운다.

- `/ff_help` — 목록. 손으로 적지 않고 `.claude/commands/`에서 만든다
- `/ff_sync check | up <태그> | notes | patches` — **위에서 오는 것.** 원본 모드 따라잡기
- `/ff_env check | dalamud | vnavmesh | game` — **아래에서 오는 것.** KR 달라무드·vnavmesh·게임 패치

**아래가 위보다 먼저다** ([upstream-sync.md](docs/upstream/sync.md) §9). 그리고 각 커맨드는 `## 멈추는 조건`을 갖는다 — 사람이 정할 것이 섞여 들어오면 커밋하지 않고 멈춘다.

## 클론 직후 한 번

git config core.hooksPath .githooks && git config commit.template .gitmessage && git submodule update --init && uv run --no-project --with pytest pytest tools -q

`vendor/`는 비공개 미러의 submodule이라 접근 권한이 있어야 받아진다. 못 받은 상태에서는 vendor가 필요한 검사가 건너뛰어진다 — 오류가 아니다.

빌드 환경 구성은 [docs/dev/environment.md](docs/dev/environment.md)를 본다. `DALAMUD_HOME`과 .NET SDK 경로에 함정이 있다.

## 라이선스

업스트림이 AGPL-3.0이고 Dalamud 자체도 AGPL-3.0이므로, 이 저장소의 산출물도 AGPL-3.0을 따를 예정이다. 현 단계는 문서와 저장소 도구뿐이라 아직 LICENSE 파일을 두지 않았다.

KR Dalamud 도구(`MiqoKR/*`)는 **재배포하지 않는다.** 라이선스가 명시돼 있지 않고, 사용자가 직접 받도록 안내만 한다.
