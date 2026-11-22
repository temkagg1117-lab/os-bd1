# F.CSM302 — БИЕ ДААЛТ 2: Эцсийн боловсруулалтын тайлан

**Төсөл:** Linux Kernel Module for Task Information — Task Hierarchy  
**Хуваарилалтын код:** `II-4-2` *(БД1-д ашигласан тэмдэглэгээнээс таамагласан, багшийн баталгаатай кодтой тулган шалгана)*  
**Багийн гишүүд:** Г. Тэмүүжин B242270046; М. Цогтбаяр B242270133; А. Бямбасүрэн B241940082; Г. Ганболд B241910023; Ц. Гантүшиг B231940130; Ц. Гантулга B190910023.  
**Repository:** https://github.com/temkagg1117-lab/os-bd1  
**Шинжилсэн БД1 baseline commit:** `0cb46da0c42eefd69121b81e9a889071bc309eb9`.  
**BD2 final commit / tag:** **PENDING** (GitHub интеграц 403 алдаа өгсөн тул нийтлээгүй).  
**Ажлын огноо:** 2026-11-21.

## Хураангуй

БД1-д Linux kernel-ийн `task_struct` мэдээллийг `/proc/pid` рүү PID бичиж, `command / pid / state`-ийн хамт parent/ancestor/children холбоосоор унших module, Python backend, SVG Task Hierarchy UI хэрэгжсэн. БД2-д GitHub PR #3-ийн бодит техникийн review-ыг ангилж, мөн source-code audit хийсэн. Хэрэглэгчийн оролтын хатуу шалгалт, parser-ийн алдааны хамгаалалт, static file path security, demo process-н хязгаар, дүрслэлийн таслагдлыг үнэн зөв тэмдэглэх, diagnostics/UI-ийн сайжруулалтыг оруулав. Шинэ standalone backend/API test suite-ийн 21 тест Linux mock mode-д **21/21 PASS**. Энэ нь бодит kernel module-ийг ачаалсан VM дээрх regression тестийг орлохгүй.

## 1. Төслийн тойм ба БД1-ийн шаардлага

БД1-ийн зорилго нь Silberschatz, *Operating System Concepts* (10th ed.), Chapter 3, Programming Project 2-т хамаарах PID уншилтын механизмыг Linux-д хэрэгжүүлэх байсан. `src/ti_main.c`-ийн `ti_write()` нь `copy_from_user`, `kstrtol` ашигладаг; `ti_read()` нь `ti_walk.c`-ийн report-ыг `simple_read_from_buffer`-аар өгдөг. Output-ийн эхний мөр нь `command = [NAME] pid = [N] state = [S]` форматтай. UI нь `/api/query`, `/api/tree` болон process demo endpoint-уудтай холбогддог. Kernel module нээгээгүй бол MOCK горим `/proc/<pid>/stat`-оос бодит Linux процесс уншдаг. Энэ хоёр горимыг ялгах нь зайлшгүй.

## 2. Эцсийн архитектур

**Бодит горим:** Browser SVG UI → HTTP API (`ui/server.py`) → `/proc/pid` write/read → `ti_main.c` → `ti_walk.c` → Linux `task_struct`. Backend дахь lock нь зөвхөн тухайн server process-оос зэрэг ирсэн write/read хүсэлтийг дарааллуулна; өөр процесс `/proc/pid`-д зэрэг бичвэл global-PID race хэвээр байж болно.

**MOCK горим:** Browser SVG UI → HTTP API → Linux `/proc/<pid>/stat` → process hierarchy. Энэ горим нь UI/parser/HTTP-ийн тест болохоос kernel module-ийн шинжилгээ биш. БД2-ийн өөрчлөлтүүд kernel C интерфейсийн үндсэн протоколыг хадгалж, Python UI/backend-д төвлөрсөн.

## 3. Туршилт ба дүрслэлийн урсгал

1. Linux-д module-гүй үед `python3 ui/server.py --mock` ажиллуулах.
2. PID=1 эсвэл UI-ийн `Мод үүсгэх` товчоор бодит demo Linux process үүсгэх.
3. UI нь `/api/tree?pid=N&depth=2&max=200` хүсэлт илгээнэ.
4. API нь процесс болон хүүхдүүдэд query хийж, нэгдсэн JSON tree буцаана.
5. UI нь ancestor → selected node → descendants-ийг state өнгөөр зурж, selected PID, node count, query count, `/proc` raw output үзүүлнэ.
6. Auto-refresh, Reset, Error/cleanup-ийг шалгана.

**Бодит screenshot:** `docs/evidence/real_mock_ui.png`. Тайлбар: screenshot-ийг шинэ UI-г headless Chromium-д ажиллуулж, live mock backend-ийн бодит `/proc` API хариултаар авсан. Зураг дээр `MOCK` гэсэн ялгах тэмдэг харагдах ёстой.

## 4. Reviewer Comments and Responses

GitHub PR #3-ийн 2026-10-31-нд оруулсан бодит review-г ашигласан. Энд бүрэн хүснэгт: `docs/BD2_Reviewer_Responses.md`. Гол мөрүүд: **R-01 Critical** branch reset risk — БД1 current `main` дээр засагдсан; **R-02 Major** ReportLab markup escape — patch-д орсон; **R-03 Major** багийн 6 дахь гишүүн — current source-д бий; **R-04 Major** dependency зөрүү — manual/README-д зассан; **R-05 Critical** `{II-4-2}` NameError ба generator syntax — patch-д шийдэхээр оруулсан. Өөрийн audit (A-01..A-05)-ыг албан ёсны reviewer-ийн саналтай хутгаагүй.

**Албан ёсны peer-review PDF:** Одоогоор хавсаргагдаагүй. БД2-ийн зааварт шаардагдах албан ёсны PDF ирвэл эх шүүмжийг үгчлэн ишилж, priority/decision/commit/test-ийн матрицад нэмж бүртгэнэ.

## 5. Дахин туршилт: өмнөх/дараах

| Шалгах нөхцөл | БД1 `main`-ийн кодын шинжилгээгээр | БД2-ийн шинэ код / бодит тест |
|---|---|---|
| `/api/tree?pid=1&max=0` | 1 болгон чимээгүй clamp хийдэг | `400 BAD_PARAM`; API тест PASS |
| `/api/tree?pid=1&max=501` | 500 болгон clamp хийдэг | `400 BAD_PARAM`; API тест PASS |
| Дутуу module response | `KeyError`/unexpected error-оор 500 болох эрсдэл | `502 BAD_OUTPUT`; unit test PASS |
| Symlink static path escape | `startswith(STATIC)`-д semantic weakness | `realpath + commonpath`; symlink security test PASS |
| Node cap яг хүрэх | Заавал `truncated=true` болж болно | Бодит орхигдолгүй үед false; unit/API test PASS |
| Demo resource | Өдөрт/серверт group limit байхгүй | 3 active group cap; дөрөв дэхэд 429; API test PASS |

Дээрх **“өмнөх”** багана нь GitHub source-ийн статик шинжилгээ бөгөөд гүйцэтгэлийн хэмжилт биш. Дараах багана нь багцын `tests/test_bd2_api.py`-ийн бодит ажиллуулалтын үр дүн. Хоёр өөр environment/суурь suite-ийн бүх pass count-ыг шууд тэнцүү metric гэж үзэхгүй.

**Тестийн бодит орчин:** Linux kernel 6.18.57, Python 3.13.5, MOCK mode, 2026-11-21. 21 автомат тест: 21 pass, 0 failure, 0 error; 1.011 секунд. Log: `docs/evidence/mock_test_log.txt`.

**Kernel regression:** `sudo ./tests/run_module_tests.sh`, `python3 tests/test_bd2_api.py --module` болон бодит VM screenshot — **NOT RUN in this environment**. Linux kernel headers ба kernel module ачаалах root privilege-ийг энд олгоогүй. Эдгээрийг VM дээр ажиллуулсны дараа logs/summary-г нэмнэ.

## 6. Эцсийн үр дүн

- БД1-ийн C kernel module, interface болон process tree-ийн үндсэн протокол хадгалагдсан.
- БД2 Python backend нь input/API static/file safety болон response validation сайжруулсан.
- HTML/SVG UI-д status, node/query metrics, error message, real/mock ялгаа болон Node cap note тод харагдана.
- **Бодит mock regression: 21/21 PASS**. Kernel test: NOT VERIFIED.
- `BD2_Manual.md`, `BD2_Reviewer_Responses.md`, `BD2_Final_Report.md`, нэг нүүр PDF poster, test log, QR-тай reporting bundle бэлтгэсэн.

## 7. Хязгаарлалт

1. Linux kernel module нь `/proc/pid`-д **нэг global selected PID** хадгална. Өөр write client-уудын хооронд race болох боломжтой.
2. Process tree нь агшин зуур өөрчлөгддөг; parent/child PID exit үед `gone` тэмдэглэнэ.
3. Per-report 64 ancestors, 128 children cap; UI depth 0..6, node cap 1..500.
4. `MOCK` нь Linux `/proc`-ын өөр өөр snapshot-аас state авдаг, kernel module-ийн synchronization/RCU зөв гэдгийг батлахгүй.
5. Linux VM (module build/insmod/dmesg) дээр БД2-ийн бодит kernel regression болон screenshot хийгдээгүй.
6. GitHub-д write эрх 403 учир BD2 branch, final tag/release одоогоор бүтээгдээгүй; “final release” гэж худал тэмдэглээгүй.
7. Албан ёсны peer-review PDF болон багшийн баталгаатай allocation code орж ирээгүй.

## 8. Дүгнэлт

БД2 нь үндсэн kernel төслийг солихгүйгээр дээр нь ажиллах service-layer, output parser, UI-ийн найдвартай байдал, хамгаалалт, тестийн хамрах хүрээг сайжруулсан. Reviewer comment-той холбосон мөр, source-level static audit, ажилласан mock regression болон анхан шатны баримт бичгийн уялдаа бүрдлээ. **Эцсийн хамгаалалтаас өмнө** бодит kernel VM regression, албан peer review, GitHub tag/release, release-URL-тай QR шинэчлэлтийг хийсэн байх ёстой.

**Эшлэлүүд:** Silberschatz et al., *Operating System Concepts* 10th ed. Chapter 3; `OS_BD2_Guide.pdf` х. 2–7; GitHub PR #3 (review comments); `main@0cb46da0...`; `tests/test_bd2_api.py` / `docs/evidence/mock_test_log.txt`.
