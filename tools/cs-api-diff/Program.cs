using System.Reflection;

// args: <assembly path> <type simple name> [sigs]
//   sigs -> print the signature strings ClientStructs uses to resolve every
//           member function of the type, plus the field offsets, instead of the
//           API listing. Type name may end in '*' to match a prefix.
var asmPath = args[0];
var typeName = args[1];
var sigMode = args.Length > 2 && args[2] == "sigs";

var dir = Path.GetDirectoryName(Path.GetFullPath(asmPath))!;
var assemblies = Directory.GetFiles(dir, "*.dll").ToList();
var resolver = new PathAssemblyResolver(
    assemblies.Concat(Directory.GetFiles(
        Path.GetDirectoryName(typeof(object).Assembly.Location)!, "*.dll")));

using var mlc = new MetadataLoadContext(resolver);
var asm = mlc.LoadFromAssemblyPath(Path.GetFullPath(asmPath));
Console.WriteLine($"# {asm.GetName().Name} {asm.GetName().Version}");

bool Matches(Type t) => typeName.EndsWith('*')
    ? t.Name.StartsWith(typeName[..^1], StringComparison.Ordinal)
    : t.Name == typeName;

if (sigMode)
{
    foreach (var t in asm.GetTypes().Where(Matches).OrderBy(t => t.FullName))
    {
        Console.WriteLine($"## {t.FullName}");
        foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.NonPublic
                                       | BindingFlags.Instance | BindingFlags.Static
                                       | BindingFlags.DeclaredOnly)
                           .OrderBy(m => m.Name))
        {
            foreach (var a in m.GetCustomAttributesData())
            {
                var kind = a.AttributeType.Name;
                if (kind is not ("MemberFunctionAttribute" or "StaticAddressAttribute"
                                 or "VirtualFunctionAttribute" or "SigAttribute"))
                    continue;
                var argv = string.Join(" | ", a.ConstructorArguments.Select(x => x.Value?.ToString()));
                Console.WriteLine($"  sig {t.Name}.{m.Name} [{kind}] {argv}");
            }
        }
        foreach (var f in t.GetFields(BindingFlags.Public | BindingFlags.NonPublic
                                      | BindingFlags.Instance | BindingFlags.Static
                                      | BindingFlags.DeclaredOnly))
        {
            var off = f.GetCustomAttributesData()
                       .FirstOrDefault(a => a.AttributeType.Name == "FieldOffsetAttribute");
            if (off is not null)
                Console.WriteLine($"  field {t.Name}.{f.Name} @ 0x{Convert.ToInt32(off.ConstructorArguments[0].Value):X} {f.FieldType.Name}");
            else if (f.IsLiteral)
                Console.WriteLine($"  const {t.Name}.{f.Name} = 0x{Convert.ToInt64(f.GetRawConstantValue()):X}");
        }
    }
    return;
}

foreach (var t in asm.GetTypes().Where(t => t.Name == typeName))
{
    Console.WriteLine($"## {t.FullName}");
    foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.NonPublic
                                   | BindingFlags.Instance | BindingFlags.Static
                                   | BindingFlags.DeclaredOnly)
                       .OrderBy(m => m.Name))
    {
        var ps = string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name + " " + p.Name + (p.HasDefaultValue ? " = " + (p.RawDefaultValue?.ToString() ?? "null") : "")));
        Console.WriteLine($"  {m.Name}({ps}) -> {m.ReturnType.Name}");
    }
}

foreach (var t in asm.GetTypes().Where(t => t.Name == typeName))
{
    Console.WriteLine($"## fields of {t.FullName}");
    foreach (var f in t.GetFields(BindingFlags.Public | BindingFlags.NonPublic
                                  | BindingFlags.Instance | BindingFlags.Static
                                  | BindingFlags.DeclaredOnly).OrderBy(f => f.Name))
        Console.WriteLine($"  {f.FieldType.Name} {f.Name}");
    Console.WriteLine($"## properties of {t.FullName}");
    foreach (var p in t.GetProperties(BindingFlags.Public | BindingFlags.NonPublic
                                      | BindingFlags.Instance | BindingFlags.Static
                                      | BindingFlags.DeclaredOnly).OrderBy(p => p.Name))
        Console.WriteLine($"  {p.PropertyType.Name} {p.Name}");
}

foreach (var t in asm.GetTypes().Where(t => t.Name == typeName))
{
    Console.WriteLine($"## kind {t.FullName}: class={t.IsClass} valuetype={t.IsValueType} sealed={t.IsSealed}");
    foreach (var f in t.GetFields(BindingFlags.Public | BindingFlags.NonPublic
                                  | BindingFlags.Instance | BindingFlags.Static
                                  | BindingFlags.DeclaredOnly))
        Console.WriteLine($"   field {f.Name}: static={f.IsStatic} initonly={f.IsInitOnly} literal={f.IsLiteral} type={f.FieldType.Name}");
}
