# Evidence provenance — F.CSM302 BD2

- `mock_test_log.txt`: **actual standard-output capture** from running `python3 -m unittest discover -s tests -p 'test_bd2_api.py' -v` against the new standalone backend on Linux. Outcome: 21 tests, 21 passes, 0 failures/errors.
- `test_summary.json`: environment, Python/kernel version, date, baseline SHA, and GitHub integration write limitation.
- `real_mock_ui.png`: **actual screenshot** of the updated HTML/CSS/JS in a headless Chromium browser receiving live HTTP API responses from the updated Python mock backend. The test started real Linux `sh`/`sleep` process groups; the backend read current `/proc/<pid>/stat` for process data. In this environment the Chromium sandbox blocks localhost URL navigation, so Playwright's Python binding relayed the browser requests into the live localhost backend and returned the responses without changing the content. UI screenshot explicitly says `MOCK`.

These files are **not** evidence that `src/task_info.ko` was compiled, loaded, or tested on a Linux VM. No VM kernel build/load/log evidence has been generated here. The final submission needs verified kernel screenshots/logs from the team's VM and the official peer-review PDF. QR in `BD2_Poster.pdf` points to the repository until a final release is actually published.
