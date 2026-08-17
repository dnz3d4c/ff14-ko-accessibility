# ff14-ko-accessibility

FFXIV 글로벌 서버용 접근성 플러그인([derbruedi/ff14-accessibility](https://github.com/derbruedi/ff14-accessibility))을 한국 공식 서버 클라이언트에서 쓸 수 있게 포팅하는 작업의 저장소.

## 현재 상태: KR 실기에서 동작 확인, 캐릭터 생성 완료

업스트림 플러그인이 한국 클라이언트에서 **실제로 돌아간다.** KR 전용 결함 3건을 고쳐 캐릭터 생성까지 마쳤다. 한국어화는 아직 시작 전이다 — 모드 안내 음성은 여전히 영어다.

그 뒤에 남아 있던 **"게임과 답이 다른 두 곳"을 정리했다.** 노드 가시성은 KR 바이너리에서 게임 함수를 찾아내 되돌렸고(추론이던 부모 사슬 판정을 폐기), 기어세트 마크의 id 단위 오차는 유지하되 기동 시 음성으로 알린다. 근거는 [개발 환경 문서](docs/environment.md) §5~6.

자동 이동에 필요한 **vnavmesh를 설치하고 사전 검증까지 통과시켰다.** 접근성 모드가 요구하는 외부 플러그인은 이것 하나뿐이다(IPC 호출 16건 전수). 게임을 켜지 않고 어셈블리 참조·멤버 참조·시그니처를 검사해 미해결 0건을 확인했다 — [개발 환경 문서](docs/environment.md) §7. **인게임 적재는 아직 확인 못 했다.** 키를 사람이 눌러야 하기 때문이고, 판정 방법은 [KR 실행 환경 구축 절차](docs/kr-runtime-setup.md) §10에 적어 뒀다.

- **[한국 클라이언트 포팅 타당성 조사](docs/ko-client-port-feasibility.md)** — 2026-08-17
- **[개발 환경 실측과 설치 결과](docs/environment.md)** — 2026-08-17
- **[KR 실행 환경 구축 절차](docs/kr-runtime-setup.md)** — 2026-08-17
- **[단축키 한국어 표](docs/keys-ko.md)** — 2026-08-17
- **[커밋 규칙](docs/commit-rules.md)** — 2026-08-17

### 조사 결론 요약

- 플러그인 소스에 리전 제한은 **없다.** 업스트림이 독일 클라이언트로만 개발·테스트했을 뿐이다.
- 실제 장벽은 그 아래 Dalamud 계층이고, 한국 서버용 Dalamud 배포 파이프라인이 제3자에 의해 이미 존재한다.
- 권장 경로는 fork가 아니라 **로케일 일반화 업스트림 기여 + 얇은 KR 오버레이**다.

### 환경 구축에서 새로 확인한 것

- 설치된 KR 클라이언트 버전 `2026.08.05.0000.0000`이 KR Dalamud 지원 버전과 **정확히 일치**한다.
- KR 호환 Dalamud(공식 15.0.3.2 + KR IL 패치, FFXIVClientStructs 7.51.0.8667)를 구성하고 자체 검증까지 통과했다.
- **업스트림 소스를 KR 호환 CS로 빌드했을 때 오류가 정확히 1건이었다** — 53,971줄에서 `RaptureGearsetModule.IsItemRegisteredToGearset` 하나. 확장 메서드 shim으로 메웠고(`overlay/patches/0001`), **글로벌 빌드의 바인딩은 바뀌지 않는다**(실증 완료). 지금은 양쪽 다 경고 0 오류 0으로 빌드된다.
- 게임 `sqpack`이 있으므로 조사 §7의 1순위 미확인 항목(KR Addon 시트 행 ID)을 **게임 실행 없이 Lumina로 확인할 수 있다.**

## 구조

- `docs/` — 조사·설계 문서
- `overlay/patches/` — **한국 전용** 소스 패치. vendor 클론의 `kr-port` 브랜치에서 뽑아낸다
- `tools/commit-lint/` — 커밋 메시지 검증기 (`.githooks/commit-msg`가 호출)
- `tools/kr-setup/` — KR 프로필에 dev 플러그인을 심는 스크립트
- `tools/cs-api-diff/` — 두 FFXIVClientStructs 어셈블리의 API 차이를 뽑는 도구 (`sigs` 인자를 주면 시그니처 문자열과 필드 오프셋을 뽑는다)
- `tools/sig-probe/` — 게임을 켜지 않고 `ffxiv_dx11.exe`에서 시그니처를 해석하는 검증기. 우리가 박아 넣은 KR 시그니처가 아직 유일하게 잡히는지 테스트가 확인한다
- `tools/asmref-check/` — 플러그인 어셈블리가 부르는 타입·멤버가 KR이 깐 FFXIVClientStructs에 실제로 있는지 대조하는 도구. 게임을 켜지 않고 돌린다
- `tools/asmstr/` — 어셈블리에 박힌 시그니처 문자열을 뽑는다. `#US` 힙(`ScanText`)과 `#Blob` 힙(`[Signature]` 특성) 양쪽을 읽고, 뽑은 것은 `sig-probe`로 해석한다
- `vendor/ff14-accessibility/` — upstream 클론. **버전 관리에서 제외**된다. 직접 손대지 않고 `kr-port` 브랜치에 커밋한 뒤 패치로 떼어낸다. 채택 시 submodule로 전환한다.

아직 없는 것: `patches/`(업스트림 기여 대기 변경), `overlay/`의 데이터 자산(`ko.json` 등), `tests/`. 내용이 생길 때 만든다.

## 클론 직후 한 번

git config core.hooksPath .githooks && git config commit.template .gitmessage && uv run --no-project --with pytest pytest tools/commit-lint/tests -q

빌드 환경 구성은 [docs/environment.md](docs/environment.md)를 본다. `DALAMUD_HOME`과 .NET SDK 경로에 함정이 있다.

## 라이선스

업스트림이 AGPL-3.0이고 Dalamud 자체도 AGPL-3.0이므로, 이 저장소의 산출물도 AGPL-3.0을 따를 예정이다. 현 단계는 문서와 저장소 도구뿐이라 아직 LICENSE 파일을 두지 않았다.

KR Dalamud 도구(`MiqoKR/*`)는 **재배포하지 않는다.** 라이선스가 명시돼 있지 않고, 사용자가 직접 받도록 안내만 한다.
