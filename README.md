# FF14 접근성 모드 (한국 서버)

파이널 판타지 14를 한국 서버에서 시각장애인이 스크린 리더로 플레이할 수 있게 합니다. [원본 접근성 모드](https://github.com/derbruedi/ff14-accessibility)에 한국 서버용 패치를 얹은 것입니다.

- **받는 곳** — [최신 릴리스](https://github.com/dnz3d4c/ff14-ko-accessibility/releases/latest)
- **설치 및 사용방법** — [사용 안내](overlay/ko/README.ko.md)
- **프로젝트 현황** — [현황판](docs/status.md)
- **프로젝트 문서 읽는법** — [문서 지도](docs/README.md)
- **개발 참여** — [개발 안내](docs/dev/README.md)

## 1. 이 모드가 하는 일

모드가 만든 안내 메시지는 NVDA가 음성 및 점자로 처리합니다. 메뉴와 창, 로그와 대화, 이동과 길안내, 전투, 소지품과 장비, 단축바를 음성 출력합니다. 인게임 내 메시지(NPC 이름, 대사, 메뉴, 아이템 이름)은 한국어로 출력되며, 모드가 손대지 않습니다.

모드 기능과 단축키, 명령어는 [사용 안내](overlay/ko/README.ko.md) 4장과 5장에 있습니다. 키만 한자리에 모은 것은 [단축키 목록](overlay/ko/KEYS.ko.md)입니다.

## 2. 한국 서버 모드가 원본 모드와 다른 점

- 원본 모드는 독일어로 개발되고 글로벌 클라이언트를 전제로 합니다. 한국 서버 모드는 파이널 판타지 14 한국 서버에서 동작하도록 수정되었습니다.
- **모드 안내 메시지가 한국어로 출력됩니다.**
- **공식 파이널 판타지 14 런처와 한국 서버용으로 포팅된 Dalamud를 사용합니다**
- **방향 안내를 켜고 끄는 `N`이 한국 클라이언트에서는 제작수첩을 여는 키와 같습니다.** 한국 서버에만 있는 결함이고, 원본과 함께 겪는 결함이 둘 더 있습니다. 증상과 우회 방법은 [사용 안내](overlay/ko/README.ko.md) 6장에 있습니다

이 외 동작은 원본 모드와 같습니다.

## 3. 함께 필요한 것

**한국 서버는 한국 전용 계정을 사용합니다.** 글로벌 서버 계정으로는 접속할 수 없습니다. 계정을 만드는 방법은 [사용 안내](overlay/ko/README.ko.md) 1장 2절에 있습니다.

**Microsoft .NET 10 Desktop Runtime x64가 필요합니다.** 없으면 모드가 동작하지 않습니다. 아래 주소를 클릭하면 설치 파일 내려받기가 바로 시작됩니다. 이미 설치되어 있는지 확인하는 방법은 [사용 안내](overlay/ko/README.ko.md) 1장 3절에 있습니다.

https://aka.ms/dotnet/10.0/windowsdesktop-runtime-win-x64.exe

**KR Dalamud 업데이터와 vnavmesh는 설치 프로그램이 해당 프로그램의 저장소에서 직접 내려받으며**, 내려받을지 묻는 대화상자가 표시됩니다. 이 저장소에서 재배포하지 않습니다.

- **[KR Dalamud 업데이터](https://github.com/MiqoKR/kr-dalamud-updater)** — 게임에 Dalamud를 사용할 수 있게 해주는 프로그램입니다. 프로그램이 없으면 모드가 실행되지 않습니다
- **[vnavmesh](https://github.com/awgil/ffxiv_navmesh)** — 자동 이동, 따라가기, 경로 미리 듣기에 필요합니다. 설치하지 않아도 나머지 모드 기능은 그대로 동작합니다

## 4. 기능 제안과 문제 신고

- 한국어 번역, 설치 프로그램 **한국 서버와 관련된 내용**은 [이 저장소의 이슈](https://github.com/dnz3d4c/ff14-ko-accessibility/issues)에 남길 수 있습니다
- 모드의 새 기능 제안, 원본 모드에서 나타나는 문제는 [원본 저장소의 이슈](https://github.com/derbruedi/ff14-accessibility/issues)에 올려주세요. 어느 쪽에 올릴지 모르겠다면 이 저장소에 올려주세요.

문제를 남길 때 다음이 함께 있으면 원인을 찾는 데 도움이 됩니다.

- 인게임에서 `Ctrl+F5`로 바탕 화면에 저장한 창 구조 파일
- 바탕 화면의 `FFXIV_Keybinds.txt`
- 어떤 음성이 들렸고 어떻게 동작하길 기대하는지


## 5. 라이선스

이 모드는 **GNU Affero General Public License, Version 3**을 따릅니다. 원본 모드와 Dalamud, goatcorp의 공식 플러그인 서식도 모두 같은 라이선스입니다. 전문은 저장소의 [LICENSE](LICENSE)에 있습니다.

배포물에 함께 포함된 제3자 소프트웨어는 **Tolk**(LGPL-3.0), **NVDA Controller Client**(LGPL-2.1), **NAudio**(MIT)입니다. 각각의 라이선스는 `FF14Accessibility.zip` 안의 `THIRD-PARTY-NOTICES.md`에 있고, **재배포할 때 이 파일이 함께 있어야 합니다.**

## 6. 만든 사람들

- **원본 접근성 모드** — [derbruedi](https://github.com/derbruedi)가 만들고 있습니다. 기여자 목록은 [원본 저장소](https://github.com/derbruedi/ff14-accessibility)에 있습니다
- **한국 서버 모드** — [dnz3d4c](https://github.com/dnz3d4c)
