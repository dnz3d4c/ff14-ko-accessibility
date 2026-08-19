# asmref-check

플러그인 DLL이 참조하는 멤버가 **한국판 Dalamud가 실제로 깔아 둔 어셈블리에 존재하는지**를 게임을 켜지 않고 판정한다.

한국판 Dalamud는 공식 15.0.3.2를 IL 패치한 것이고 FFXIVClientStructs를 7.55 계열에서 7.51로 낮춰 싣는다. 글로벌용으로 빌드된 서드파티 플러그인은 이 차이 때문에 **적재는 되는데 호출 시점에 MissingMethodException으로 죽을** 수 있다. 이 도구는 그 위험을 사전에 거른다.

## 판정하는 것과 못 하는 것

판정한다 — 어셈블리 메타데이터 수준의 바인딩. 플러그인의 TypeReference / MemberReference 테이블을 전수 열거해서, 참조하는 타입과 멤버가 실제 어셈블리에 이름·인자 개수·시그니처까지 맞게 있는지 본다. 즉 "적재와 JIT가 성립하는가"에 답한다.

판정하지 못한다 — 런타임 주소. FFXIVClientStructs는 멤버 함수 주소를 시그니처 스캔으로 잡고 필드 오프셋은 구조체 레이아웃에 박혀 있다. 클라이언트 바이너리가 다르면 메타데이터에 아무 흔적 없이 런타임에 틀린 주소가 나온다. **"잡은 주소가 맞는가"는 이 도구 밖이다.**

## 용법

**저장소 루트에서** 실행한다. 별도 빌드가 필요 없다 (`dotnet run`이 빌드까지 한다). `dotnet`은 절대 경로로 부른다 — 이유는 `docs/dev/environment.md` §2. 아래 복사용 명령은 **Git Bash 기준**이라 경로를 `$USERPROFILE`·`$APPDATA`로 적었고, 그 값은 백슬래시 경로로 그대로 확장된다.

$USERPROFILE\scoop\apps\dotnet-sdk\current\dotnet.exe run -c Release --project tools/asmref-check -- <플러그인DLL> <참조어셈블리디렉토리>

특정 어셈블리만 보려면 뒤에 `--only FFXIVClientStructs` 또는 쉼표로 여러 개를 붙인다. 어셈블리별 검사 건수를 따로 뽑을 때 쓴다.

참조 어셈블리 디렉토리는 KR Dalamud의 Hooks 디렉토리다.

%APPDATA%\XIVLauncherKR\addon\Hooks\15.0.3.2

## 검사 대상 선정

참조 디렉토리에 같은 이름의 `.dll`이 있는 어셈블리만 본다. BCL(`System.*`)은 거기 없으니 자동으로 빠진다.

플러그인이 자기 디렉토리에 사본을 들고 오는 의존성도 뺀다. Dalamud 플러그인 로더가 플러그인 디렉토리를 먼저 보기 때문에 런타임엔 그 사본이 쓰이고, Hooks 쪽 버전과 대조하면 헛경보가 난다. vnavmesh의 Newtonsoft.Json이 양쪽에 다 있는 실제 사례다.

단 플러그인이 참조 디렉토리 **안에** 있으면(자기 정합성 검사) 사본이란 개념이 없으므로 이 배제를 끈다. `--only`를 주면 배제 규칙보다 우선한다.

## 판정 종류

| 판정 | 뜻 |
|------|-----|
| `MISSING TYPE` | 타입 자체가 없다. 그 타입을 쓴 멤버 이름을 같이 찍는다 |
| `MISSING MEMBER` | 타입은 있는데 그 이름의 멤버가 하나도 없다 |
| `ARITY MISMATCH` | 이름은 있는데 인자 개수가 맞는 오버로드가 없다. 기대 개수와 실제 후보 개수를 같이 찍는다 |
| `SIGNATURE DIFF` | 이름·개수는 맞는데 파라미터 타입이나 반환 타입이 다르다. **경고** |

출력은 어셈블리별로 묶고 헤더에 참조 버전과 실제 버전을 같이 찍는다. 문제 없으면 `(no issues)`, 마지막에 `SUMMARY` 한 줄.

## 종료 코드

| 코드 | 조건 |
|------|------|
| 0 | 문제 없음, 또는 `SIGNATURE DIFF`만 있음 |
| 1 | `MISSING TYPE` / `MISSING MEMBER` / `ARITY MISMATCH`가 하나라도 있음 |
| 2 | 인자 부족 (용법 오류) |

`SIGNATURE DIFF`를 0으로 두는 이유: 바인딩을 실제로 깨뜨리는 건 타입·멤버 부재와 인자 개수 불일치다. 시그니처 문자열 차이는 이 도구의 짧은 이름 비교가 만들어내는 잡음일 수 있어 사람이 보고 판단할 몫으로 남긴다.

## 교정 (calibration)

이 도구는 **오탐이 없다는 게 증명되지 않으면 쓸모가 없다.** 전부 통과로 나올 때 그게 진짜 안전인지 도구가 조용한 건지 구분이 안 되기 때문이다. 그래서 성질을 아는 대조군 2건을 먼저 돌린다. 도구를 고친 뒤에는 반드시 둘 다 다시 돌린다. 저장소 루트에서 한 줄로 둘 다 돌아간다.

DN="$USERPROFILE\scoop\apps\dotnet-sdk\current\dotnet.exe"; R="$APPDATA\XIVLauncherKR\addon\Hooks\15.0.3.2"; "$DN" run -c Release --project tools/asmref-check -- "$APPDATA\XIVLauncherKR\devPlugins\FF14Accessibility\FF14Accessibility.dll" "$R" && "$DN" run -c Release --project tools/asmref-check -- "$R\Dalamud.dll" "$R"

**(a) FF14Accessibility.dll** — 참조 디렉토리는 KR Hooks.

%APPDATA%\XIVLauncherKR\devPlugins\FF14Accessibility\FF14Accessibility.dll

이 DLL은 **한국 클라이언트 실기에서 적재·동작이 이미 증명됐다.** 따라서 여기서 MISSING이나 ARITY가 나오면 그건 진짜 결함이 아니라 도구의 오탐이다. 기대값은 906 checked, 전 항목 0.

**(b) Hooks 디렉토리의 Dalamud.dll을 같은 디렉토리에 대고 검사** — 자기 정합성.

어셈블리가 자기가 함께 배포된 의존성을 못 찾을 리 없으므로, 여기서 나오는 것도 전부 오탐이다. (a)보다 표본이 4배 크고(3763 checked) 무엇보다 **Dalamud.dll 자신이 FFXIVClientStructs 7.55.1.8875를 참조하는데 실제로 깔린 건 7.51.0.8667이다** — 7.55→7.51 다운그레이드를 가로지르는 3763건이 전부 해석되는지 보는 것이라 이 프로젝트의 관심사와 정확히 겹친다.

교정에서 실제로 잡아낸 오탐 2건:

- 플러그인 디렉토리 == 참조 디렉토리일 때 자기 번들 배제 규칙이 참조 디렉토리 전체를 배제해 `0 checked`가 됐다. (b)가 아니었으면 못 잡는다.
- 함수 포인터 타입에서 리플렉션 쪽 `Type.Name`이 빈 문자열이라 88건이 가짜 `SIGNATURE DIFF`로 잡혔다. ClientStructs의 `*VirtualTable` / `MemberFunctionPointers`가 전부 이 형태다.

## 탐지기가 살아 있는지 확인 (음성 대조군)

교정은 오탐이 없음을 보이지만 탐지기가 **울리기는 하는지**는 안 보여준다. 검사 결과가 전부 0으로 나올 때 그게 "문제 없음"인지 "도구가 안 돈다"인지 구분하려면 반대 방향의 대조군이 필요하다. 그래서 `tests/`에 멤버를 일부러 뺀 어셈블리 두 판을 두고 실제로 돌린다.

- `tests/v1/` — 구판. `tests/client/`가 이걸 보고 컴파일된다.
- `tests/v2/` — 신판. `Gone` 타입 삭제, `Foo.Baz` 필드 삭제, `Foo.Bar` 인자 1→2, `Foo.Keep` 인자 `string`→`object`. `Foo.Ptr`(포인터 인자)와 `Nest.Inner.Deep`(중첩 타입)은 안 건드린다.
- `tests/client/` — v1으로 컴파일해 참조 테이블만 뽑아낸다. 실행하지 않는다.

저장소 루트에서 한 줄로 돌린다.

DN="$USERPROFILE\scoop\apps\dotnet-sdk\current\dotnet.exe"; T=tools/asmref-check/tests; "$DN" build -c Release -v q --nologo $T/v1 && "$DN" build -c Release -v q --nologo $T/client && "$DN" build -c Release -v q --nologo $T/v2 && "$DN" run -c Release --project tools/asmref-check -- $T/client/bin/Release/net10.0/Client.dll $T/v2/bin/Release/net10.0 --only StubLib

2026-08-18 실측 출력이다. 도구를 고친 뒤에는 교정 2건과 함께 이걸 다시 돌려 아래와 같은지 본다.

```
# StubLib ref=1.0.0.0 actual=1.0.0.0
  MISSING TYPE    Stub.Gone    members: Poof
  MISSING MEMBER  Stub.Foo.Baz    want field Int32
  ARITY MISMATCH  Stub.Foo.Bar    want 1 params [Void Bar(Int32)]    actual [2]
  SIGNATURE DIFF  Stub.Foo.Keep    ref: Void Keep(String)    actual: Void Keep(Object)

SUMMARY: 7 checked, 1 missing-type, 1 missing-member, 1 arity, 1 sig-diff
```

종료 코드는 1이다. 4종이 각각 한 건씩 울리고, 안 바꾼 `Foo.Ptr`와 `Nest.Inner.Deep`은 조용하다 — 즉 무조건 울리는 것도 아니다. `--only`를 쓰는 이유는 client 디렉토리에 StubLib 사본이 복사되기 때문이다. 자기 번들 배제 규칙에 걸리는 걸 `--only`가 덮는다.

검사 결과를 0건으로 보고할 때는 이 대조군을 같이 돌린 사실을 붙인다.
