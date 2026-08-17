# ff14-ko-accessibility

FFXIV 글로벌 서버용 접근성 플러그인([derbruedi/ff14-accessibility](https://github.com/derbruedi/ff14-accessibility))을 한국 공식 서버 클라이언트에서 쓸 수 있게 포팅하는 작업의 저장소.

## 현재 상태: 조사 단계 (구현 착수 전)

코드는 아직 없다. 지금 있는 것은 타당성 조사 보고서 하나다.

- **[한국 클라이언트 포팅 타당성 조사](docs/ko-client-port-feasibility.md)** — 2026-08-17

### 조사 결론 요약

- 플러그인 소스에 리전 제한은 **없다.** 업스트림이 독일 클라이언트로만 개발·테스트했을 뿐이다.
- 실제 장벽은 그 아래 Dalamud 계층이고, 한국 서버용 Dalamud 배포 파이프라인이 제3자에 의해 이미 존재한다.
- 권장 경로는 fork가 아니라 **로케일 일반화 업스트림 기여 + 얇은 KR 오버레이**다.
- 구현 착수 전에 한국 클라이언트 실기 증거가 필요하다. 상세는 보고서 §14.

## 구조

- `docs/` — 조사·설계 문서
- `vendor/ff14-accessibility/` — upstream 클론. **읽기 전용 참조이며 버전 관리에서 제외**된다. 채택 시 submodule로 전환한다.

## 라이선스

업스트림이 AGPL-3.0이고 Dalamud 자체도 AGPL-3.0이므로, 이 저장소의 산출물도 AGPL-3.0을 따를 예정이다. 현 단계는 문서뿐이라 아직 LICENSE 파일을 두지 않았다.
