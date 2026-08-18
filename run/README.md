# run — 실행 배치

게임·모드·빌드·로그를 매번 손으로 붙여넣지 않기 위한 배치 파일. 탐색기에서 더블클릭하거나 Win+R에 전체 경로를 넣어 실행한다.

## 무엇을 언제 쓰나

| 파일 | 언제 | 게임 상태 |
|------|------|-----------|
| `play.bat` | **평소 실행.** 게임 켜고 → 로그인 → Dalamud 붙이기 | 꺼져 있어야 함 |
| `build.bat` | 소스를 고친 뒤 반영 | 켜져 있어도 됨 |
| `log.bat` | 이번 판이 정상인지 판정 | 아무 때나 |
| `sync.bat` | 업스트림이 앞서 갔는지 보고, 깨끗하면 올린다 | 아무 때나 |
| `terms.bat` | 게임이 쓰는 한국어 낱말 찾기 (sqpack 직독) | **꺼져 있어도 됨** |
| `setup.bat` | **최초 1회.** 프로필 부트스트랩 + 개발용 시딩 | **꺼져 있어야 함** |
| `pack.bat` | 남에게 줄 배포 폴더 만들기 (+ 낸 것을 다시 잰다) | 아무 때나 |
| `_env.cmd` | 직접 실행하지 않는다. 나머지가 경로를 얻는 곳 | — |

## 사람 없이 돌릴 때 — `FF14_NOPAUSE`

전부 끝에 `pause`가 있다. 탐색기에서 더블클릭하면 결과를 읽기 전에 창이 닫히기 때문이고, **스크린리더로 읽으려면 창이 살아 있어야 한다.**

그게 자동 실행에서는 반대로 걸린다 — 아무도 안 보는 창이 키 입력을 기다리며 영원히 멈춘다. `FF14_NOPAUSE`가 정의돼 있으면 `pause`를 건너뛴다. 값은 아무거나 좋다.

cmd //c "set FF14_NOPAUSE=1 && run\build.bat"

**종료 코드는 그대로다** — 0이 성공, 1이 실패. 멈추지 않는 대신 코드로 판정한다.

`sync.bat`은 인자 없이는 **아무것도 안 옮긴다** — 재기만 한다. 올릴 때는 태그를 손으로 적는다(`run\sync.bat v5.87`). 실수로 최신에 끌려가지 않게 하려는 것이고, 절차는 [docs/upstream-sync.md](../docs/upstream-sync.md).

`setup.bat`과 설치기 EXE는 비슷한 일을 하지만 **플러그인을 놓는 자리가 다르다.** `build.bat`·`setup.bat`은 개발용 자리(`devPlugins`)에, 설치기는 정식 자리(`installedPlugins`)에 놓는다. 둘은 **상호 배타적**이고 서로를 걷어낸다 — 같이 있으면 Dalamud가 같은 모드를 두 번 적재한다. 근거와 조건은 [docs/kr-runtime-setup.md](../docs/kr-runtime-setup.md) §7.

즉 **`build.bat`을 돌리면 그 머신은 개발 상태가 된다.** 배포 상태로 되돌리려면 `dist\FF14AccessibilityInstaller-KR.exe`를 다시 실행한다. 배포판을 인게임에서 검증하는 중이라면 그 사이에 `build.bat`을 돌리지 않는다.

`pack.bat`은 낸 것을 그대로 믿지 않는다. 3단계에서 `tools/pack-check`가 압축 내용을 규칙과 대조하고, 설치기를 **버리는 프로필 루트**에 대고 실제로 돌려 결과를 잰다.

`setup.bat`이 게임을 끈 상태를 요구하는 이유는 Dalamud가 **종료할 때 설정을 저장하기 때문**이다. 켜 놓고 심으면 조용히 덮인다.

`terms.bat`은 게임을 안 켜고 `game\sqpack`을 직접 읽는다. 그래서 한국어화 중에 "게임이 이걸 뭐라고 부르지"가 막힐 때 사용자를 기다릴 필요가 없다. 자세한 것은 [tools/ko-terms/README.md](../tools/ko-terms/README.md).

    run\terms.bat dump tools\ko-terms\out

## 경로를 박아 넣지 않는다

`_env.cmd`가 전부 환경변수에서 끌어낸다. 특히 **Dalamud hook 폴더는 이름이 버전이라 업데이터가 갱신할 때마다 바뀐다.** `docs/environment.md` §3이 "빌드가 갑자기 Dalamud 타입을 못 찾으면 여기부터 본다"고 적어 둔 함정이고, `_env.cmd`가 `Hooks` 아래에서 최신을 골라 그 손질을 없앤다.

## 인코딩 — 손대기 전에 읽는다

**배치 파일은 워킹트리에서 CP949다.** UTF-8로 저장하면 cmd가 한글 줄을 잘못 읽어 **주석이 아니라 코드까지 명령으로 실행된다**(2026-08-18 실측: `set "SCOOP=..."`가 `'coop"' is not recognized`로 깨졌다). BOM을 붙이면 첫 줄에서 오류가 난다.

저장소에는 UTF-8로 담긴다. `.gitattributes`의 `working-tree-encoding=CP949`가 체크아웃 때 변환하므로 **diff와 grep은 UTF-8 그대로 된다.**

에디터로 고칠 때는 CP949로 저장한다. UTF-8로 저장했다면 커밋 전에 되돌린다.

uv run --no-project python -c "import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_bytes(p.read_bytes().decode('utf-8').encode('cp949'))" run\build.bat

## 왜 dotnet 출력을 영어로 고정하나

`build.bat`이 `DOTNET_CLI_UI_LANGUAGE=en`을 건다. dotnet은 UTF-8로 출력하는데 콘솔은 CP949라 한국어 메시지가 깨져 나온다. **깨진 글자보다 영어가 낫다 — 스크린리더가 읽을 수 있다.**

## log.bat이 판정하는 것

`docs/kr-runtime-setup.md` §10의 판정을 `tools/kr-setup/check_log.py`가 대신 한다. 25만 자에서 다섯 줄을 눈으로 찾지 않기 위한 것이라 로그를 그대로 뱉지 않는다.

**마지막 세션만 본다.** 로그는 세션을 이어 붙이므로 앞판의 성공 줄이 이번 판의 실패를 가린다.
