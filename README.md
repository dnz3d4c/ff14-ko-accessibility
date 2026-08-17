# ff14-ko-accessibility

FFXIV 글로벌 서버용 접근성 플러그인([derbruedi/ff14-accessibility](https://github.com/derbruedi/ff14-accessibility))을 한국 공식 서버 클라이언트에서 쓸 수 있게 포팅하는 작업의 저장소.

## 현재 상태: KR 실기 동작, 번역 착수 직전

업스트림 플러그인이 한국 클라이언트에서 **실제로 돌아간다.** 캐릭터 생성·창 읽기·채팅·NPC 대화가 되고, **자동 이동도 대상 지정부터 도착 안내까지 인게임에서 확인됐다.** 한국어화는 아직 시작 전이다 — 모드 안내 음성은 여전히 영어다.

KR 전용 결함과 "게임과 답이 다른 두 곳"은 정리했고, 설치기를 KR용으로 돌려 **폴더에 손으로 넣고 빼는 절차를 없앴다.** 업스트림에 보낼 수 있는 수정도 하나 나왔다(타이틀 메뉴 항목 수).

**남은 일은 전부 [프로젝트 현황판](docs/status.md)에 있다.** 뭘 고치기 전에 거기를 먼저 연다.

- **[프로젝트 현황판](docs/status.md)** — 남은 일의 기준
- **[한국 클라이언트 포팅 타당성 조사](docs/ko-client-port-feasibility.md)** — 2026-08-17
- **[개발 환경 실측과 설치 결과](docs/environment.md)** — 2026-08-17
- **[KR 실행 환경 구축 절차](docs/kr-runtime-setup.md)** — 2026-08-17
- **[단축키 한국어 표](docs/keys-ko.md)** — 2026-08-17
- **[커밋 규칙](docs/commit-rules.md)** — 2026-08-17
- **[손으로 옮겨야 하는 40곳](docs/ko-hand-cases.md)** — 2026-08-18

### 조사 결론 요약

- 플러그인 소스에 리전 제한은 **없다.** 업스트림이 독일 클라이언트로만 개발·테스트했을 뿐이다.
- 실제 장벽은 그 아래 Dalamud 계층이고, 한국 서버용 Dalamud 배포 파이프라인이 제3자에 의해 이미 존재한다.
- 권장 경로는 fork가 아니라 **업스트림엔 언어 일반화를 보내고, KR 전용은 얇게 따로 두는 것**이다.

### 환경 구축에서 새로 확인한 것

- 설치된 KR 클라이언트 버전 `2026.08.05.0000.0000`이 KR Dalamud 지원 버전과 **정확히 일치**한다.
- KR 호환 Dalamud(공식 15.0.3.2 + KR IL 패치, FFXIVClientStructs 7.51.0.8667)를 구성하고 자체 검증까지 통과했다.
- **업스트림 소스를 KR 호환 CS로 빌드했을 때 오류가 정확히 1건이었다** — 53,971줄에서 `RaptureGearsetModule.IsItemRegisteredToGearset` 하나. 확장 메서드 shim으로 메웠고(`overlay/patches/0001`), **글로벌 빌드의 바인딩은 바뀌지 않는다**(실증 완료). 지금은 양쪽 다 경고 0 오류 0으로 빌드된다.
- 게임 `sqpack`이 있으므로 조사 §7의 1순위 미확인 항목(KR Addon 시트 행 ID)을 **게임 실행 없이 Lumina로 확인할 수 있다.**

## 매일 쓰는 것

게임과 모드를 켜는 것부터 로그 판정까지 배치가 갖고 있다. 자세한 건 [run/README.md](run/README.md).

C:\project\games\ff14-ko-accessibility\run\play.bat

남은 일은 전부 **[프로젝트 현황판](docs/status.md)** 에 있다. 뭘 고치기 전에 거기를 먼저 연다.

## 구조

- `docs/` — 조사·설계 문서. **`status.md`가 남은 일의 기준**
- `run/` — 실행 배치 (게임·빌드·로그·최초설정)
- `overlay/patches/` — **한국 전용** 소스 패치. vendor 클론의 `kr-port` 브랜치에서 뽑아낸다
- `patches/` — **업스트림에 보낼** 변경. `overlay/`보다 **먼저** 적용된다
- `.claude/skills/` — 프로젝트 스킬. 한국어화 규칙은 `ko-localization`이 갖는다
- `tools/commit-lint/` — 커밋 메시지 검증기 (`.githooks/commit-msg`가 호출, 규칙 C1~C8)
- `tools/patch-check/` — 패치가 순서대로 붙고 vendor와 어긋나지 않았는지 (`.githooks/pre-commit`이 개수만, `run\check.bat`이 전체)
- `tools/strings-golden/` — 한국어화 전 독일어·영어 675쌍 스냅샷. 옮기다 건드리면 빨개진다
- `tools/kr-setup/` — KR 프로필에 dev 플러그인을 심는 스크립트
- `tools/cs-api-diff/` — 두 FFXIVClientStructs 어셈블리의 API 차이를 뽑는 도구 (`sigs` 인자를 주면 시그니처 문자열과 필드 오프셋을 뽑는다)
- `tools/sig-probe/` — 게임을 켜지 않고 `ffxiv_dx11.exe`에서 시그니처를 해석하는 검증기. 우리가 박아 넣은 KR 시그니처가 아직 유일하게 잡히는지 테스트가 확인한다
- `tools/asmref-check/` — 플러그인 어셈블리가 부르는 타입·멤버가 KR이 깐 FFXIVClientStructs에 실제로 있는지 대조하는 도구. 게임을 켜지 않고 돌린다
- `tools/asmstr/` — 어셈블리에 박힌 시그니처 문자열을 뽑는다. `#US` 힙(`ScanText`)과 `#Blob` 힙(`[Signature]` 특성) 양쪽을 읽고, 뽑은 것은 `sig-probe`로 해석한다
- `vendor/ff14-accessibility/` — upstream 클론. **버전 관리에서 제외**된다. 직접 손대지 않고 `kr-port` 브랜치에 커밋한 뒤 패치로 떼어낸다. 채택 시 submodule로 전환한다.

아직 없는 것: `overlay/`의 데이터 자산(`ko.json` 등). 한국어화를 시작할 때 생긴다.

## 클론 직후 한 번

git config core.hooksPath .githooks && git config commit.template .gitmessage && uv run --no-project --with pytest pytest tools -q

빌드 환경 구성은 [docs/environment.md](docs/environment.md)를 본다. `DALAMUD_HOME`과 .NET SDK 경로에 함정이 있다.

## 라이선스

업스트림이 AGPL-3.0이고 Dalamud 자체도 AGPL-3.0이므로, 이 저장소의 산출물도 AGPL-3.0을 따를 예정이다. 현 단계는 문서와 저장소 도구뿐이라 아직 LICENSE 파일을 두지 않았다.

KR Dalamud 도구(`MiqoKR/*`)는 **재배포하지 않는다.** 라이선스가 명시돼 있지 않고, 사용자가 직접 받도록 안내만 한다.
