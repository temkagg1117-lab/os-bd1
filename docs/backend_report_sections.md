# Тайлангийн хэсэг — Backend (Бямбасүрэн)

> Энэ файл нь Report.pdf-д нэгтгэгдэх **§4 Системийн зохиомж (Компонент ба өгөгдлийн урсгал)** ба
> **§5.2 Хэрэгжилт (Backend хэсэг)**-ийн эх бичвэр. Хэсгийн дугаарыг нэгтгэгч (Report.pdf) эцэслэнэ.
> Холбогдох код: `src/proc_bridge.py`, `src/ui_server.py`.

---

## 4. Системийн зохиомж

### 4.1 Ерөнхий бүтэц

Систем нь гурван давхаргатай. Цөмийн модуль процессийн мэдээллийг `/proc/pid` файлаар гаргана, Python
backend тэр файлыг уншиж JSON болгоно, веб UI нь JSON-оос Task hierarchy мод зурна.

```
 Хөтөч: index.html + style.css + app.js            (UI давхарга)
          │  HTTP/JSON:  GET /api/query   POST /api/spawn   POST /api/cleanup
          ▼
 ui_server.py   ThreadingHTTPServer: статик файл + API    ┐
          │  Python дуудалт                               │ Backend
          ▼                                               │ (user space)
 proc_bridge.py  write(pid) → read(report) → parse → мод  ┘
          │  write("1203\n")            ▲ read() → текст тайлан
 ═════════╪═════════════════════════════╪═══════════ user / kernel хил
          ▼                             │
 task_info.ko:  ti_main.c  (/proc/pid, шалгалт, mutex)     (Kernel давхарга)
                ti_walk.c  (task_struct алхагч, RCU)
          ▼
 task_struct:  pid, comm, __state, real_parent, children
```

### 4.2 Компонентууд

| Компонент | Файл | Үүрэг |
|---|---|---|
| Цөмийн /proc интерфэйс | `ti_main.c` | `echo <pid> > /proc/pid`-ийг шалгаж хадгална, `cat /proc/pid` дээр тайлан буцаана |
| Hierarchy алхагч | `ti_walk.c` | `real_parent` гинжээр дээш, `children`-ээр доош алхаж тайлангийн мөрүүдийг бичнэ |
| Bridge | `proc_bridge.py` | `/proc/pid` руу бичих/унших, тайланг задлах (parse), мод барих, алдааг ангилах |
| HTTP сервер | `ui_server.py` | Статик файл өгөх, `/api/*` хүсэлт хүлээн авах, туршилтын мод үүсгэх/цэвэрлэх |
| UI | `static/*` | `/api/query`-ийн JSON-оор SVG/HTML мод зурах, node дээр дарж PID солих |

### 4.3 Өгөгдлийн урсгал: PID хайх

1. Хэрэглэгч UI дээр PID бичиж (эсвэл node дээр дарж) `GET /api/query?pid=<текст>` илгээнэ.
2. `ui_server.py` текстийг өөрчлөхгүйгээр `ProcBridge.query()`-д өгнө.
3. Bridge хоосон/хэвлэгдэхгүй оролтыг татгалзаж, `0`-г reset гэж үзнэ (4.5-г үз). Бусад оролтыг модуль руу илгээнэ.
4. Lock авч `write("<pid>\n")`, дараа нь файлыг шинээр нээж EOF хүртэл `read()` хийнэ.
5. Модуль `write` дээр `EINVAL` буцаавал bridge оролтыг ангилж `FORMAT_ERROR`/`BOUNDARY_ERROR` болгоно.
   Тайлан хоосон бол `NOT_FOUND`.
6. Тайлангийн мөр бүрийг `key = [value]` хос болгон задалж `pid → task` толь үүсгэнэ.
7. Зорилтот процессийн бүх хүүхдийн хувьд тэдний өөрсдийн хүүхдийг (ач) мөн модулиас асууж толинд нэмнэ.
8. `ppid` холбоосоор ancestors → target → children → grandchildren мод барьж JSON-оор буцаана.

### 4.4 Өгөгдлийн урсгал: туршилтын мод

* `POST /api/spawn` нь тусдаа Python процесс (launcher) эхлүүлнэ. Launcher `os.fork()`-оор
  `tree_parent → tree_child1 → tree_grand` ба `tree_parent → tree_child2` бүтцийг үүсгэж,
  PID-уудаа нэг JSON мөр болгон хэвлээд `ttl` секунд унтна. `zombie=1` үед `tree_child2` шууд гарч,
  эцэг нь `wait()` хийдэггүй тул ZOMBIE төлөвт үлдэнэ.
* `POST /api/cleanup` launcher бүрийн process group-д `SIGTERM` (удвал `SIGKILL`) илгээнэ.
  Сервер зогсох үед мөн өөрөө цэвэрлэнэ.

### 4.5 Цөм ↔ Backend интерфэйс

**Бичих (`ti_main.c`):** нэг `write()`, хамгийн ихдээ 16 байт (шинэ мөр оролцоно). Аравтын бүхэл тоо,
`1 ≤ pid ≤ PID_MAX_LIMIT` бол хүлээн авна, эс бөгөөс `-EINVAL`. Модуль **нэг глобал "сонгосон pid"**
хадгалдаг.

**Унших:** сонгосон процесс байхгүй бол 0 байт, байвал тайлан.

**Тайлангийн формат** (`proc_bridge.parse_report()` ойлгох хэлбэр): мөр бүр нэг task, `key = [value]` хосууд.

```
command = [bash] pid = [1203] ppid = [1190] state = [1]
command = [sshd] pid = [1190] ppid = [812] state = [1]
command = [systemd] pid = [1] ppid = [0] state = [1]
command = [sleep] pid = [1630] ppid = [1203] state = [1]
```

| Түлхүүр | Заавал | Утга |
|---|---|---|
| `command` | тийм | `task->comm` |
| `pid` | тийм | `task->pid` |
| `ppid` | тийм (мод барихад) | `task->real_parent->pid` |
| `state` | тийм | тоо (kernel bit), үсэг (R S D T Z X) эсвэл үг (RUNNING …) |
| `exit_state` | үгүй | `32` бол ZOMBIE |
| `status` | үгүй | `OK` / `NOT_FOUND` / `ERROR` / `EMPTY` |

Эхний мөр нь зорилтот процесс. Дараалал чухал биш: мод `pid`/`ppid`-ээс сэргээгддэг.
Модулиас зөвхөн **шууд хүүхдүүд** шаардлагатай; ач нарыг bridge нэмэлт асуулгаар олно.

### 4.6 HTTP API

| Хүсэлт | Параметр | Хариу |
|---|---|---|
| `GET /api/query` | `pid` (текст) | 200 `OK`/`EMPTY`; 404 `NOT_FOUND`; 400 `FORMAT_ERROR`/`BOUNDARY_ERROR`; 503 модуль ачаалаагүй; 403 эрхгүй |
| `POST /api/spawn` | `ttl` (5..600 сек, анхдагч 300), `zombie` (0/1) | 201 `{parent, children[], grandchildren[], zombies[], ttl}` |
| `POST /api/cleanup` | — | 200 `{stopped_trees, parents[]}` |
| `GET /api/health` | — | `{module_loaded, proc_path, active_trees}` |

Хариу бүр JSON (алдаа ч мөн). `/api/query`-ийн бие бүтэц:

```json
{
  "ok": true, "status": "OK", "error_code": null, "message": "",
  "requested": "1203", "pid": 1203,
  "target":    {"pid": 1203, "ppid": 1190, "command": "bash", "state": 1,
                "state_name": "SLEEPING", "role": "target"},
  "ancestors": [ {"pid": 1, "command": "systemd", "role": "ancestor", "...": "..."} ],
  "children":  [ {"pid": 1630, "role": "child", "children": [ {"role": "grandchild", "...": "..."} ]} ],
  "tree":      { "pid": 1, "role": "ancestor", "children": [ "... target хүртэл, түүний дор children ..." ] },
  "counts":    {"ancestors": 3, "children": 4, "grandchildren": 0},
  "truncated": false, "raw": "<модулийн анхны текст>"
}
```

UI нь `tree`-г шууд зурж болно (root = хамгийн дээд өвөг). `role`: `ancestor|target|child|grandchild`,
`state_name`: `RUNNING|SLEEPING|STOPPED|ZOMBIE|DEAD|UNKNOWN`.

### 4.7 Зохиомжийн шийдвэрүүд

| Асуудал | Шийдэл | Шалтгаан |
|---|---|---|
| Модуль нэг глобал pid хадгалдаг | `write`+`read`-ийг `threading.Lock`-оор нэг нэгээр нь | `ThreadingHTTPServer` зэрэг хүсэлтэд нэг хүсэлтийн `write` нөгөөгийнхийг дарахаас сэргийлнэ |
| Модуль ач нарыг заавал өгөхгүй | Bridge хүүхэд бүрийг дахин асууна (дээд хязгаар 64) | Модулийн гаралтын гүнээс хамаарахгүй, UI-ийн 4 түвшинг баталгаажуулна |
| Мод ямар дарааллаар ирэхээс хамаарах | `pid`/`ppid` толиор барина | Мөрийн дараалал алдагдсан ч зөв ажиллана; мөчлөгөөс `seen` олонлогоор хамгаална |
| Модуль `0`-г хүлээж авдаггүй | `0`-г bridge өөрөө reset (`EMPTY`) гэж үзнэ | Тест 7-ийн шаардлага |
| Серверийн аюулгүй байдал | `127.0.0.1` дээр сонсоно, `/api/spawn|cleanup` зөвхөн POST, CORS толгой илгээхгүй, тоо хязгаартай (8 мод, 16 байт оролт) | Дотоод хэрэгсэл тул гаднаас хандахгүй |
| Linux цөмгүй орчинд UI хөгжүүлэх | `--mock` горим | Windows/Mac дээр UI-г модульгүйгээр туршина |

---

## 5.2 Хэрэгжилт — Backend хэсэг

### 5.2.1 `proc_bridge.py`

| Функц / класс | Үүрэг |
|---|---|
| `ProcBridge.query(pid)` | Нэг PID-ийн бүрэн хариу (JSON-д бэлэн dict). Оролтыг шалгаж, lock авч, `_collect()` дуудна |
| `ProcBridge._exchange(text)` | `os.open(O_WRONLY)` → `os.write("<pid>\n")` → `os.open(O_RDONLY)` → EOF хүртэл `os.read(4096)` (дээд хязгаар 1 MiB) |
| `parse_report(text)` | Мөр бүрээс `(\w+) = [..]` хосуудыг regex-ээр гаргаж task/status/алдааны код олно |
| `classify_state(raw, exit_state)` | Төлөвийг UI-ийн нэр болгоно |
| `build_hierarchy(records, pid)` | `ppid`-ээс ancestors, children, grandchildren, `tree` барина |
| `MockProcBridge` | `--mock`: санах ойн процессийн хүснэгт; `ti_main.c`-тэй адил `EINVAL`, хоосон тайлан |

**Төлөв ангилах.** `exit_state & 0x20` → `ZOMBIE`. Үгүй бол `state` бит: `0` → `RUNNING`, `1|2` → `SLEEPING`,
`4|8` → `STOPPED`, `0x10|0x80` → `DEAD`, сөрөг тоо (сурах бичгийн "unrunnable") → `SLEEPING`.
Үсэг (`R S D T Z X`) болон үгийг мөн хүлээн авна. UI-ийн RUNNING/SLEEPING/ZOMBIE өнгөнүүд эдгээрт тулгуурлана.

**Мод барих.** Зорилтоос `ppid` гинжээр дээш алхаж ancestors (хамгийн ойрхон нь эхэнд цуглуулж, дараа нь
root-ыг эхэнд тавина). Зорилтын `ppid`-тэй таарах бүртгэлүүд нь children, тэдний хүүхдүүд grandchildren.
Мөчлөг, давхар бүртгэлээс `seen` олонлогоор хамгаална. Модулийн тайланд ач нар ороогүй бол `_expand()` хүүхэд
бүрийн PID-ийг дахин асууж нэмнэ; 64-өөс олон хүүхэд байвал `truncated = true`.

### 5.2.2 Алдаа боловсруулалт ба тестийн төлөвлөгөөний харгалзаа

| Тест | Оролт | Хэн илрүүлэх | `status` / `error_code` | HTTP |
|---|---|---|---|---|
| 1, 2 | `$$`, `1` | модуль | `OK` | 200 |
| 3 | `/api/spawn` → parent PID | модуль + `_expand` | `OK`, 2 child, 1 grandchild | 200 |
| 4 | `999999` | модуль (хоосон тайлан) | `NOT_FOUND` | 404 |
| 5 | `-150` | модуль `EINVAL` → `_refusal()` | `ERROR` / `BOUNDARY_ERROR` | 400 |
| 6 | `abc` | модуль `EINVAL` → `_refusal()` | `ERROR` / `FORMAT_ERROR` | 400 |
| 7 | `0` | bridge | `EMPTY` | 200 |

Бусад нөхцөл: `/proc/pid` байхгүй → `ERROR` / `MODULE_NOT_LOADED` (503); эрхгүй → `PERMISSION_DENIED` (403);
таних боломжгүй гаралт → `PARSE_ERROR` (502). Модуль өөрөө татгалзсан тохиолдолд (EINVAL) шалтгааныг
bridge оролтоос нь ангилдаг: тоо биш → `FORMAT_ERROR`, сөрөг эсвэл `PID_MAX_LIMIT`-ээс их → `BOUNDARY_ERROR`.

### 5.2.3 `ui_server.py`

* **Статик файл.** `SimpleHTTPRequestHandler(directory=src/static)`; `..` замыг стандарт сан хаадаг.
* **Маршрут.** `do_GET`/`do_POST` дотор `/api/*`-ийг ялгана; буруу method-д 405 + `Allow`, үл мэдэх замд 404 (JSON).
* **`TreeRegistry`.** `subprocess.Popen([python, "-c", LAUNCHER, ttl, zombie], start_new_session=True)`
  нь launcher-ыг тусдаа process group болгоно. Сервер launcher-ийн нэг мөр JSON-ыг (`select`-ээр 5 сек хүлээж)
  уншаад бүртгэнэ. Нэгэн зэрэг 8 мод хүртэл. `cleanup()` нь `os.killpg(pgid, SIGTERM)`, 2 сек дотор гарахгүй бол `SIGKILL`.
* **Процессийн нэр.** Launcher `prctl(PR_SET_NAME)`-ээр `tree_parent`, `tree_child1`, `tree_child2`, `tree_grand` нэр
  өгдөг тул `task->comm` дээр UI-д ялгагдахуйц харагдана.
* **Зогсоох.** `Ctrl+C`, `SIGTERM` дээр `finally` блок үлдсэн модыг цэвэрлэнэ.

Ажиллуулах:

```bash
python3 src/ui_server.py            # бодит /proc/pid, http://127.0.0.1:8080
python3 src/ui_server.py --mock     # модульгүй, хуурамч процессийн хүснэгтээр
python3 src/proc_bridge.py 1203     # нэг PID-ийг JSON-оор хэвлэх (--mock боломжтой)
```

### 5.2.4 Backend-ийн туршилтын байдал

`--mock` горимд Python 3.12 дээр дараахыг шалгасан: 7 тестийн оролт бүр дээрх `status`/`error_code`/HTTP-тэй
таарсан; хоосон, зөвхөн шинэ мөр, 20 оронтой тоо, `5000000`, `+0`, `00`, `1;2` оролтууд зөв ангилагдсан;
`/api/spawn?zombie=1` → `/api/query` дээр `tree_parent` дор 2 хүүхэд (нэг нь ZOMBIE) ба 1 ач гарсан;
`/api/cleanup` дараа PID `NOT_FOUND` болсон; нэгэн зэрэг 200 хүсэлт (20 зэрэг) бүгд 200 буцсан;
`/../` замаар статик хавтсаас гарах оролдлого 404 болсон.

**Шалгаагүй:** бодит `task_info.ko`-той ажиллагаа болон `os.fork()`-д суурилсан launcher (Windows дээр `fork`
байхгүй). Эдгээрийг Ubuntu VM дээр `tests/`-ийн скриптээр баталгаажуулна.

### 5.2.5 Хязгаарлалт

* Нэг модуль = нэг глобал "сонгосон pid". Хоёр backend процесс зэрэг ажиллавал бие биедээ саад болно; нэг сервер ашиглана.
* Олон хүүхэдтэй процесс дээр ач хайх нь хүүхэд бүрт `write`+`read` нэмдэг (дээд хязгаар 64).
* Модулийн тайлангийн формат (4.5) `ti_walk.c`-тэй зөрвөл `parse_report()`-ийг л засна; бусад давхарга өөрчлөгдөхгүй.
* Сервер нэвтрэлтгүй, зөвхөн локал ашиглалтад зориулсан.
