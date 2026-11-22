#!/usr/bin/env bash
# Run inside the patched os-bd1 repository. Never claims a kernel test in MOCK mode.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p docs/evidence
{
 echo "BD2 MOCK regression started: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
 echo "Kernel: $(uname -r)"
 echo "Python: $(python3 --version)"
 echo "NOTE: This does NOT test task_info.ko."
 python3 -m py_compile ui/server.py tests/test_bd2_api.py docs/build_bd2.py
 bash -n tests/run_module_tests.sh scripts/validate_bd2.sh
 python3 -m unittest discover -s tests -p test_bd2_api.py -v
} 2>&1 | tee docs/evidence/latest_mock_regression.log
echo "Optional Linux VM steps (separate): sudo ./tests/run_module_tests.sh; python3 tests/test_bd2_api.py --module"
