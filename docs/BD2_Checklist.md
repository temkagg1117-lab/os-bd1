# F.CSM302 БД2 — зааврын checklist ба үнэн бодит төлөв

Нотолгоо: `OS_BD2_Guide.pdf` х. 4–6 (post, final release, checklist). ✅ = тухайн багцад баталгаажсан; ⏳ = багийн VM, GitHub, Teams дээр дуусгах шаардлагатай.

| БД2 шаардлага | Төлөв | Нотолгоо / дараагийн алхам |
|---|---|---|
| Үндсэн функц хадгалагдсан | ✅ (source compatibility), ⏳ (kernel runtime) | C module-ийн файлууд patch-д солигдоогүй; VM test зайлшгүй |
| Critical/Major асуудлыг шийдсэн эсвэл үндэслэлтэй тайлбарласан | ✅ (code + review бүртгэл), ⏳ (repo дээр баталгаажуулах) | `BD2_Reviewer_Responses.md`, шинэ backend; BD1 generator-ийн patch-ийг бодит репо дээр ажиллуулах |
| UI бодит өгөгдөлтэй нийцсэн | ✅ (Linux `/proc` MOCK), ⏳ (module) | `docs/evidence/real_mock_ui.png`; kernel screenshot авна |
| Regression ба нэмэлт тест | ✅ MOCK 21/21, ⏳ kernel regression | `mock_test_log.txt`; `sudo ./tests/run_module_tests.sh`, `python3 tests/test_bd2_api.py --module` |
| Reviewer Responses бүрэн | ✅ олдсон GitHub PR #3 comment-д, ⏳ official peer-review PDF-д | Албан PDF ирвэл үгчлэн нэмж ангилна |
| Poster нэг нүүр, уншигдахуйц | ✅ | `BD2_Poster.pdf` (A3 landscape, нэг нүүр, MOCK screenshot) |
| QR код зөв final release рүү орно | ⏳ | Одоогийн QR repository руу ордог, release үүсгэсэн **дараа** `python3 docs/build_bd2.py --release-url URL` |
| Final Report, Manual, GitHub нэг commit/tag-тай | ⏳ | GitHub integration 403. `git status`, commit/push/tag, Release, report final SHA шинэчлэх |
| README Quick Start, dependency version, тест өгөгдөл | ✅ bundle-д; ⏳ GitHub-д суулгах | `README_BD2.md`, `requirements-docs.txt`, `docs/BD2_Manual.md`, `tests/` |
| Secret, хувийн файл, build artifact байхгүй | ⏳ final repo audit | `git ls-files`, `git status --ignored`, `git grep -niE 'password|token|secret'` шалга |
| MS Teams “БД2 - Final projects” пост | ⏳ | `BD2_Teams_Post.md` загварыг PDF/Release бэлэн болсны дараа нийтлэх |

**Зөв дараалал:** bundle-ийг Git branch-д оруулах → tests/VM regression → official peer review-ыг нэгтгэх → report ба poster-ийг бодит нотолгоогоор шинэчлэх → GitHub tag/release → QR шинэчлэх → Final Report SHA-г release-тэй тохируулах → Teams пост.
