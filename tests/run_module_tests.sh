#!/usr/bin/env bash
# run_module_tests.sh - tests of the REAL kernel module (needs root + headers)
#   sudo ./tests/run_module_tests.sh
# Builds src/, loads the module, runs main + boundary tests, unloads it.
set -u
cd "$(dirname "$0")/.."
PASS=0; FAIL=0
ok()   { echo "PASS  $1"; PASS=$((PASS+1)); }
bad()  { echo "FAIL  $1  ($2)"; FAIL=$((FAIL+1)); }

[ "$(id -u)" -eq 0 ] || { echo "run with sudo"; exit 2; }
make -C src >/dev/null || { echo "build failed"; exit 2; }
rmmod task_info 2>/dev/null
insmod src/task_info.ko || { echo "insmod failed (dmesg | tail)"; exit 2; }
trap 'rmmod task_info 2>/dev/null' EXIT

P=/proc/pid
rd() { echo "$1" > $P 2>/dev/null; cat $P 2>/dev/null; }

# T1 textbook example: own shell
out=$(rd $$); first=$(echo "$out" | head -1)
[[ "$first" =~ ^command\ =\ \[.+\]\ pid\ =\ \[$$\]\ state\ =\ \[[0-9]+\]$ ]] && ok "T1 textbook format for \$\$" || bad "T1" "$first"

# T2 pid 1
out=$(rd 1); echo "$out" | head -1 | grep -q "pid = \[1\]" && ok "T2 pid 1 readable" || bad "T2" "$out"

# T3 parent matches /proc
pp=$(awk '{print $4}' /proc/$$/stat)
echo "$(rd $$)" | grep -q "^ppid = \[$pp\]" && ok "T3 ppid equals /proc/\$\$/stat" || bad "T3" "ppid mismatch"

# T4 children appear
sleep 30 & C1=$!; sleep 30 & C2=$!
out=$(rd $$)
echo "$out" | grep -q "child: pid = \[$C1\]" && echo "$out" | grep -q "child: pid = \[$C2\]" && ok "T4 children listed" || bad "T4" "children missing"
kill $C1 $C2 2>/dev/null

# T5 state of a stopped task is 4
sleep 30 & S=$!; kill -STOP $S; sleep 0.2
st=$(rd $S | head -1 | sed -n 's/.*state = \[\([0-9]*\)\].*/\1/p')
(( st & 4 )) && ok "T5 stopped bit set (state=$st)" || bad "T5" "state=$st"
kill -KILL $S 2>/dev/null

# T6 nonexistent pid -> read returns 0 bytes (textbook)
echo 4194303 > $P; n=$(cat $P | wc -c); [ "$n" -eq 0 ] && ok "T6 nonexistent pid -> empty read" || bad "T6" "$n bytes"

# boundary / error writes must fail and not crash
for v in "abc" "0" "-5" "99999999999" " " "12abc" "1 2" "$(printf '9%.0s' {1..40})"; do
  if echo -n "$v" > $P 2>/dev/null; then bad "E write '$v'" "accepted"; else ok "E write '$v' rejected"; fi
done

# E: after bad writes the previously stored valid pid is unchanged
echo $$ > $P; echo "abc" > $P 2>/dev/null; cat $P | head -1 | grep -q "pid = \[$$\]" && ok "E pid kept after bad write" || bad "E keep" "changed"

# R: reload cycle leaves no stale entry
rmmod task_info; [ ! -e $P ] && ok "R /proc/pid removed on rmmod" || bad "R" "entry remains"
insmod src/task_info.ko && ok "R reload works"

# unprivileged user may write/read (mode 0666)
if id nobody >/dev/null 2>&1; then
  su -s /bin/bash nobody -c "echo 1 > $P && cat $P | head -1" 2>/dev/null | grep -q "pid = \[1\]" && ok "U unprivileged access" || bad "U" "denied"
fi

dmesg | tail -15 | grep -iE "BUG|Oops|WARNING|RCU" && bad "K kernel log" "oops/warn in dmesg" || ok "K no oops/warn in dmesg"
echo "---- $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ]
