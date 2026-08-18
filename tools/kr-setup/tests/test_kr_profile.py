"""프로필 루트를 어디서 얻는가.

막는 사고는 하나다 - **우리가 넣은 곳과 업데이터가 보는 곳이 갈리는 것.**
갈리면 오류가 안 난다. 업데이터가 자기 기본값으로 빈 프로필을 새로 만들어
거기 주입하고, 플러그인만 조용히 빠진다.

전에는 세 군데가 각자 `XIVLauncherKR`을 박아 뒀다(설치기·`_env.cmd`·
`check_log.py`). 셋이 서로 맞는지도, 업데이터의 실제 설정과 맞는지도 아무도
안 봤다. 권위는 `%APPDATA%\\KrDalamudUpdater\\settings.json`의 `ProfileRoot`고,
그건 `README-KR.txt`가 "사용자 설정"이라고 못박은 값이다 - 사용자가 바꾼다.
"""

import json

import kr_profile
import pytest


@pytest.fixture
def env(tmp_path, monkeypatch):
    """APPDATA를 임시 폴더로 돌리고 우리 override는 지운 상태."""
    appdata = tmp_path / "Roaming"
    appdata.mkdir()
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.delenv(kr_profile.ROOT_OVERRIDE_VARIABLE, raising=False)
    return appdata


def write_settings(appdata, value, *, raw=None):
    path = appdata / "KrDalamudUpdater" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if raw is not None:
        path.write_text(raw, encoding="utf-8")
    else:
        path.write_text(json.dumps({"ProfileRoot": value}), encoding="utf-8")
    return path


# --- 권위를 읽는다 ---------------------------------------------------------


def test_업데이터_설정을_읽는다(env):
    write_settings(env, r"D:\ffxiv\profile")
    assert kr_profile.resolve_root() == r"D:\ffxiv\profile"


def test_설정값의_환경변수를_펼친다(env):
    # 업데이터가 실제로 이 모양으로 저장한다 - 실측값이 "%APPDATA%\XIVLauncherKR"다.
    write_settings(env, r"%APPDATA%\XIVLauncherKR")
    assert kr_profile.resolve_root() == str(env / "XIVLauncherKR")


def test_설정이_없으면_기본값(env):
    assert kr_profile.resolve_root() == str(env / "XIVLauncherKR")


# --- 우리 탈출구가 제일 세다 -----------------------------------------------


def test_환경변수_override가_설정을_이긴다(env, monkeypatch):
    write_settings(env, r"D:\ffxiv\profile")
    monkeypatch.setenv(kr_profile.ROOT_OVERRIDE_VARIABLE, r"E:\test")
    assert kr_profile.resolve_root() == r"E:\test"


# --- 남의 파일이 깨져도 우리가 안 죽는다 -----------------------------------


def test_설정이_깨진_JSON이면_기본값(env):
    write_settings(env, None, raw="{ 이건 JSON이 아니다")
    assert kr_profile.resolve_root() == str(env / "XIVLauncherKR")


def test_ProfileRoot_키가_없으면_기본값(env):
    write_settings(env, None, raw='{"HookVersion": "15.0.3.2"}')
    assert kr_profile.resolve_root() == str(env / "XIVLauncherKR")


def test_값이_비면_기본값(env):
    write_settings(env, "   ")
    assert kr_profile.resolve_root() == str(env / "XIVLauncherKR")


# --- 업데이터가 거부하는 값은 우리도 안 쓴다 -------------------------------


def test_APPDATA_자신은_거부한다(env):
    # 여기를 프로필 루트로 삼으면 남의 설정 폴더를 통째로 프로필로 다룬다.
    write_settings(env, r"%APPDATA%")
    assert kr_profile.resolve_root() == str(env / "XIVLauncherKR")


def test_드라이브_루트는_거부한다(env):
    write_settings(env, "C:\\")
    assert kr_profile.resolve_root() == str(env / "XIVLauncherKR")


# --- 갈라지지 않았나 - 지금 저장소 -----------------------------------------


def test_설치기가_같은_규칙을_적어_뒀다():
    """C# 쪽은 여기서 못 부른다(단일 EXE). 규칙이 갈라지지 않았나만 본다."""
    source = (kr_profile.REPO / "vendor" / "ff14-accessibility" / "Installer"
              / "KrProfile.cs")
    if not source.is_file():
        pytest.skip("vendor 클론이 없다")
    text = source.read_text(encoding="utf-8")
    for token in (
        kr_profile.ROOT_OVERRIDE_VARIABLE,
        kr_profile.UPDATER_SETTINGS_DIR,
        kr_profile.UPDATER_SETTINGS_NAME,
        kr_profile.PROFILE_ROOT_KEY,
        kr_profile.DEFAULT_FOLDER,
    ):
        assert token in text, f"설치기에 `{token}`이 없다 - 두 해석기가 갈라졌다"


def test_배치도_해석기를_쓴다():
    env_cmd = (kr_profile.REPO / "run" / "_env.cmd").read_text(encoding="cp949")
    assert "kr_profile.py" in env_cmd, "_env.cmd가 아직 경로를 박아 두고 있다"
    assert "XIVLauncherKR" not in env_cmd, "_env.cmd에 하드코딩이 남아 있다"
