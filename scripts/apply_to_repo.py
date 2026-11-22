#!/usr/bin/env python3
"""Apply the standalone BD2 package to a CLEAN checkout of os-bd1/main.

Preserves C kernel module sources and Git metadata. Backs off if source SHA
is not the reviewed main snapshot, rather than overwriting a student's work.
"""
import ast
import hashlib
import shutil
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
EXPECTED = {
    "README.md": "89b5cb05c9f0c7ca9dd433764c8f0eea4686fcdf",
    "docs/src/build_docs.py": "d832813c3280d45b6722c23d2b3f7e87bb02205e",
    "ui/server.py": "22cd53682ca6c46c0710e7d233ce95b3de78b698",
    "ui/static/index.html": "8c49cf8efd15c8e2f6aec1b807d58a06d32a0306",
}


def blobsha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def bd1_generator_patch(source):
    # Repair the reviewer's explicitly reported NameError and ReportLab markup risk.
    source = source.replace('from reportlab.lib.pagesizes import A4',
                            'from xml.sax.saxutils import escape\nfrom reportlab.lib.pagesizes import A4')
    source = source.replace('P(f"Хуваарилалтын код: <b>{II-4-2}</b>", C)',
                            'P(f"Хуваарилалтын код: <b>{escape(CODE)}</b>", C)')
    source = source.replace('P(f"Код: {CODE} • UI: Task hierarchy", C)',
                            'P(f"Код: {escape(CODE)} • UI: Task hierarchy", C)')
    # Several historical RESULTS literals contain unescaped physical newlines.
    # Keep the original historical claims, but mark them as BD1-era records.
    original_start = source.index('RESULTS = [')
    original_end = source.index('\ndef report():', original_start)
    new_results = '''RESULTS = [  # Хуучин БД1-ийн бүртгэл; шинэ VM regression-тэй андуурч болохгүй.
    ("T1", "echo $$ > /proc/pid; cat /proc/pid", "command/pid/state", "БД1 тайланд тэмдэглэсэн: command=[bash] pid=[5554], state=[1]"),
    ("T2", "pid 1", "pid=[1], ancestor байхгүй", "БД1 тайланд давсан гэж тэмдэглэсэн"),
    ("T3", "ppid шалгалт", "proc stat ppid-тай тэнцүү", "БД1 тайланд ppid=[5543] гэж тэмдэглэсэн"),
    ("T4", "2 sleep child", "2 child мөр", "БД1 тайланд 2 child харагдсан гэж тэмдэглэсэн"),
    ("T5", "STOP state bit", "state & 4 != 0", "БД1 тайланд state=260, STOPPED bit=4 гэж тэмдэглэсэн"),
    ("T6", "nonexistent PID", "0 byte", "БД1 тайланд 0 byte гэж тэмдэглэсэн"),
    ("E1-E4", "bad writes", "EINVAL; PID unchanged", "БД1 тайланд bad input rejected гэж тэмдэглэсэн"),
    ("R1", "unload/reload", "proc entry removed and recreated", "БД1 тайланд давсан гэж тэмдэглэсэн"),
    ("K1", "kernel log", "no BUG/Oops/RCU warning", "БД1 тайланд давсан гэж тэмдэглэсэн"),
]

'''
    source = source[:original_start] + new_results + source[original_end:]
    # Two other broken source fragments in the integrated BD1 generator:
    # malformed CSV-like tuple in the contributor stats and unclosed results list.
    source = source.replace('("Цогтбаяр", "m2-walker", "4, "3, "0"),',
                            '("Цогтбаяр", "m2-walker", "4", "3", "0"),')
    source = source.replace('          Spacer(1, 3 * mm),\n    s += [P("9. Хэлэлцүүлэг", H1)]',
                            '          Spacer(1, 3 * mm)]\n    s += [P("9. Хэлэлцүүлэг", H1)]')
    # Allow font discovery on Linux and machines with a user-installed font path.
    source = source.replace('FD = "/usr/share/fonts/truetype/dejavu/"',
                            'FD = os.environ.get("BD2_FONT_DIR", "/usr/share/fonts/truetype/dejavu/")\n'
                            'if not FD.endswith(os.sep):\n    FD += os.sep')
    try:
        ast.parse(source, filename="docs/src/build_docs.py")
    except SyntaxError as exc:
        raise RuntimeError(f"Cannot safely repair BD1 generator: {exc}") from exc
    return source


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 OS_BD2_Submission/scripts/apply_to_repo.py PATH_TO_os-bd1")
    repo = Path(sys.argv[1]).resolve()
    if not (repo / ".git").exists() or not (repo / "src/ti_main.c").exists():
        raise SystemExit("ERROR: target must be the checked-out os-bd1 Git repository")
    for rel, expected in EXPECTED.items():
        path = repo / rel
        if not path.exists():
            raise SystemExit(f"ERROR: expected upstream file missing: {rel}")
        actual = blobsha(path.read_bytes())
        if actual != expected:
            raise SystemExit(f"ERROR: {rel} modified/updated (blob {actual}); refusing to overwrite. "
                             "Use a clean checkout of the reviewed main commit and inspect changes manually.")
    # Perform checks before writing any file.
    generator = bd1_generator_patch((repo / "docs/src/build_docs.py").read_text(encoding="utf-8"))
    readme = (repo / "README.md").read_text(encoding="utf-8")
    readme += """

## Бие даалт 2 — сайжруулсан хувилбар

- БД2 Quick Start, limitation болон бодит тестийн ялгааг [README_BD2.md](README_BD2.md)-ээс үзнэ үү.
- Шинэ backend/API regression: `python3 -m unittest discover -s tests -p 'test_bd2_api.py' -v` (MOCK),
  бодит module: `python3 tests/test_bd2_api.py --module` (VM-д /proc/pid ачаалсан үед).
- UI: `python3 ui/server.py --mock` (module-гүй), эсвэл `make -C src && sudo insmod src/task_info.ko`-ийн дараа `python3 ui/server.py`.
- Runtime backend нь Python stdlib ашигладаг. **PDF generator нь тусдаа** `reportlab`, `qrcode[pil]`
  болон DejaVu Sans TTF font шаарддаг: `python3 -m pip install reportlab 'qrcode[pil]'`;
  Debian/Ubuntu-д `sudo apt install fonts-dejavu-core`. Mac дээр PDF font-ын байрлалыг
  `BD2_FONT_DIR=/path/to/fonts` environment variable-аар өгч болно; kernel module нь зөвхөн Linux-д.
- Report/Manual/Poster: `docs/BD2_*.pdf`; review tracking: `docs/BD2_Reviewer_Responses.md`.
- Бодит kernel regression, албан ёсны peer review, GitHub final tag/release баталгаажтал
  'final release completed' гэж ойлгож болохгүй.
"""
    copied = [
        "README_BD2.md", "CHANGELOG_BD2.md", "requirements-docs.txt", "requirements-screenshot.txt", "ui/server.py", "ui/static/index.html", "tests/test_bd2_api.py",
        "docs/BD2_Final_Report.md", "docs/BD2_Reviewer_Responses.md", "docs/BD2_Manual.md",
        "docs/BD2_Teams_Post.md", "docs/BD2_Checklist.md", "docs/BD2_Final_Report.pdf", "docs/BD2_Manual.pdf",
        "docs/BD2_Poster.pdf", "docs/build_bd2.py",
        "docs/evidence/mock_test_log.txt", "docs/evidence/test_summary.json", "docs/evidence/README.md",
        "docs/evidence/real_mock_ui.png", "scripts/capture_ui.py", "scripts/validate_bd2.sh", "scripts/apply_to_repo.py",
    ]
    for rel in copied:
        src = PACKAGE / rel
        if not src.is_file():
            raise SystemExit(f"ERROR: BD2 package missing generated file: {rel}")
    # Avoid accidental partial writes due to missing inputs above.
    for rel in copied:
        destination = repo / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PACKAGE / rel, destination)
        print("COPIED", rel)
    (repo / "docs/src/build_docs.py").write_text(generator, encoding="utf-8")
    (repo / "README.md").write_text(readme, encoding="utf-8")
    print("PATCHED docs/src/build_docs.py (compile checked) + README.md")
    print("NEXT: run tests, inspect git diff, then commit/push on YOUR branch.")

if __name__ == "__main__":
    main()
