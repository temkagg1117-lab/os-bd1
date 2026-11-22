# БД2 — Эцсийн ашиглалтын заавар (Manual)

**Linux Kernel Module for Task Information + Task Hierarchy UI**  
**Repository:** https://github.com/temkagg1117-lab/os-bd1  
**Анхаарах:** Энэ багцын `ui/server.py`, `ui/static/index.html`, `tests/test_bd2_api.py` нь БД2-ийн сайжруулсан файлууд; repository-ийн `main` дээр хараахан commit хийгдээгүй.

## 1. Дэмжих орчин ба dependency

- **Бодит kernel горим:** Ubuntu/Debian Linux VM, working kernel headers, `gcc`, `make`, root (`insmod`, `rmmod`). Kernel C compilation нь ажиллаж буй VM-ийн `uname -r`-тэй тохирох headers шаарддаг.
- **Backend/UI:** Linux, Python 3.9+ (`http.server`, `urllib`, `subprocess` зэрэг stdlib). Browser: Chromium/Chrome/Firefox. Runtime-д `pip` dependency шаардахгүй.
- **PDF build:** Python `reportlab==4.4.9`, `qrcode==8.2`, `Pillow==12.3.0` (`requirements-docs.txt`), DejaVu Sans font (Runtime-с тусдаа).
- **Screenshot test capture:** `playwright` + Chromium (report PDF үзэхэд шаардахгүй).

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y git build-essential "linux-headers-$(uname -r)" python3 python3-pip fonts-dejavu-core
python3 -m pip install -r requirements-docs.txt  # зөвшөөрөхгүй бол venv ашигла
```

PDF-д `reportlab` ба DejaVu Sans шаардлагатай, харин backend stdlib-only. macOS-д kernel module ажиллахгүй; зөвхөн PDF бэлтгэж болох бөгөөд `python3 -m pip install reportlab 'qrcode[pil]'` хийгээд DejaVuSans TTF файлуудын байрлалыг `BD2_FONT_DIR` environment variable-аар өгч болно.

## 2. Repository-д БД2-ийг оруулах

```bash
git clone https://github.com/temkagg1117-lab/os-bd1.git
cd os-bd1
git checkout -b bd2-final-improvements
# Татаж авсан OS_BD2_Submission хавтсыг repository-ийн хажууд байрлуул
python3 ../OS_BD2_Submission/scripts/apply_to_repo.py .
git status
```

**Анхаар:** Patcher нь зөвхөн шалгасан замд файл хуулна, эх `src/` C module-ийг солихгүй. `README.md` болон `docs/src/build_docs.py`-д агуулгын баталгаатай pattern байвал patch хийнэ. Patcher-ийн дараа `git diff`-ээ шалгана. Команд 0 амжилттай бол шинэ source болон docs харагдана.

## 3. MOCK горимоор UI / backend шалгах (module хэрэггүй)

```bash
python3 ui/server.py --mock
# browser: http://127.0.0.1:8000
```

UI дээр `MOCK · /proc simulation` гэсэн ялгах тэмдэг гарна. PID=1 сонгоод `Харуулах` дарна. `Мод үүсгэх` товч нь жинхэнэ Linux sleep process group үүсгэдэг; дуусгахаа марталгүй `Цэвэрлэх` дарна. `depth 0..6`, `max 1..500`. Тестийн demo group хамгийн ихдээ 3.

## 4. Бодит kernel module горим

```bash
make -C src
sudo insmod src/task_info.ko
ls -l /proc/pid
echo 1 | sudo tee /proc/pid
cat /proc/pid
python3 ui/server.py
# browser: http://127.0.0.1:8000
```

`cat /proc/pid`-ийн эхний мөр `command = [systemd/...] pid = [1] state = [N]` форматтай, бусад мөрүүдэд `state_name`, `ppid`, `nchildren`, `ancestor/child` мэдээлэл байна. Нэр, PID, child тоо тухайн OS/session-аас хамаарч өөр өөр байна; screenshot-тэй яг тэнцүү байх ёстой гэж үзэхгүй.

Бодит module-тэй UI сервер ажиллуулахад `/proc/pid` руу бичих/унших permission хэрэгтэй. Төслийн default `proc_create(..., 0666, ...)` тул зохих Linux дээр энгийн хэрэглэгч хандаж болох ч байгууллагын host policy-оор өөр байж болно. Хэрэв permissions error гарвал зохих VM-д sudo эрх/permission шалгана. Public network руу `--host 0.0.0.0` байдлаар expose хийхгүй.

## 5. Туршилт ба нотолгоо

```bash
python3 -m unittest discover -s tests -p 'test_bd2_api.py' -v
# MOCK: /proc дээр ажиллах, шинэ 21 suite

# зөвхөн Linux VM, module суусан үед:
sudo ./tests/run_module_tests.sh
python3 tests/test_bd2_api.py --module

# шалгах бусад команд:
python3 -m py_compile ui/server.py
bash -n tests/run_module_tests.sh
uname -a
python3 --version
```

`--module` test-д kernel module-ийн `/proc/pid` байх ёстой. Мөн original BD1-ийн `python3 tests/test_ui_api.py --module` ажиллуулбал backwards compatibility regression болно. Kernel log-д `BUG`, `Oops`, `WARNING`, `RCU` хайж шалгана. Хамгийн сүүлийн бодит logs-ийг `docs/evidence/` руу хадгалж, тайлан дахь NOT VERIFIED-ийг засна.

## 6. Түгээмэл алдаа

| Шинж | Шалтгаан | Шийдвэр |
|---|---|---|
| `MODULE_NOT_LOADED` | `/proc/pid` байхгүй | `sudo insmod src/task_info.ko` эсвэл `--mock` |
| `PERMISSION` | `/proc/pid` зөвшөөрөлгүй | `ls -l /proc/pid`, эрх / sudo шалгах |
| `BAD_PID` | хоосон, сөрөг, үсэг, хязгаар давсан PID | 1..4194304 бүхэл тоо оруулах |
| `BAD_OUTPUT` | output malformed, эсвэл өөр процесс global PID-г сольсон | өөр writer-уудыг зогсоож дахин оролдох |
| `DEMO_LIMIT` | 3 demo group аль хэдийн бий | `Цэвэрлэх` дарах |
| `make: ... /build ...` | kernel headers таарахгүй | `linux-headers-$(uname -r)` суулгах |
| `Address already in use` | port 8000 эзлэгдсэн | `python3 ui/server.py --port 8001` |

## 7. Reset, Cleanup, Unload

- `Reset` нь UI-ийн талбар, график, auto-refresh-ийг цэвэрлэнэ; Linux process-ийг **алахаас өөр үйлдэл**.
- `Цэвэрлэх` нь UI-аас үүсгэсэн demo process group-уудыг зогсооно.
- Browser-ийг хаасны дараа server-ийн терминалд `Ctrl+C`, дараа нь `sudo rmmod task_info`.
- `sudo rmmod task_info` хийхээс өмнө server-ээ зогсоох нь зөв.

## 8. PDF ба GitHub release бэлтгэх

```bash
python3 docs/build_bd2.py
# PDF builder-д screenshot автоматаар гаргахгүй; docs/evidence/real_mock_ui.png-г уншина.
# Албан review / kernel screenshot/үнэн test log-уудыг дараа нь нэмнэ.
```

Release-г `v2.0.0` гэж сонгох бол багийн бүх гишүүн зөвшөөрсөн, VM regression log/screenshot болон албан review бүрэн байх шаардлагатай. Тэгээд `git commit`, `git tag -a v2.0.0`, `git push`, GitHub Release үүсгэж, Poster-ийн QR-ийг яг тэр release-ийн URL-тай дахин build хийнэ. Final report-д release commit SHA/tag-ийг ижил бичнэ.

## 9. Expected result vs actual

Expected: UI-д real/mock mode зөв ялгарч, PID query буцааж, SVG мод зурж, invalid request-д 400, module байхгүй бол 503, unauthorized file access-д 404, demo limit-д 429. **Actual:** 2026-11-21-д шинэ mock suite 21/21 PASS, screenshot `docs/evidence/real_mock_ui.png` дээр marker `MOCK`. **Kernel module actual:** энэ орчинд туршаагүй — VM нотолгоо шаардлагатай.
