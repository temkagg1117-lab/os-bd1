# Ажлын хуваарилалт — 5 гишүүн (guide Хавсралт A, §4 төлөвлөгөө)

| Талбар | Мэдээлэл |
|---|---|
| Хуваарилалтын код | `<II/IV/V>-<цаг>-2` (багийн кодоо бөглөнө) |
| Төсөл | Linux Kernel Module for Task Information (Ch.3, Project 2) |
| Repository | https://github.com/temkagg1117-lab/os-bd1 |
| Хэл/сан/орчин | C (Linux kernel module), Python 3 stdlib (backend), HTML/JS/SVG (UI), Ubuntu VM |
| Үндсэн дүрслэл | Task hierarchy (ancestor → selected → descendants мод) |

## Гишүүн тус бүрийн хариуцлага
| # | Гишүүн (нэр, ID бөглөнө) | Хариуцах ажил | Commit/file | Тайлангийн хэсэг |
|---|---|---|---|---|
| 1 | ________ | **/proc интерфейс**: `proc_create`, `ti_write` (kmalloc, copy_from_user, kstrtol, мужийн шалгалт), `ti_read`, mutex, init/exit, `proc_ops`/`file_operations` салаа, Makefile | `src/ti_main.c`, `src/Makefile` | §2 Номын шаардлага, §5.1 |
| 2 | ________ | **Hierarchy цуглуулагч**: `pid_task/find_vpid`, state→нэр, parent, ancestors, children (`for_each_process`+`real_parent`), RCU, хязгаар (64/128), гаралтын формат | `src/ti_walk.c`, `src/ti_walk.h` | §3 Онолын үндэс (task_struct, PCB, process tree), §4 Зохиомж, §5.2 |
| 3 | ________ | **Backend**: module-тэй write+read протокол, parser, алдааны кодууд, tree builder, `--mock` горим, туршилтын мод үүсгэгч, path-traversal хамгаалалт | `ui/server.py` | §5.3, §7 Туршилтын арга (backend) |
| 4 | ________ | **Task hierarchy UI**: SVG мод, өнгө/төлөв, node click, PID/depth/max оролт, шалгалт, Reset, auto-refresh, алдааны мэдээлэл | `ui/static/index.html` | §6 Туршилт ба UI дүрслэл, Manual §8.1 (тэмдэг, өнгө) |
| 5 | ________ | **Тест, баримт, хэвлэл**: `run_module_tests.sh`, `test_ui_api.py`, `test_cases.md`, бодит үр дүн/screenshot цуглуулах, README, Report+Manual нэгтгэл, GitHub Release `v1.0`, Teams пост, 10-р долоо хоногийн шүүмжийн бэлтгэл | `tests/`, `examples/`, `README.md`, `docs/` | Нүүр, Хураангуй, §1, §7, §8 Үр дүн, §9 Хэлэлцүүлэг, §10 Дүгнэлт |

Бүх гишүүн: өөрийн хэсгээ ажиллуулж туршсан commit-тэй байх; дор хаяж 1 хамтрагчийн Pull Request-ийг review хийх.

## Хугацааны төлөвлөгөө (guide §4)
| 7х | Үйл ажиллагаа | Хариуцагч |
|---|---|---|
| 5 | Сэдэв судлах, repo бүтэц, VM бэлдэх, ажил хуваах, branch үүсгэх | Бүгд (#5 зохион байгуулна) |
| 6 | Номын үндсэн төсөл: `ti_main.c` + `ti_walk.c` (command/pid/state), build | #1, #2 |
| 7 | Backend + UI-г module-тэй холбох, туршилтын тохиргоо | #3, #4 |
| 8 | Тест (VM дээр), бодит үр дүн/screenshot, Report, Manual нэгтгэх | #5 + бүгд |
| 9 | Release `v1.0`, **БД1 суваг дээр нэг пост** | #5 (бүгд шалгана) |
| 10 | Оноогдсон багийн ажлыг build/run/test хийж Review PDF + товч тайлбарыг тэдний постын Reply-д | Бүгд (guide §10) |

## Git workflow (guide §2: GitHub дээр хамтарч ажиллах нөхцөл)
* `main` — тогтвортой. Салбар: `m1-proc-interface`, `m2-walker`, `m3-backend`, `m4-ui`, `m5-tests-docs`.
* Гишүүн бүр өөрийн нэрээр commit хийнэ (`git config user.name`), PR нээж хамтрагчаар review хийлгэнэ.
* Commit мессеж: `m2: add ancestors walk (RCU)`. GitHub Issues-д алдааг бүртгэнэ — Report §9-д дурдана.
* Тайланд GitHub дээрх ажиллагаа (commit тоо, PR, issue)-г тусгана.
* Нууц түлхүүр/нууц үг/хувийн өгөгдөл commit хийхгүй (`.gitignore` бэлэн).

## Review (10-р долоо хоног) — шалгах жагсаалт
Тайлан унших → repo clone → Manual-аар build/run → үндсэн тест давтах → өөрийн нэмэлт тест → UI дүрслэл бодит
ажиллагаатай нийцэж буй эсэх. Review PDF бүтэц/рубрикийг багшийн Peer Review зааврын файлаас авна
(`OS_Topic_and_Peer_Review_Allocation.pdf` дахь хуваарилалтаар тухайн кодыг харна).
