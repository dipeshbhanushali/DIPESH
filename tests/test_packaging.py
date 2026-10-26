"""Every file the app reads at runtime that is not Python is shipped: listed
in build/dipesh.spec (the Windows build) and in pyproject.toml's package
data (pip install .), at the place the code looks for it."""
import ast
import glob
import os
import tomllib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PACKAGE = os.path.join(ROOT, "dipesh")
SPEC = os.path.join(ROOT, "build", "dipesh.spec")


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def runtime_files():
    """Every file inside the package that is not Python code."""
    out = set()
    for folder, dirs, files in os.walk(PACKAGE):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if not f.endswith((".py", ".pyc")):
                out.add(rel(os.path.join(folder, f)))
    return out


def spec_datas():
    """{file: folder it is put in, inside the build}, from the spec's
    Analysis(datas=[...])."""
    with open(SPEC, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and getattr(n.func, "id", "") == "Analysis"]
    assert len(calls) == 1
    datas = ast.literal_eval(next(k.value for k in calls[0].keywords
                                  if k.arg == "datas"))
    out = {}
    for src, dest in datas:
        for path in glob.glob(os.path.join(os.path.dirname(SPEC), src)):
            out[rel(os.path.normpath(path))] = dest.replace("\\", "/")
    return out


def package_data():
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as f:
        table = tomllib.load(f)["tool"]["setuptools"].get("package-data", {})
    out = set()
    for package, patterns in table.items():
        folder = os.path.join(ROOT, *package.split("."))
        for pattern in patterns:
            out |= {rel(p) for p in glob.glob(os.path.join(folder, pattern))}
    return out


def test_there_are_runtime_files_and_the_learn_texts_are_among_them():
    files = runtime_files()
    assert "dipesh/graphical_interface/learn/texts/image.md" in files
    assert all(f.endswith(".md") for f in files), files   # nothing else yet


def test_every_runtime_file_is_in_the_windows_build_where_the_code_looks():
    datas = spec_datas()
    missing = runtime_files() - set(datas)
    assert not missing, f"add to datas in build/dipesh.spec: {missing}"
    for path, dest in datas.items():
        assert dest == os.path.dirname(path), (path, dest)


def test_every_runtime_file_is_in_the_package_data():
    missing = runtime_files() - package_data()
    assert not missing, f"add to package-data in pyproject.toml: {missing}"


def test_the_learn_texts_are_read_from_the_folder_that_is_shipped():
    from dipesh.graphical_interface.learn.textfile import FOLDER
    assert rel(FOLDER) == "dipesh/graphical_interface/learn/texts"
