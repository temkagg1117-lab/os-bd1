# Тестийн төлөвлөгөө ба бүртгэл (Member 5)

Хүлээгдсэн үр дүн нь дизайнаас; **"Бодит үр дүн"** баганыг VM дээр ажиллуулсны дараа багийнхан бөглөнө
(Report §8-д screenshot хавсаргана). Орчин: `uname -r` = ______ , Ubuntu = ______

## A. Үндсэн (номын шаардлага) — `tests/run_module_tests.sh`
| ID | Оролт | Хүлээгдсэн үр дүн | Бодит үр дүн |
|---|---|---|---|
| T1 | `echo $$ > /proc/pid; cat` | `command = [bash] pid = [N] state = [n]` | |
| T2 | pid 1 | `pid = [1]`, ancestor байхгүй | |
| T3 | `$$` | `ppid` нь `/proc/$$/stat`-ийн 4-р талбартай тэнцүү | |
| T4 | 2 `sleep &` үүсгээд `$$` унших | хоёр `child:` мөр гарна | |
| T5 | `kill -STOP` хийсэн sleep | `state = [4]` | |
| T6 | `echo 4194303 > /proc/pid; cat` | 0 byte, dmesg-д `no task with pid` | |

## B. Захын / буруу оролт
| ID | Оролт | Хүлээгдсэн үр дүн |
|---|---|---|
| E1 | `abc` | write амжилтгүй (Invalid argument), pid өөрчлөгдөхгүй |
| E2 | `0`, `-5` | write амжилтгүй |
| E3 | `99999999999`, 40 оронтой | write амжилтгүй |
| E4 | хоосон / `12abc` / `1 2` | write амжилтгүй |
| E5 | pid бичихгүй шууд `cat` (шинэ ачаалалт) | 0 byte, dmesg `no pid selected yet` |
| E6 | буруу write-ийн дараа `cat` | өмнөх зөв pid-ийн мэдээлэл хэвээр |
| R1 | `rmmod` → `/proc/pid` | файл устсан; `insmod` дахин ажиллана |
| U1 | `nobody` хэрэглэгч | write/read ажиллана (0666) |
| K1 | `dmesg` | oops/BUG/RCU warning байхгүй |

## C. UI / backend — `python3 tests/test_ui_api.py` (mock) ба `... --module` (бодит)
18 тест: T01–T04 (үндсэн), E01–E09 (алдаа), H01–H03 (мод, node cap, cleanup), S01–S02 (static, path traversal).
MOCK горимын үр дүн: **18/18 OK** (багийн хөгжүүлэлтийн орчинд ажиллуулсан). Бодит module-тэй: ______

## D. UI гар аргаар
| ID | Алхам | Хүлээгдсэн |
|---|---|---|
| U-1 | PID=1, depth=2 → Харуулах | Мод зурагдана, 1 нь тодруулагдана |
| U-2 | "Mод үүсгэх" (2,2) | Шинэ root PID автоматаар орж мод гарна; `ps -ef --forest`-тай таарна |
| U-3 | Node дээр дарах | PID солигдож дахин асууна |
| U-4 | PID=`abc` | Улаан алдааны мэдээлэл, зураг өөрчлөгдөхгүй |
| U-5 | PID=4194303 | "process олдсонгүй" |
| U-6 | `rmmod` хийгээд Харуулах | "module ачаалагдаагүй" мэдээлэл |
| U-7 | Автомат шинэчлэл + `kill` хийх | Мод 2 сек дотор шинэчлэгдэнэ |
| U-8 | Reset | Бүх талбар, зураг цэвэрлэгдэнэ |

## M5 validation notes

- On 2026-10-28, the Ubuntu VM reported kernel `7.0.0-31-generic`; a manual
  module build/load and `/proc/pid` read succeeded. Two `sleep` children were
  listed. `nchildren = 3` included the `cat` process used to read the report.
- This manual result predates the current integrated branch; the final module
  test script has not been run on the current branch.
- The current `main` tree is missing `src/ti_main.c`, which the Makefile needs.
  The module test runner now reports this prerequisite explicitly. Run it after
  the M1 module source is merged into the integration branch.
- The API mock test run during M5 development passed 20/20 against the M3
  backend branch. The current integrated mock backend reads Linux `/proc`, so
  run its API suite on Linux; a macOS run cannot validate that procfs behavior.
