# MS Teams БД2 — Final projects постын бэлэн загвар

**Гарчиг:** `[Хуваарилалтын код баталгаажуулах] — Linux Kernel Module for Task Information • Final`

**Тайлбар:**

БД1-ийн `/proc/pid`-д тулгуурласан Task Hierarchy төслийг GitHub review болон source-code audit-ийн мөрөөр сайжруулав:

1. Python backend-ийн input validation, module report parser болон HTTP error handling сайжруулав.
2. Static path хамгаалалт (symlink traversal) нэмэв; demo process group-д resource cap тогтоов.
3. SVG UI-г mode indicator, node/query metric, алдааны дэлгэрэнгүй мэдээлэлтэй шинэчлэв.
4. Reviewer responses, regression test, Final Report, Manual-ийг нэгтгэв.

**Автомат тест:** MOCK mode 21/21 PASS (2026-11-21; *kernel module тест биш*).

**Үндсэн материал:** `[код]_Poster.pdf`  
**Нэмэлт материал:** `[код]_Final_Report.pdf`, `[код]_Manual.pdf`  
**GitHub final release:** `[БОДИТ v2.0.0 release URL энд оруулна]`  
**Туршиж үзэх:** README-ийн BD2 Quick Start, Manual §3–§5.  

**Нийтлэхээс өмнө:** албан ёсны Review PDF-ийн шүүмжүүдийг нэмэх, бодит kernel VM дээр `run_module_tests.sh` болон `test_bd2_api.py --module` ажиллуулах, бодит screenshot оруулах, release tag үүсгээд poster QR-г шинэчилнэ.
