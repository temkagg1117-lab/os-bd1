# F.CSM302 БД2 — Final Improvement Package

БД1-ийн `temkagg1117-lab/os-bd1` repository-г үргэлжлүүлж, kernel C module-ийн үндсэн протоколыг хадгалсан BD2 backend/UI/test/docs сайжруулалтын багц. Төслийн багийн нэр/ID мэдээллийг `docs/BD2_Final_Report.md`-д бичсэн; хуваарилалтын кодыг багшийн баталгаатай эх сурвалжтай тулган шалгах шаардлагатай.

## Нэг дор ажиллуулах

```bash
# Энэ хавтсыг OS_BD2_Submission нэрээр repository-ийн хажууд байрлуулна.
cd os-bd1
git checkout -b bd2-final-improvements
python3 ../OS_BD2_Submission/scripts/apply_to_repo.py .
python3 -m unittest discover -s tests -p 'test_bd2_api.py' -v
python3 ui/server.py --mock
# Дараа нь http://127.0.0.1:8000
```

**Урьдчилан туршсан:** standalone patch-ийн Python 3.13.5 Linux MOCK тест 21/21 PASS. Энэ нь бодит Linux kernel module (C) regression **биш**. Суулгасны дараа original `tests/test_ui_api.py` болон kernel test-ийг дахин ажиллуул.

## Багцын файлууд

- `ui/server.py` — input, output protocol parser, resource limit, static path security, API алдаанууд.
- `ui/static/index.html` — шинэ task hierarchy visualization, real/mock badge, node/query metrics, reset, demo.
- `tests/test_bd2_api.py` — шинэ 21 unittest, mock болон `--module` горим.
- `docs/BD2_Reviewer_Responses.md` — GitHub PR #3-ий бодит review + тусдаа self-audit, шийдвэр/нотолгоо.
- `docs/BD2_Final_Report.md` + `docs/BD2_Final_Report.pdf` — 8 бүлэгтэй дүгнэлт, өмнөх/дараах шинжилгээ, нотолгоо, хязгаарлалт.
- `docs/BD2_Manual.md` + `docs/BD2_Manual.pdf` — Linux VM build/run, regression, troubleshooter.
- `docs/BD2_Poster.pdf` — нэг нүүр poster, screenshot, QR (release URL баталгаажаагүй учир repo QR).
- `docs/evidence/real_mock_ui.png` — бодитоор ажиллуулсан шинэ UI-ийн **MOCK** screenshot.
- `docs/evidence/mock_test_log.txt` — 21 test-ийн бодит output.
- `docs/build_bd2.py` — PDF generator (ReportLab, qrcode, DejaVu Sans).
- `scripts/apply_to_repo.py` — GitHub branch-д оруулахдаа шинэ source-г хуулах болон BD1 PDF generator syntax/NameError засварлах script.

## Dependency-ийн үнэн зөв ялгаа

Runtime backend/UI: Python стандарт сан + Linux `/proc` (pip сан шаардлагагүй). Kernel build: kernel headers, gcc, make. **PDF үүсгэх**: `reportlab==4.4.9`, `qrcode==8.2`, `Pillow==12.3.0` (see `requirements-docs.txt`), DejaVu Sans. **Screenshot авах**: Playwright + Chromium (зөвхөн бэлтгэл/туршилт).

## Анхаарах зайлшгүй нөхцөлүүд

Энэ package-ийг **GitHub-д хараахан push хийгээгүй**: интеграц branch create хүсэлтэд 403 буцаасан. Нэмж хичээлийн албан peer-review PDF, багшийн баталсан allocation code, бодит kernel VM regression screenshot/log, release URL байхгүй. Иймээс 100% оноог батлах боломжгүй; үлдсэн ажлыг Manual §5, §8, Teams post-д тэмдэглэсэн. **Тест, screenshot, release URL-ийг зохиогоогүй**.

## PDF dependency lock (verified environment)

`python3 -m pip install -r requirements-docs.txt`; screenshot replay optional: `python3 -m pip install -r requirements-screenshot.txt`. These versions reflect the environment where the three PDFs were generated, not an assertion about older Linux distributions.
