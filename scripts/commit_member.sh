#!/usr/bin/env bash
# commit_member.sh - тухайн гишүүний файлуудыг салбартаа commit хийж push хийнэ.
#   ./scripts/commit_member.sh 0   # (зөвхөн Тэмүүжин, нэг удаа) main-д суурь файл push
#   ./scripts/commit_member.sh N   # N = 1..6 (өөрийн дугаар)
set -euo pipefail
cd "$(dirname "$0")/.."
N="${1:-}"; [[ "$N" =~ ^[0-6]$ ]] || { echo "Хэрэглээ: $0 <0..6>"; exit 2; }
git config user.name >/dev/null && git config user.email >/dev/null || { echo "git config user.name/user.email тохируул"; exit 2; }

commit() { # commit "<msg>" files...
  local msg="$1"; shift
  git add -- "$@"
  if git diff --cached --quiet; then echo "(өөрчлөлтгүй: $msg)"; else git commit -q -m "$msg"; echo "commit: $msg"; fi
}

if [ "$N" = 0 ]; then
  git checkout -q main 2>/dev/null || git checkout -q -b main
  commit "chore: add .gitignore and task split" .gitignore docs/TASK_SPLIT.md
  git push -u origin main
  echo "Суурь main-д орлоо. Бусад гишүүд git pull хийгээд өөрийн дугаараар ажиллуулна."; exit 0
fi

declare -A BR=([1]=m1-proc-interface [2]=m2-walker [3]=m3-backend [4]=m4-ui [5]=m5-tests [6]=m6-docs)
git fetch -q origin 2>/dev/null || true
git checkout -q main 2>/dev/null && git pull -q --ff-only origin main 2>/dev/null || true
git checkout -q -B "${BR[$N]}"

case "$N" in
1) commit "m1: add /proc/pid entry with proc_ops/file_operations switch" src/ti_main.c src/Makefile ;;
2) commit "m2: add task walker header and report format" src/ti_walk.h
   commit "m2: implement parent, ancestors and children walk under RCU" src/ti_walk.c ;;
3) commit "m3: add backend with module protocol, parser and error mapping" ui/server.py ;;
4) commit "m4: add Task hierarchy SVG UI" ui/static/index.html ;;
5) commit "m5: add backend API tests" tests/test_ui_api.py
   commit "m5: add kernel module shell tests" tests/run_module_tests.sh
   commit "m5: add test plan and example outputs" tests/test_cases.md examples ;;
6) commit "m6: add README with quick start and known issues" README.md
   commit "m6: add report/manual generator and PDFs" docs/src/build_docs.py docs/BD1_Report.pdf docs/BD1_Manual.pdf docs/BD1_POST_TEMPLATE.md
   commit "m6: add git helper script" scripts/commit_member.sh ;;
esac

git push -u origin "${BR[$N]}"
echo
echo "Push хийгдлээ -> салбар ${BR[$N]}. GitHub дээр Pull Request нээж хамтрагчаар review хийлгэнэ:"
echo "https://github.com/temkagg1117-lab/os-bd1/compare/main...${BR[$N]}?expand=1"
