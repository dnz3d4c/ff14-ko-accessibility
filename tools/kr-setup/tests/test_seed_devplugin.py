"""dev 플러그인 시딩 테스트.

지키려는 것은 하나다 - **세 조건이 서로 맞물려 있어야 플러그인이 뜬다.**
어긋나면 오류 없이 조용히 안 뜨므로, 사람이 눈으로 확인할 수단이 없다.
"""

import seed_devplugin

DLL = r"C:\p\devPlugins\FF14Accessibility\FF14Accessibility.dll"
NAME = "FF14Accessibility"
NEW_ID = "11111111-1111-1111-1111-111111111111"


def fresh_config() -> dict:
    """Dalamud가 첫 실행에서 쓰는 형태의 최소 골격."""
    return {
        "DevMode": False,
        "DevPluginLoadLocations": {"$type": "list", "$values": []},
        "DefaultProfile": {"Plugins": {"$type": "list", "$values": []}},
    }


def test_DevMode를_켠다():
    config = fresh_config()
    seed_devplugin.seed(config, DLL, NAME, NEW_ID)
    assert config["DevMode"] is True


def test_로드_위치에_dll을_등록한다():
    config = fresh_config()
    seed_devplugin.seed(config, DLL, NAME, NEW_ID)
    locations = config["DevPluginLoadLocations"]["$values"]
    assert [e["Path"] for e in locations] == [DLL]
    assert locations[0]["IsEnabled"] is True


def test_StartOnBoot과_자동재로드를_켠다():
    config = fresh_config()
    seed_devplugin.seed(config, DLL, NAME, NEW_ID)
    entry = config["DevPluginSettings"][DLL]
    assert entry["StartOnBoot"] is True
    assert entry["AutomaticReloading"] is True


def test_설정과_프로필의_GUID가_일치한다():
    # 이게 어긋나면 Dalamud가 플러그인을 조용히 건너뛴다. 핵심 계약.
    config = fresh_config()
    returned = seed_devplugin.seed(config, DLL, NAME, NEW_ID)
    settings_id = config["DevPluginSettings"][DLL]["WorkingPluginId"]
    profile = config["DefaultProfile"]["Plugins"]["$values"][0]
    assert returned == settings_id == profile["WorkingPluginId"] == NEW_ID
    assert profile["InternalName"] == NAME
    assert profile["IsEnabled"] is True


def test_두_번_돌려도_중복되지_않는다():
    config = fresh_config()
    first = seed_devplugin.seed(config, DLL, NAME, NEW_ID)
    second = seed_devplugin.seed(config, DLL, NAME, "22222222-2222-2222-2222-222222222222")
    assert first == second, "기존 GUID를 재사용해야 프로필 항목과 계속 맞물린다"
    assert len(config["DevPluginLoadLocations"]["$values"]) == 1
    assert len(config["DefaultProfile"]["Plugins"]["$values"]) == 1


def test_기존_프로필_항목이_있으면_되살린다():
    config = fresh_config()
    config["DefaultProfile"]["Plugins"]["$values"].append({
        "InternalName": NAME,
        "WorkingPluginId": "00000000-0000-0000-0000-000000000000",
        "IsEnabled": False,
    })
    seed_devplugin.seed(config, DLL, NAME, NEW_ID)
    profile = config["DefaultProfile"]["Plugins"]["$values"][0]
    assert profile["IsEnabled"] is True
    assert profile["WorkingPluginId"] == NEW_ID


def test_이미_심긴_설정은_한_글자도_안_바뀐다():
    # `main()`이 이걸로 "쓸까 말까"를 정한다. 게임이 떠 있는 동안 이 파일에
    # 쓰면 Dalamud가 종료할 때 자기 상태로 덮어써서 우리 것이 사라진다 -
    # 개발 배포는 게임이 켜진 채로 도는 게 정상이라 조용히 지나가야 한다.
    import json

    config = fresh_config()
    seed_devplugin.seed(config, DLL, NAME, NEW_ID)
    before = json.dumps(config, sort_keys=True)

    seed_devplugin.seed(config, DLL, NAME, "22222222-2222-2222-2222-222222222222")
    assert json.dumps(config, sort_keys=True) == before


def test_로드_위치는_경로_대소문자를_구분하지_않는다():
    # DevPluginSettings는 딕셔너리 키라 정확히 일치해야 한다 - 업스트림도 같다.
    # 여기서 보장하는 것은 로드 위치 목록뿐이다.
    config = fresh_config()
    seed_devplugin.seed(config, DLL, NAME, NEW_ID)
    seed_devplugin.seed(config, DLL.upper(), NAME, NEW_ID)
    assert len(config["DevPluginLoadLocations"]["$values"]) == 1
