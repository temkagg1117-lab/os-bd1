# F.CSM302 Бие даалт 1 — Linux Kernel Module for Task Information

**Хуваарилалтын код:** `<II|IV|V>-<цаг>-2` (сэдэв 2) — *багийн кодоо энд бөглөнө*
**Сурах бичиг:** Silberschatz, *Operating System Concepts* (10th ed.), Chapter 3 Processes, Programming Project 2
**UI дүрслэл:** Task hierarchy (parent–child мод)

## Зорилго
`/proc/pid` файлаар дамжуулан task-ийн мэдээллийг харуулдаг Linux kernel module.
`echo <pid> > /proc/pid` гэж бичээд `cat /proc/pid` гэж уншихад task-ийн **command, pid, state**
(номын шаардлага) болон **parent, ancestors, children** (Task hierarchy UI-д) гарна.
Web UI нь тэр модыг бодит module-ээс асууж SVG мод болгон зурна.

```
echo "1395" > /proc/pid
cat /proc/pid
command = [bash] pid = [1395] state = [1]     <- номын формат
```

## Quick Start (Ubuntu 22.04/24.04 VM, root эрхтэй)
```bash
sudo apt install build-essential linux-headers-$(uname -r) python3
git clone https://github.com/temkagg1117-lab/os-bd1.git && cd os-bd1
make -C src                       # task_info.ko
sudo insmod src/task_info.ko      # /proc/pid үүснэ
echo $$ > /proc/pid && cat /proc/pid
python3 ui/server.py              # http://127.0.0.1:8000   (UI)
sudo ./tests/run_module_tests.sh  # автомат тест
sudo rmmod task_info              # unload
```
Kernel module-гүй машин дээр UI-г үзэхийг хүсвэл: `python3 ui/server.py --mock`
(UI дээр **MOCK** гэсэн шар тэмдэг гарна; энэ нь `/proc/<pid>/stat`-аас module-ийн гаралтыг дууриадаг).

> UI backend нь `/proc/pid` руу бичиж унших тул `server.py`-г module-ийг ачаалсан хэрэглэгчээс
> (эсвэл `sudo`) ажиллуулна; файлын эрх 0666 тул энгийн хэрэглэгч бас болно.

## Бүтэц
| Зам | Агуулга |
|---|---|
| `src/ti_main.c`, `src/Makefile` | /proc/pid интерфейс: write (kstrtol, шалгалт), read |
| `src/ti_walk.c/.h` | task_struct-аас hierarchy цуглуулах (RCU, parent/ancestors/children) |
| `ui/server.py` | Backend: module-тэй харилцах, parser, mock горим, туршилтын мод үүсгэгч |
| `ui/static/index.html` | Task hierarchy SVG дүрслэл |
| `tests/` | `run_module_tests.sh` (бодит module), `test_ui_api.py` (backend), `test_cases.md` |
| `examples/` | Гаралтын формат, туршиж үзэх PID-ууд |
| `docs/` | `BD1_Report.pdf`, `BD1_Manual.pdf`, `TASK_SPLIT.md`, PDF үүсгэгч (`docs/src/`) |

## Хэрэгжүүлсэн шаардлага (guide §3 ба §5)
1. Номын үндсэн функц: pid бичих → command/pid/state унших, хүчингүй pid үед read 0 буцаах.
2. Оролт өөрчилж дахин турших: UI-ийн PID/depth/node талбар, Reset, автомат шинэчлэл.
3. Буруу/захын оролт: `abc`, `0`, `-5`, хэт том, хоосон, урт оролт → ойлгомжтой алдаа (UI + dmesg).
4. Task hierarchy UI бодит module-тэй холбогдсон (мод бүр `/proc/pid` write+read-ээр баригдана).
5. Туршилт: `tests/` дотор үндсэн + нэмэлт; нотолгоог `docs/BD1_Report.pdf`-д.
6. Manual дагуу өөр машин дээр build/run хийж болно (`docs/BD1_Manual.pdf`).
Хатуу кодлосон өгөгдөл байхгүй; нууц түлхүүр/хувийн өгөгдөл репод орохгүй.

## Known issues
* Kernel 5.6+ (`proc_ops`) болон 5.14+ (`__state`)-д тохируулсан; хуучин kernel-д `LINUX_VERSION_CODE` салаагаар ажиллана.
* Ганц глобал pid хадгалдаг (номын загвар) — хоёр хэрэглэгч зэрэг ажиллуулбал pid бие биенээ дарна; UI backend `write+read`-ийг lock-оор хамгаалдаг.
* Олон thread-тэй процессын child-ийг thread-group түвшинд (tgid) харуулна.
* UI-д ZOMBIE node-ийн өнгө зөвхөн `state` тоогоор тодорхойлогддог тул сонгосон task-ийн `state_name` талбарыг шалгана.

## AI / бэлэн кодын тэмдэглэл
Энэ репогийн анхны хувилбарыг (module, UI, тест, баримтын ноорог) **Claude (Anthropic)** AI туслагчийн тусламжтай
бэлтгэсэн. Баг код бүрийг уншиж, өөрийн VM дээр build/run/test хийж баталгаажуулсан байх ёстой — үр дүнг тайландаа
бодит screenshot-оор нотлоно. Гадны сан ашиглаагүй (Python stdlib, Linux kernel headers).
Номын pid.c skeleton болон Figure 3.37-ийн санааг ашигласан.
