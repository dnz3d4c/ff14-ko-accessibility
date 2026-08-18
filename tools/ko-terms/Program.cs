// 게임 데이터에서 한국어 UI 낱말을 뽑는다.
//
// 왜 필요한가: 모드가 말하는 낱말과 게임 화면에 뜨는 낱말이 다르면 사용자가
// 이름을 두 개 외워야 한다. 그래서 게임이 쓰는 말을 그대로 써야 하는데
// **지어내면 안 된다.** 이 저장소는 이미 한 번 당했다 - `Aetheryte`를
// "에테라이트"라고 스킬에 결정으로 박아 놨는데 로그·덤프 전체에서 그 표기가
// 0건이었다.
//
// 로그를 뒤지는 방법은 그 화면에 들어가 본 적이 있어야 한다. 이 도구는 게임을
// 켜지 않고 sqpack에서 직접 읽으므로 그 제약이 없다.
//
// 찾는 방식이 이 도구의 핵심이다. **행 번호로 잇는다.** 같은 Addon 행이
// 언어마다 같은 UI 문자열이므로, 아는 언어로 찾아 행을 잡고 그 행의 한국어를
// 읽는다. 한국어를 짐작해서 찾지 않는다 - 그러면 짐작이 답이 되어 버린다.
//
// 사용법 (run\terms.bat이 감싼다):
//     terms langs              이 sqpack에 어떤 언어가 들어 있나
//     terms find <낱말>        아는 언어로 찾아 한국어를 나란히 본다
//     terms row <번호>         행 번호로 바로 본다
//     terms dump <디렉토리>    전 행을 TSV로

using System.Text;
using Lumina;
using Lumina.Data;
using Lumina.Excel.Sheets;

Console.OutputEncoding = Encoding.UTF8;

const string GameRoot = @"C:\Program Files (x86)\FINAL FANTASY XIV - KOREA";

var sqpack = Path.Combine(GameRoot, "game", "sqpack");
if (!Directory.Exists(sqpack))
{
    Console.Error.WriteLine($"게임 데이터가 없다: {sqpack}");
    Console.Error.WriteLine("  설치 경로는 docs/environment.md 1절.");
    return 2;
}

// 체크섬 검사를 끄는 것은 추측이 아니다. KR 시트는 Lumina의 글로벌 기준
// 스키마와 체크섬이 어긋나고, KR Dalamud 언어 패치도 같은 이유로 이걸 끈다
// (docs/ko-client-port-feasibility.md).
GameData game;
try
{
    game = new GameData(sqpack, new LuminaOptions
    {
        PanicOnSheetChecksumMismatch = false,
        DefaultExcelLanguage = Language.Korean,
    });
}
catch (Exception ex)
{
    Console.Error.WriteLine($"게임 데이터를 못 열었다: {ex.Message}");
    return 2;
}

// 어느 언어가 실제로 들어 있는지는 클라이언트마다 다르다. 한국 클라이언트가
// 영어를 같이 담고 있는지는 **확인해 봐야 아는 것**이라 하드코딩하지 않는다.
var candidates = new[]
{
    Language.Korean, Language.English, Language.Japanese,
    Language.German, Language.French,
};

var available = new List<Language>();
foreach (var language in candidates)
{
    try
    {
        var sheet = game.GetExcelSheet<Addon>(language);
        if (sheet is { Count: > 0 }) available.Add(language);
    }
    catch
    {
        // 그 언어가 없는 것은 오류가 아니다.
    }
}

if (available.Count == 0)
{
    Console.Error.WriteLine("Addon 시트를 어떤 언어로도 못 읽었다.");
    return 1;
}

var mode = args.Length > 0 ? args[0] : "langs";

switch (mode)
{
    case "langs":
        Console.WriteLine($"sqpack: {sqpack}");
        foreach (var language in available)
            Console.WriteLine($"  {language}\t{game.GetExcelSheet<Addon>(language)!.Count}행");
        return 0;

    case "find":
        if (args.Length < 2) { Console.Error.WriteLine("찾을 낱말을 달라."); return 2; }
        return Find(args[1]);

    case "row":
        if (args.Length < 2 || !uint.TryParse(args[1], out var wanted))
        { Console.Error.WriteLine("행 번호를 달라."); return 2; }
        Show(wanted);
        return 0;

    case "dump":
        if (args.Length < 2) { Console.Error.WriteLine("출력 디렉토리를 달라."); return 2; }
        return Dump(args[1]);

    default:
        Console.Error.WriteLine($"모르는 모드: {mode}");
        return 2;
}

string TextAt(Language language, uint rowId)
{
    var sheet = game.GetExcelSheet<Addon>(language);
    var row = sheet?.GetRowOrDefault(rowId);
    return row?.Text.ExtractText() ?? "";
}

void Show(uint rowId)
{
    Console.WriteLine($"행 {rowId}");
    foreach (var language in available)
    {
        var text = TextAt(language, rowId);
        if (!string.IsNullOrWhiteSpace(text))
            Console.WriteLine($"  {language,-8} {text}");
    }
}

int Find(string query)
{
    // 한국어 말고 다른 언어에서 찾는다. 한국어로 찾으면 짐작한 낱말이 그대로
    // 답이 되어 버려서, 확인이 아니라 자기 확인이 된다.
    var searchable = available.Where(l => l != Language.Korean).ToList();
    if (searchable.Count == 0)
    {
        Console.Error.WriteLine(
            "이 sqpack에는 한국어밖에 없다. 행 번호를 아는 경우에만 `row`로 볼 수 있다.");
        Console.Error.WriteLine(
            "  글로벌 클라이언트가 있으면 거기서 행 번호를 잡아 여기서 그 행을 읽는다.");
        return 1;
    }

    var hits = new SortedSet<uint>();
    foreach (var language in searchable)
    {
        var sheet = game.GetExcelSheet<Addon>(language)!;
        foreach (var row in sheet)
        {
            var text = row.Text.ExtractText();
            if (!string.IsNullOrEmpty(text)
                && text.Contains(query, StringComparison.OrdinalIgnoreCase))
                hits.Add(row.RowId);
        }
    }

    if (hits.Count == 0)
    {
        Console.WriteLine($"'{query}' 없음. 못 찾았으면 못 찾았다고 적어라 - 지어내지 않는다.");
        return 1;
    }

    Console.WriteLine($"'{query}' {hits.Count}행");
    foreach (var rowId in hits) Show(rowId);
    return 0;
}

int Dump(string directory)
{
    Directory.CreateDirectory(directory);
    foreach (var language in available)
    {
        var sheet = game.GetExcelSheet<Addon>(language)!;
        var path = Path.Combine(directory, $"addon-{language}.tsv");
        using var writer = new StreamWriter(path, false, new UTF8Encoding(false));
        writer.NewLine = "\n";
        writer.WriteLine("row\ttext");
        foreach (var row in sheet)
        {
            var text = row.Text.ExtractText();
            if (string.IsNullOrWhiteSpace(text)) continue;
            // 탭과 줄바꿈은 TSV를 깨므로 눈에 보이게 바꿔 둔다.
            writer.WriteLine($"{row.RowId}\t{text.Replace("\t", "\\t").Replace("\n", "\\n").Replace("\r", "")}");
        }
        Console.WriteLine($"  {path}");
    }
    return 0;
}
