# БД2 — Reviewer Comments and Responses

**Төсөл:** Linux Kernel Module for Task Information / Task Hierarchy  
**Repository:** https://github.com/temkagg1117-lab/os-bd1  
**Эх шалгалтын commit:** `0cb46da0c42eefd69121b81e9a889071bc309eb9` (`main`)  
**Эх сурвалж:** GitHub PR #3-ийн бичмэл review comments (2026-10-31), https://github.com/temkagg1117-lab/os-bd1/pull/3  
**Тайлбар:** Эдгээр нь бодит GitHub техникийн comment. Хичээлийн **албан ёсны peer-review PDF** өгөөгүй тул түүний шүүмжийг энд зохиож нэмээгүй.

Priority = Critical / Major / Minor / Suggestion. Шийдвэр = Зөвшөөрсөн / Хэсэгчлэн зөвшөөрсөн / Зөвшөөрөөгүй.

| № | Эх сурвалж / бодит шүүмжийн агуулга | Priority | Шийдвэр | Өөрчлөлт, нотолгоо, төлөв |
|---|---|---|---|---|
| R-01 | `scripts/commit_member.sh`-д өмнө нь `|| true`, `checkout -B` байсан нь fetch алдааг нууж, branch reset хийх аюултай. | Critical | Зөвшөөрсөн | **БД1 `main` дээр засагдсан**: одоогийн скрипт `set -euo pipefail`, `git fetch` амжилтгүй бол зогсоно, байгаа branch-ийг reset хийхгүй, зөвхөн `--ff-only` merge хийдэг. БД2-д скриптийг эвдэлгүй хадгалсан. Баталгаажуулалт: GitHub-ийн `scripts/commit_member.sh` эх кодын шалгалт. Бодит remote failure сценарийг энд туршаагүй. |
| R-02 | PDF generator дахь `<II|IV|V>` мэт текстийг ReportLab `Paragraph` HTML markup мэт ойлгож болзошгүй. | Major | Зөвшөөрсөн | `scripts/apply_to_repo.py` patch нь allocation `CODE`-ийг `xml.sax.saxutils.escape`-ээр escape хийж Paragraph-д өгнө. PDF build-ийн бодит баталгаажуулалтыг репогийн эх файлууд дээр patch ажиллуулсны дараа хийнэ. |
| R-03 | Team жагсаалтад 5 гишүүн байхад M1-M6 нийт 6 гишүүнтэй. | Major | Зөвшөөрсөн | **БД1 `main` дээр засагдсан**: `TEAM` жагсаалтад 6 гишүүн байгаа нь эх кодоор батлагдсан. |
| R-04 | ReportLab + DejaVu фонт шаардаж байхад README-д dependency байхгүй/гаднын сангүй гэж бичсэн. | Major | Зөвшөөрсөн | `README_BD2.md` болон `BD2_Manual.md`-д Python runtime vs PDF build dependency-г салгаж бичсэн; `scripts/apply_to_repo.py` README-д тодруулгыг хавсаргана. |
| R-05 | `docs/src/build_docs.py`-ийн `report()` дотор `{II-4-2}` нь хувьсагч биш, `NameError` үүсгэнэ. | Critical | Зөвшөөрсөн | БД2 patch нь `escape(CODE)` ашиглана. Нэмж current source-ийн `RESULTS` олон мөрөнд тасарсан Python literal-уудыг syntax-safe текстээр солино. `ast.parse` шалгалтыг patcher дотор хийдэг. БД1 эх генераторын PDF дахин үүсгэлт репо дээр гүйцэтгэсний дараа нотлогдоно. |

## Нэмэлт хөгжүүлэгчийн code audit (албан reviewer биш)

| № | Илэрсэн асуудал | Priority | Шийдвэр | БД2-ийн засвар | Тест |
|---|---|---|---|---|---|
| A-01 | `max=0` болон `max=501`-ийг сервер 1 эсвэл 500 болгон чимээгүй clamping хийдэг. | Major | Зөвшөөрсөн | Хязгаараас гарсан тоонд `400 BAD_PARAM` буцаана. | `test_invalid_depth_or_max_fails_not_clamped` |
| A-02 | Буруу/дутуу module report-оос `KeyError`/`ValueError` гарвал `500 INTERNAL` болон exception текст хэрэглэгчид ил болж болно. | Major | Зөвшөөрсөн | Strict parser, `502 BAD_OUTPUT`, дотоод exception-ий текстийг HTTP-д ил гаргахгүй. | `test_parse_rejects_malformed_report`, `test_parse_rejects_mismatched_pid` |
| A-03 | Static замын `startswith(STATIC)` шалгалт нь symlink эсвэл ижил угтвартай path-ыг аюулгүй гэж эндүүрэх боломжтой. | Critical | Зөвшөөрсөн | `os.path.realpath` + `os.path.commonpath` ашиглаж, symlink escape-ийг хориглосон. | `test_static_symlink_escape_blocked`, `test_static_traversal` |
| A-04 | `max_nodes` яг хүрэхэд хүүхэд орхигдоогүй байсан ч `truncated=True` болж болно. | Minor | Зөвшөөрсөн | Өгөгдөл үнэхээр алдагдсан (`cut` / module report truncation) үед л анхааруулна. | `test_depth_zero_has_no_descendants` |
| A-05 | Demo process-ийг хязгааргүй удаа үүсгэж, backend-ийн нөөц дуусгаж болно. | Major | Зөвшөөрсөн | Идэвхтэй demo process group хамгийн ихдээ 3; түүнээс хойш `429 DEMO_LIMIT`. Cleanup lock болон SIGTERM/SIGKILL fallback. | `test_demo_group_cap`, `test_spawn_and_cleanup` |

**Шүүмжийг зөвшөөрөөгүй мөр:** Энэ repository-д унших боломжтой бичмэл review-уудаас татгалзсан санал илрээгүй. Тиймээс зохиомол “татгалзсан” мөр нэмээгүй. Албан peer-review PDF-ийг хүлээн авсны дараа тухайн санал бүрийг (татгалзсан бол техникийн үндэслэлтэйгээр) энэ хүснэгтэд бүртгэнэ.

**Test evidence:** `docs/evidence/mock_test_log.txt`, `docs/evidence/test_summary.json`, `docs/evidence/real_mock_ui.png`. Эдгээр нь шинэ хувилбарыг MOCK горимд бодитоор ажиллуулсан нотолгоо бөгөөд kernel module-ийн баталгаа **биш**.
