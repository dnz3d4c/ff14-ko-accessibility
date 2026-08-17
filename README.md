# ff14-ko-accessibility

FFXIV 글로벌 서버용 접근성 플러그인([derbruedi/ff14-accessibility](https://github.com/derbruedi/ff14-accessibility))을 한국 공식 서버 클라이언트에서 쓸 수 있게 포팅하는 작업의 저장소.

## 현재 상태: 환경 구축 완료, 구현 착수 전

플러그인 코드는 아직 없다. 지금 있는 것은 조사 문서와 저장소 설비다.

- **[한국 클라이언트 포팅 타당성 조사](docs/ko-client-port-feasibility.md)** — 2026-08-17
- **[개발 환경 실측과 설치 결과](docs/environment.md)** — 2026-08-17
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
- `vendor/ff14-accessibility/` — upstream 클론. **버전 관리에서 제외**된다. 직접 손대지 않고 `kr-port` 브랜치에 커밋한 뒤 패치로 떼어낸다. 채택 시 submodule로 전환한다.

아직 없는 것: `patches/`(업스트림 기여 대기 변경), `overlay/`의 데이터 자산(`ko.json` 등), `tests/`. 내용이 생길 때 만든다.

## 클론 직후 한 번

git config core.hooksPath .githooks && git config commit.template .gitmessage && uv run --no-project --with pytest pytest tools/commit-lint/tests -q

빌드 환경 구성은 [docs/environment.md](docs/environment.md)를 본다. `DALAMUD_HOME`과 .NET SDK 경로에 함정이 있다.

## 라이선스

업스트림이 AGPL-3.0이고 Dalamud 자체도 AGPL-3.0이므로, 이 저장소의 산출물도 AGPL-3.0을 따를 예정이다. 현 단계는 문서와 저장소 도구뿐이라 아직 LICENSE 파일을 두지 않았다.

KR Dalamud 도구(`MiqoKR/*`)는 **재배포하지 않는다.** 라이선스가 명시돼 있지 않고, 사용자가 직접 받도록 안내만 한다.
