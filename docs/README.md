# 문서 지도

무엇이 어디 있는지. **남은 일은 여기가 아니라 [현황판](status.md)이 갖는다.**

## 먼저 여는 것

- [status.md](status.md) — **현황판.** 기능 구현·수정·개선을 시작하기 전에 여기부터 연다. 남은 일도, 알려진 결함도, 사용자 판단을 기다리는 것도 전부 여기 있다. 다른 문서는 근거만 갖는다

## dev/ — 세우고 만드는 것

- [environment.md](dev/environment.md) — 경로·버전·빌드 함정. KR 클라이언트와 글로벌이 갈리는 자리
- [kr-runtime.md](dev/kr-runtime.md) — KR 실행 환경을 손으로 세우는 절차. 설치 프로그램이 이 절차를 대신한다
- [release.md](dev/release.md) — **내는 절차.** 릴리스 자산, 태그 규약, 그리고 **공개 전환과 첫 릴리스의 순서.** 순서를 틀리면 오류가 안 나고 받는 사람 화면에서만 이상해진다
- [commit-rules.md](dev/commit-rules.md) — 커밋 갈래와 트레일러, 검사기가 막는 것

## korean/ — 한국어로 옮기는 것

- [keys.md](korean/keys.md) — 키를 두고 **실측하거나 판정한 것.** KR에서 겹치는 키, 지금 안 되는 키와 원인, 게임 자체 메뉴가 받는 입력이다. **키 목록 자체는 여기 없다** — [사용 안내](../overlay/ko/README.ko.md) 4장이 갖고 `tools/docs-check`가 소스와 대조한다
- [hand-cases.md](korean/hand-cases.md) — 생성기가 못 읽는 문장 모양과 옮길 때 조심할 것
- [guide-corpus.md](korean/guide-corpus.md) — 파판14 공식 가이드 코퍼스. 무엇을 받아 뒀고 어떻게 찾나

## upstream/ — 위에서 오는 것

- [sync.md](upstream/sync.md) — 핀을 옮기는 절차
- [changes.md](upstream/changes.md) — 업스트림 변경 이력. 원문이 독일어라 한국어로 옮겨 둔다
- [vendor.md](upstream/vendor.md) — vendor가 왜 submodule인가

## frozen/ — 그때 그대로 두는 것

**여기 둘은 지금 값으로 맞추지 않는다.** 쓰인 시점의 판단과 숫자를 그대로 갖는 것이 이 문서들의 쓸모다. 실제와 어긋나 보여도 고칠 대상이 아니다.

- [port-feasibility.md](frozen/port-feasibility.md) — 착수 전 타당성 조사 (2026-08-17)
- [ko-review-2026-08-18.md](frozen/ko-review-2026-08-18.md) — 한국어 전수 검수 기록 (2026-08-18)

## 이 폴더 밖에 있는 문서

- [../README.md](../README.md) — 프로젝트 안내. 모드가 무엇을 하고, 무엇 위에 서 있고, 어떻게 기여하나
- [../overlay/ko/README.ko.md](../overlay/ko/README.ko.md) — **사용자가 읽는 문서.** 배포물에 `사용 안내.md`로 나간다
- [../patches/README.md](../patches/README.md) — 업스트림에 보낼 것의 기준과 기록
- [../overlay/patches/README.md](../overlay/patches/README.md) — 한국 전용 변경의 명세
- [../run/README.md](../run/README.md) — 실행 배치

## 왜 이렇게 나눴나

전에는 문서 열둘이 `docs/` 밑에 평평하게 깔려 있었고, 이름 접두가 `ko-`·`upstream-`·없음으로 세 갈래였다. **찾으려면 이름을 이미 알아야 했다.**

가른 기준은 둘이다.

- **언제 여는가** — 환경을 세울 때(`dev/`), 문장을 옮길 때(`korean/`), 업스트림을 따라잡을 때(`upstream/`)
- **고쳐야 하는가** — `frozen/`은 안 고치고 나머지는 실제와 어긋나면 고친다. 전에는 동결 기록과 살아 있는 절차가 같은 자리에 섞여 있어서, 낡은 것인지 틀린 것인지 열어 보기 전에는 알 수 없었다

**폴더가 갈래를 말하므로 파일 이름에서 접두를 뺐다.** `ko-hand-cases.md`는 `korean/hand-cases.md`가 됐다. 날짜가 박힌 기록만 이름에 날짜를 남긴다 — 그것이 동결이라는 표시다.

**`status.md`는 안 옮겼다.** 커밋 검사기(`tools/commit-lint`의 C8)가 이 경로를 문자열로 비교하는데, 그 비교는 파일이 있는지를 보지 않는다. 옮기고 상수를 놓치면 **오류 없이 규칙이 영원히 통과한다** — 이 저장소가 `tools/docs-check`를 만든 이유인 "조용히 낡는" 실패와 같은 모양이다. 현황판은 제일 자주 여는 문서이기도 해서 한 단계 얕은 자리가 맞다.
