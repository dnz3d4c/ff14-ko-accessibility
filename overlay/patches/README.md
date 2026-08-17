# overlay/patches

**한국 전용** 소스 패치. 업스트림에 올리지 않는다.

업스트림에 기여할 변경은 여기가 아니라 `patches/`에 둔다(아직 없음). 커밋 훅이 두 경로를 섞는 커밋을 거부한다 — 근거는 [docs/commit-rules.md](../../docs/commit-rules.md) §2.2.

## 왜 패치 파일인가

`vendor/ff14-accessibility/`는 업스트림 클론이고 **우리 저장소의 버전 관리 밖**이다(`.gitignore`). 거기에 직접 손대면 우리 저장소에 아무 기록도 남지 않고, 업스트림 태그를 올리는 순간 조용히 사라진다. 그래서 변경은 vendor 클론의 `kr-port` 브랜치에 커밋하고, `git format-patch`로 떼어내 여기에 둔다.

## 적용

vendor 클론에서 실행한다.

cd vendor/ff14-accessibility && git checkout -b kr-port main && git am ../../overlay/patches/*.patch

이미 `kr-port` 브랜치가 있으면 `git checkout kr-port`로 충분하다. 패치는 pristine `main`에 깨끗하게 적용되는 것을 확인해 두었다.

## 목록

### 0001 — ClientStructs 7.51에서 기어세트 마크 유지

업스트림이 부르는 `RaptureGearsetModule.IsItemRegisteredToGearset`이 CS 7.55.1.8875에는 있고 KR이 고정하는 7.51.0.8667에는 **없다.** 그래서 KR 참조로는 컴파일 자체가 안 된다(53,971줄 중 오류 1건).

확장 메서드로 메운다. C#은 인스턴스 메서드가 적용 가능하면 확장 메서드를 아예 후보에 넣지 않으므로, **7.55 빌드는 게임 함수를 그대로 부르고 이 파일을 참조조차 하지 않는다.** 전처리기 분기도, 호출부 수정도 없다.

바인딩은 추정이 아니라 실증했다 — 확장에 `[Obsolete(error: true)]`를 붙이면 7.55 빌드는 그대로 성공하고(확장 미바인딩), 7.51 빌드만 `InventoryService.cs:199`에서 CS0619로 실패한다(확장 바인딩).

**정밀도가 게임 답과 다르다.** 게임은 아이템 **인스턴스** 단위로 답하지만 기어세트는 아이템 id만 저장하므로 폴백은 **id 단위**로만 답한다. 같은 장비 두 개 중 하나만 등록돼 있어도 둘 다 표시된다. 업스트림이 `IsAnyCopyRegisteredToGearset`에서 이미 받아들인 오차 방향이고 이유도 같다 — "팔지 마라" 경고가 빠지는 쪽이 남는 쪽보다 비싸다.
