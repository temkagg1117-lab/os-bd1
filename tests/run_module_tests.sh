#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROC_PATH="${PID_PROC_PATH:-/proc/pid}"
MODULE_PATH="$ROOT_DIR/src/task_info.ko"
LOADED_BY_TEST=0
PASSED=0
FAILED=0
CHILD_ONE=""
CHILD_TWO=""

pass() {
	PASSED=$((PASSED + 1))
	printf 'PASS: %s\n' "$1"
}

fail() {
	FAILED=$((FAILED + 1))
	printf 'FAIL: %s\n' "$1" >&2
}

cleanup() {
	if [[ -n "$CHILD_ONE" ]]; then
		kill "$CHILD_ONE" 2>/dev/null || true
		wait "$CHILD_ONE" 2>/dev/null || true
	fi
	if [[ -n "$CHILD_TWO" ]]; then
		kill "$CHILD_TWO" 2>/dev/null || true
		wait "$CHILD_TWO" 2>/dev/null || true
	fi
	if [[ "$LOADED_BY_TEST" -eq 1 ]]; then
		rmmod task_info || printf 'WARNING: could not unload task_info\n' >&2
	fi
}
trap cleanup EXIT

if [[ "$(uname -s)" != Linux ]]; then
	printf 'ERROR: module tests require Linux; run them inside the Ubuntu VM.\n' >&2
	exit 2
fi

if [[ "$EUID" -ne 0 ]]; then
	printf 'ERROR: run with sudo: sudo ./tests/run_module_tests.sh\n' >&2
	exit 2
fi

if ! command -v make >/dev/null 2>&1; then
	printf 'ERROR: make is not installed.\n' >&2
	exit 2
fi

if ! make -C "$ROOT_DIR/src"; then
	printf 'ERROR: kernel module build failed.\n' >&2
	exit 1
fi
if [[ ! -f "$MODULE_PATH" ]]; then
	printf 'ERROR: build succeeded but %s is missing.\n' "$MODULE_PATH" >&2
	exit 1
fi

if [[ ! -e "$PROC_PATH" ]]; then
	if ! insmod "$MODULE_PATH"; then
		printf 'ERROR: could not load %s.\n' "$MODULE_PATH" >&2
		exit 1
	fi
	LOADED_BY_TEST=1
fi

if [[ ! -e "$PROC_PATH" ]]; then
	printf 'ERROR: %s is not available after module load.\n' "$PROC_PATH" >&2
	exit 1
fi

read_report() {
	local pid="$1"
	if ! printf '%s\n' "$pid" >"$PROC_PATH"; then
		return 1
	fi
	REPORT="$(<"$PROC_PATH")"
}

if read_report "$$" && grep -Fq "pid = [$$]" <<<"$REPORT"; then
	pass "current process PID is reported"
else
	fail "current process PID is reported"
fi

if grep -q '^command = \[' <<<"${REPORT:-}"; then
	pass "command and process state are reported"
else
	fail "command and process state are reported"
fi

if grep -q '^ppid = \[' <<<"${REPORT:-}"; then
	pass "parent information is reported"
else
	fail "parent information is reported"
fi

if grep -q '^ancestor: ' <<<"${REPORT:-}"; then
	pass "ancestor chain is reported"
else
	fail "ancestor chain is reported"
fi

if read_report 1 && grep -Fq 'pid = [1]' <<<"$REPORT"; then
	pass "PID 1 can be queried"
else
	fail "PID 1 can be queried"
fi

if read_report "$$"; then
	before_invalid="$REPORT"
	if printf 'abc\n' >"$PROC_PATH" 2>/dev/null; then
		fail "non-numeric PID write is rejected"
	else
		pass "non-numeric PID write is rejected"
	fi
	REPORT="$(<"$PROC_PATH")"
	if [[ "$REPORT" == "$before_invalid" ]]; then
		pass "rejected write preserves the previous PID"
	else
		fail "rejected write preserves the previous PID"
	fi
else
	fail "cannot select the current PID before invalid-input check"
fi

missing_pid=4194304
while [[ -e "/proc/$missing_pid" && "$missing_pid" -gt 4194000 ]]; do
	missing_pid=$((missing_pid - 1))
done
if [[ -e "/proc/$missing_pid" ]]; then
	fail "could not find an unused PID for NOT_FOUND test"
elif read_report "$missing_pid" && [[ -z "$REPORT" ]]; then
	pass "nonexistent PID returns an empty report"
else
	fail "nonexistent PID returns an empty report"
fi

sleep 60 &
child_one=$!
CHILD_ONE="$child_one"
sleep 60 &
child_two=$!
CHILD_TWO="$child_two"
if read_report "$$"; then
	if grep -Fq "pid = [$child_one]" <<<"$REPORT" &&
		grep -Fq "pid = [$child_two]" <<<"$REPORT"; then
		pass "both live child processes are listed"
	else
		fail "both live child processes are listed"
	fi
else
	fail "could not read parent report while children are alive"
fi
kill "$child_one" "$child_two" 2>/dev/null || true
wait "$child_one" "$child_two" 2>/dev/null || true
CHILD_ONE=""
CHILD_TWO=""

printf '\nModule test summary: %d passed, %d failed\n' "$PASSED" "$FAILED"
[[ "$FAILED" -eq 0 ]]
