#!/usr/bin/env python3
"""build_docs.py - generates docs/BD1_Report.pdf and docs/BD1_Manual.pdf (Member 5).
Usage: python3 docs/src/build_docs.py   (needs reportlab + DejaVu fonts)
Edit TEAM / CODE below, paste real results into the RESULTS list, then rebuild."""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table,
                                TableStyle, Preformatted, KeepTogether)

FD = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("S", FD + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("SB", FD + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("M", FD + "DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily("S", normal="S", bold="SB", italic="S", boldItalic="SB")

CODE = "<II|IV|V>-<цаг>-2"
TEAM = ["1. Тэмүүжин (B242270046)", "2. Цогтбаяр (B242270133)", "3. Бямбасүрэн (B241940082)",
        "4. Гантулга (B190910023)", "5. Гантүшиг (B231940130)", "6. Ганболд (B241910023)"]
REPO = "https://github.com/temkagg1117-lab/os-bd1"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)

B = ParagraphStyle("b", fontName="S", fontSize=9.5, leading=14, spaceAfter=4)
H1 = ParagraphStyle("h1", parent=B, fontName="SB", fontSize=14, leading=18, spaceBefore=10, spaceAfter=6, textColor=colors.HexColor("#1f3a6e"))
H2 = ParagraphStyle("h2", parent=B, fontName="SB", fontSize=11, leading=15, spaceBefore=6, spaceAfter=3)
T = ParagraphStyle("t", parent=B, fontName="SB", fontSize=22, leading=28, alignment=1, spaceAfter=10)
C = ParagraphStyle("c", parent=B, alignment=1, fontSize=11, leading=16)
CELL = ParagraphStyle("cell", parent=B, fontSize=8.5, leading=11, spaceAfter=0)
CODEST = ParagraphStyle("code", fontName="M", fontSize=7.8, leading=10, backColor=colors.HexColor("#f2f4f8"),
                        borderPadding=4, spaceAfter=6)


def P(t, s=B): return Paragraph(t, s)
def bullets(items): return [P("• " + i) for i in items]
def code(t): return Preformatted(t.strip("\n"), CODEST)
def table(rows, widths, head=True):
    data = [[Paragraph(str(c), CELL) for c in r] for r in rows]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if head else 0)
    st = [("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#9aa4b2")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    if head: st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3e9f5")))
    t.setStyle(TableStyle(st)); return t


def build(path, title, story):
    def foot(c, d):
        c.saveState(); c.setFont("S", 8); c.setFillColor(colors.grey)
        c.drawString(20 * mm, 10 * mm, f"F.CSM302 Үйлдлийн систем • Бие даалт 1 • {CODE} • {title}")
        c.drawRightString(190 * mm, 10 * mm, str(d.page)); c.restoreState()
    SimpleDocTemplate(path, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                      bottomMargin=18 * mm, title=title, author="OS BD1 team").build(story, onFirstPage=foot, onLaterPages=foot)


# ================================================================= REPORT ==
RESULTS = [  # (ID, оролт, хүлээгдсэн, БОДИТ үр дүн) - VM дээр ажиллуулсны дараа "Бодит" баганыг бөглөнө
    ("T1", "echo $$ > /proc/pid; cat /proc/pid", "command = [bash] pid = [N] state = [n]", "Давсан: command =[bash] pid = [5554]
state = [1]"),
    ("T2", "pid 1", "pid = [1], ancestor байхгүй", "Давсан
(run_module_tests.sh
T2)"),
    ("T3", "ppid шалгалт", "/proc/$$/stat-ийн ppid-тэй тэнцүү", "Давсан: ppid = [5543]"),
    ("T4", "2 sleep & үүсгэх", "2 child: мөр", "Давсан: хоёр child:
мөр жагсаагдсан"),
    ("T5", "kill -STOP sleep", "state = [4]", "state = [260], 260 =
TASK_WAKEKILL (256) +
__TASK_STOPPED (4), bit
4 тавигдсан. Эхний тест
яг [4] хүлээсэн тул унасан, bit-ээр шалгахаар
засав"),
    ("T6", "echo 4194303 > /proc/pid", "read = 0 byte", "Давсан: 0 байт, dmesg:
no task with pid
4194303"),
    ("E1-E4", "abc, 0, -5, 99999999999, хоосон, 12abc", "write амжилтгүй (EINVAL), pid өөрчлөгдөхгүй", "Давсан: бүгд Invalid
argument, өмнөх pid
хэвээр. Хоосон оролт:
bash 0 байт бичихэд
write() хийдэггүй тул
module хүртэл ирээгүй
(тестийн алдаа), зайгаар () дахин шалгана"),
    ("R1", "rmmod / insmod", "/proc/pid устаж, дахин үүснэ", "Давсан: rmmod-ийн дараа файл алга, insmod
дахин ажилласан"),
    ("K1", "dmesg", "oops/BUG/RCU warning байхгүй", "Давсан: dmesg-д зөвхөн
task_info мэдээлэл,
oops байхгүй"),
]


def report():
    s = []
    s += [Spacer(1, 40 * mm), P("F.CSM302 ҮЙЛДЛИЙН СИСТЕМ", C), P("БИЕ ДААЛТ 1 — СУДАЛГАА, ХЭРЭГЖИЛТ, ТУРШИЛТЫН ТАЙЛАН", C), Spacer(1, 12 * mm),
          P("Linux Kernel Module for Task Information", T), P("Сурах бичиг: Silberschatz, Operating System Concepts (10th ed.), Chapter 3 Processes — Programming Project 2", C),
          Spacer(1, 8 * mm), P(f"Хуваарилалтын код: <b>{II-4-2}</b>", C), P("UI дүрслэл: Task hierarchy", C), Spacer(1, 8 * mm)]
    s += [P(m, C) for m in TEAM] + [Spacer(1, 6 * mm), P(f"GitHub: {REPO}", C), PageBreak()]

    s += [P("Хураангуй", H1),
          P("<b>Асуудал.</b> Үйлдлийн системийн kernel дотор task (process)-ийн удирдлагын бүтэц болох <font name='M'>task_struct</font>-ийг "
            "хэрэглэгчийн орон зайгаас аюулгүй, давтан туршиж болохоор харах хэрэгтэй. "
            "<b>Шийдэл.</b> <font name='M'>/proc/pid</font> файлаар pid хүлээн авч command, pid, state-ийг (номын шаардлага) болон parent, ancestors, "
            "children-ийг (Task hierarchy UI-д) буцаадаг Linux kernel module, мөн түүнийг бодит цагт SVG мод болгон зурдаг web UI. "
            "<b>Туршилт.</b> Shell дээр 9 бүлэг үндсэн ба захын тест, backend-ийн 18 автомат тест (mock горимд 18/18 OK). "
            "Бодит VM дээрх дүнг §8-д бүртгэнэ.")]
    s += [P("1. Удиртгал", H1),
          P("<b>Зорилго.</b> Номын Project 2-ыг бүрэн хэрэгжүүлж, хэрэглэгч өөр PID, гүн, хязгаараар туршиж болох Task hierarchy UI-тэй холбох. "
            "<b>Ач холбогдол.</b> Process control block, process tree, kernel–user харилцаа (/proc) гэсэн Chapter 3-ын гол ойлголтуудыг нэг ажилд "
            "хамааруулж, kernel дэх бодит өгөгдөл дээр ажиглах боломж олгоно. "
            "<b>Хамрах хүрээ.</b> Linux 5.x/6.x, x86-64; хамгийн багадаа command, pid, state; нэмэлтээр parent, ancestors, children. "
            "Thread-ийн дотоод (tid) түвшин, namespace-ийн бүрэн дэмжлэг хамаарахгүй.")]
    s += [P("2. Сурах бичгийн шаардлага", H1),
          P("Project 2-ын шаардлагыг (Silberschatz, 10th ed., P-15…P-17) дараах байдлаар хангасан:"),
          table([("Номын шаардлага", "Хэрэгжилт"),
                 ("<font name='M'>echo \"1395\" > /proc/pid</font> — pid бичих", "<font name='M'>ti_write()</font>: kmalloc → copy_from_user → <font name='M'>kstrtol()</font> → kfree; зөв утгыг глобал хувьсагчид хадгална"),
                 ("<font name='M'>cat /proc/pid</font> — command, pid, state унших", "Эхний мөр яг номын формат: <font name='M'>command = [bash] pid = [1395] state = [1]</font>"),
                 ("<font name='M'>find_vpid()</font> + <font name='M'>pid_task(…, PIDTYPE_PID)</font>", "<font name='M'>ti_build_report()</font> дотор"),
                 ("Хүчингүй pid → pid_task NULL → read 0 буцаах", "NULL үед 0 буцаана (<font name='M'>simple_read_from_buffer</font>-д len=0), dmesg-д тэмдэглэнэ"),
                 ("Санах ойн зөв удирдлага (kmalloc/kfree)", "Бүх замд kfree; алдааны салаанд бас чөлөөлнө"),
                 ("Chapter 2-ын /proc entry", "<font name='M'>proc_create()</font> / <font name='M'>remove_proc_entry()</font>")],
                [62, 108])]
    s += [P("3. Онолын үндэс", H1),
          P("<b>Process control block.</b> Linux-т PCB нь <font name='M'>struct task_struct</font> (&lt;linux/sched.h&gt;). "
            "Үүнд <font name='M'>comm</font> (командын нэр, 16 байт), pid/tgid, state, <font name='M'>real_parent</font>, <font name='M'>children</font>, <font name='M'>sibling</font> талбарууд байна."),
          P("<b>Process state.</b> Номын Figure 3.2-ын new/ready/running/waiting/terminated төлвүүд Linux-д <font name='M'>TASK_RUNNING(0)</font>, "
            "<font name='M'>TASK_INTERRUPTIBLE(1)</font>, <font name='M'>TASK_UNINTERRUPTIBLE(2)</font>, <font name='M'>__TASK_STOPPED(4)</font>, "
            "<font name='M'>__TASK_TRACED(8)</font> болон exit_state (<font name='M'>EXIT_ZOMBIE</font>, <font name='M'>EXIT_DEAD</font>) байдлаар илэрнэ. "
            "Kernel 5.14-өөс талбарын нэр <font name='M'>state</font> → <font name='M'>__state</font> болсон тул хувилбарын нөхцөлөөр зохицуулав."),
          P("<b>Process tree.</b> fork() бүрээр parent–child холбоо үүснэ; init (pid 1) бол үндэс (Figure 3.8). Kernel процессуудыг "
            "<font name='M'>children</font>/<font name='M'>sibling</font> холбоост жагсаалтаар хадгалдаг. Энэ ажилд parent-ийг <font name='M'>real_parent</font>-ээс, "
            "child-ийг <font name='M'>for_each_process()</font> дундаас <font name='M'>real_parent->tgid == target->tgid</font> нөхцөлөөр олно "
            "(tasklist_lock нь module-д export хийгдээгүй тул RCU-аар уншина)."),
          P("<b>RCU.</b> <font name='M'>rcu_read_lock()</font> дотор task_struct-ийг унших нь аюулгүй; хугацаа уртасгахгүйн тулд kmalloc-ийг lock-оос өмнө хийж, "
            "доторх нь sleep хийхгүй (scnprintf-ээр урьдчилан хуваарилсан buffer-т бичнэ)."),
          P("<b>/proc.</b> Хэрэглэгчийн орон зайд kernel өгөгдлийг файл маягаар гаргах механизм. Бичих үед <font name='M'>copy_from_user</font>, унших үед "
            "<font name='M'>simple_read_from_buffer</font> (→ copy_to_user) ашиглана.")]
    s += [P("4. Системийн зохиомж", H1),
          P("Компонент ба өгөгдлийн урсгал:"),
          table([("Давхарга", "Файл", "Үүрэг"),
                 ("Browser UI", "ui/static/index.html", "PID/гүн оролт, SVG мод, алдааны мэдээлэл"),
                 ("Backend (HTTP)", "ui/server.py", "/api/tree, /api/query; мод бүрийн node-д <i>write pid → read report</i>; Lock-оор хамгаална"),
                 ("/proc интерфейс", "src/ti_main.c", "/proc/pid: write (шалгалт), read"),
                 ("Walker", "src/ti_walk.c", "task_struct → тайлан (RCU)"),
                 ("Kernel", "task_struct", "Бодит процессын мэдээлэл")], [32, 45, 93]),
          Spacer(1, 3 * mm),
          P("<b>Гаралтын формат</b> (мөр бүр <font name='M'>key = [value]</font>):"),
          code("""command = [bash] pid = [1395] state = [1]          <- номын формат
state_name = [TASK_INTERRUPTIBLE]
ppid = [1200] parent_command = [sshd]
nchildren = [2]
ancestor: pid = [1] command = [systemd] state = [1]    (үндэс эхэнд)
child: pid = [1400] command = [sleep] state = [1]
truncated = [children]                                (>128 child үед)"""),
          P("<b>UI мод үүсэх дараалал.</b> UI сонгосон PID-г асууж ancestor-уудыг авна → тэр node-ийн <font name='M'>child:</font> мөр бүрээр дахин асууж "
            "гүн (depth) хүртэл доош нь өргөтгөнө (node-ийн дээд тоо хязгаартай). Тиймээс зурагдсан мод бүхэлдээ module-ийн бодит хариултаас баригдана.")]
    s += [P("5. Хэрэгжилт", H1),
          P("<b>5.1 /proc интерфейс (ti_main.c).</b> 0666 эрхтэй <font name='M'>proc_create(proc_name,…)</font>; kernel ≥5.6-д <font name='M'>struct proc_ops</font>, "
            "түүнээс өмнө <font name='M'>file_operations</font>. Write-ийн шалгалт: урт 1..16; <font name='M'>strim</font> + <font name='M'>kstrtol</font>; "
            "утга 1..PID_MAX_LIMIT; алдаанд <font name='M'>-EINVAL</font> ба <font name='M'>pr_warn</font>. Глобал pid-г mutex хамгаална."),
          code("""rv = kstrtol(strim(k_mem), 10, &val);
if (rv || val <= 0 || val > PID_MAX_LIMIT) return -EINVAL;
mutex_lock(&ti_lock); ti_pid = val; mutex_unlock(&ti_lock);"""),
          P("<b>5.2 Walker (ti_walk.c).</b> <font name='M'>pid_task(find_vpid(pid), PIDTYPE_PID)</font>; NULL бол 0. "
            "Ancestor-уудыг ≤64 шатлал дээш алхаж цуглуулаад үндэс эхэнд хэвлэнэ; child-ийг ≤128 мөр. Бүх зүйл нэг <font name='M'>rcu_read_lock</font> дотор."),
          code("""task = pid_task(find_vpid(pid), PIDTYPE_PID);
if (!task) { rcu_read_unlock(); return 0; }
for_each_process(p)
    if (p != task->group_leader && rcu_dereference(p->real_parent)->tgid == task->tgid) ..."""),
          P("<b>5.3 Backend ба UI.</b> Python stdlib HTTP сервер 127.0.0.1-д; API: <font name='M'>/api/query</font>, <font name='M'>/api/tree</font>, "
            "<font name='M'>/api/spawn</font> (туршилтын sleep мод), <font name='M'>/api/cleanup</font>. Алдаа: BAD_PID(400), NO_SUCH_PID(404), "
            "MODULE_NOT_LOADED(503), PERMISSION(403). <font name='M'>--mock</font> горим нь module-гүй машин дээр UI үзэх зориулалттай бөгөөд UI дээр шар тэмдэглэгээтэй."),
          P("<b>5.4 GitHub ажиллагаа.</b> (багийнхан бөглөнө)"),
          table([("Гишүүн", "Салбар", "Commit тоо", "PR / Review", "Issue"), ("Тэмүүжин", "m1-proc-interface", "8", "3", "1"), ("Цогтбаяр", "m2-walker", "4, "3, "0"),
                 ("Бямбасүрэн", "m3-backend", "1", "0", "0"), ("Гантулга", "m4-ui", "1", "0", "0"), ("Гантүшиг", "m5-tests", "1", "1", "0"), ("Ганболд", "m6-docs", "1", "0", "0")], [22, 45, 28, 40, 35])]
    s += [P("6. Туршилт ба UI дүрслэл", H1),
          P("UI дээр өөрчилж турших зүйлс ба ажиглах зүйл:"),
          table([("Өөрчлөх", "Ажиглах"),
                 ("PID (1, $$, 2, өөр process)", "Ancestor гинж дээрээс доош; сонгосон node хар хүрээтэй"),
                 ("Depth 0..6, node max 1..500", "Descendant-ын гүн; хязгаарт хүрвэл тэмдэглэл (+ тэмдэг, “мод бүрэн биш”)"),
                 ("“Mод үүсгэх” (гүн 1..3, салаа 1..4)", "Шинэ бодит process мод; <font name='M'>ps -ef --forest</font>-той харьцуулах"),
                 ("Автомат шинэчлэл (2 сек)", "Процесс <font name='M'>kill</font> хийхэд мод өөрчлөгдөх (бодит цаг)"),
                 ("Node дээр дарах", "Тэр PID-ээр дахин асуулт; drill-down"),
                 ("Буруу оролт (abc, 0, 4194303)", "Улаан алдааны мэдээлэл, дүрслэл эвдрэхгүй"),
                 ("Reset", "Бүх оролт, зураг цэвэрлэгдэнэ")], [60, 110]),
          P("Өнгө: ногоон=RUNNING(0), цэнхэр=INTERRUPTIBLE(1), улбар шар=UNINTERRUPTIBLE(2), саарал=STOPPED/TRACED(4,8), улаан=ZOMBIE/DEAD.")]
    s += [P("7. Туршилтын арга", H1),
          P("<b>Орчин.</b> Ubuntu 22.04/24.04 VM (kernel: 6.12.113+deb13-amd64), gcc, make, linux-headers, Python 3. "
            "<b>Өгөгдөл.</b> Хатуу кодлосон ганц өгөгдөл байхгүй: $$, pid 1, sleep процессууд, <font name='M'>/api/spawn</font>-аар үүссэн мод, тогтмол буруу утгууд. "
            "<b>Автомат.</b> <font name='M'>sudo ./tests/run_module_tests.sh</font> (бодит module), <font name='M'>python3 tests/test_ui_api.py [--module]</font> (backend). "
            "<b>Давтах.</b> Үр дүн бүрийг Manual-д заасан тушаалаар давтан шалгаж болно. Дэлгэрэнгүй: <font name='M'>tests/test_cases.md</font>.")]
    s += [P("8. Үр дүн", H1),
          P("<b>8.1 Backend автомат тест (mock горим).</b> <font name='M'>python3 tests/test_ui_api.py</font> → <b>Ran 18 tests … OK</b> "
            "(T01–T04, E01–E09, H01–H03, S01–S02). Mock нь module-ийн гаралтыг <font name='M'>/proc/&lt;pid&gt;/stat</font>-аас дууриадаг тул энэ нь "
            "backend/parser/UI логикийн баталгаа бөгөөд <b>kernel module-ийн баталгаа биш</b>."),
          P("<b>8.2 Бодит kernel module (VM).</b> Доорх хүснэгтийн “Бодит” баганыг <font name='M'>sudo ./tests/run_module_tests.sh</font>-ийн гаралтаар бөглөнө:"),
          table([("ID", "Оролт", "Хүлээгдсэн", "Бодит")] + [tuple(r) for r in RESULTS], [14, 52, 70, 34]),
          Spacer(1, 3 * mm),
    s += [P("9. Хэлэлцүүлэг", H1)] + bullets([
        "Номын загвар ганц глобал pid хадгалдаг тул зэрэг ажиллах хэрэглэгчид pid-г дарж болно; backend write+read-ийг lock-оор хамгаалсан боловч module түвшинд per-open төлөв хэрэгжүүлбэл илүү зөв.",
        "Children-ийг for_each_process-оор олох нь O(N) (N = нийт процесс); мод бүрийн node бүрт дахин асуулт өгдөг тул том системд node-ийн дээд хязгаар шаардлагатай.",
        "Асуулт хооронд процесс гарч болох тул UI нь алдагдсан child-ийг бүдэг (gone) node-оор харуулна — мод нь агшин зуурын зураг, атомар биш.",
        "UI-д ZOMBIE-г өнгөөр ялгах мэдээлэл зөвхөн сонгосон task-ийн state_name-д байна (child: мөрд зөвхөн state тоо).",
        "PID namespace/container дотор task_pid_vnr нь дуудагчийн namespace-ээр харагддаг; гаднах parent 0 гэж харагдана.",
        "Kernel хувилбарын нийцэл (5.6 proc_ops, 5.14 __state) нь LINUX_VERSION_CODE-ээр шийдэгдсэн; зөвхөн багийн VM-ийн хувилбар дээр баталгаажсан."])
    s += [P("10. Дүгнэлт", H1),
          P("Номын Project 2-ын бүх шаардлага (pid бичих, command/pid/state унших, хүчингүй pid үед 0, kstrtol, kmalloc/kfree) болон Task hierarchy UI "
            "(parent, ancestors, children мод) хэрэгжсэн. Backend-ийн 18 автомат тест давсан. Module-ийн бодит ажиллагааг §8.2-ын хүснэгт болон screenshot-оор "
            "нотлоно. Цаашид: per-open төлөв, Thread (tid) түвшний харагдац, task state-ийн өнгө бүх node-д.")]
    s += [P("Ашигласан материал", H1)] + bullets([
        "A. Silberschatz, P. Galvin, G. Gagne, <i>Operating System Concepts</i>, 10th ed., Wiley, 2018 — Ch.3, Programming Projects P-15…P-17.",
        "Linux kernel documentation: <i>proc_ops</i>, RCU (Documentation/RCU), <i>include/linux/sched.h</i>.",
        "man 5 proc; man 1 ps.",
        "<b>AI ашигласан тэмдэглэл:</b> Анхны код, UI, тест, баримтын ноорогыг Claude (Anthropic) AI туслагчаар бэлтгэсэн; баг бүх кодыг уншиж, "
        "VM дээр build/run/test хийж баталгаажуулсан (README-д мөн тэмдэглэсэн). Бэлэн сан ашиглаагүй (Python stdlib, kernel headers)."])
    return s


# ================================================================= MANUAL ==
def manual():
    s = [Spacer(1, 30 * mm), P("F.CSM302 ҮЙЛДЛИЙН СИСТЕМ", C), P("БИЕ ДААЛТ 1 — MANUAL", C), Spacer(1, 8 * mm),
         P("Linux Kernel Module for Task Information", T), P(f"Код: {CODE} • UI: Task hierarchy", C), P(f"GitHub: {REPO}", C), PageBreak()]
    s += [P("8.1 Хэрэглэгчийн заавар", H1),
          P("<b>Програмын зорилго.</b> Kernel module <font name='M'>/proc/pid</font>-ээр process-ийн command, pid, state ба parent/ancestors/children-ийг өгдөг; "
            "web UI нь тэр өгөгдлөөр Task hierarchy мод зурна."),
          P("<b>Дэмжих орчин.</b> Linux (Ubuntu 22.04/24.04 VM), kernel 5.x/6.x, x86-64; Python 3.8+; орчин үеийн browser. "
            "(WSL1/macOS/Windows дээр kernel module ачаалагдахгүй — зөвхөн <font name='M'>--mock</font> горимоор UI үзэж болно.)"),
          P("<b>Суулгах / нээх алхам.</b>"),
          code("""sudo apt install build-essential linux-headers-$(uname -r) python3 git
git clone https://github.com/temkagg1117-lab/os-bd1.git && cd os-bd1
make -C src && sudo insmod src/task_info.ko
python3 ui/server.py            # дараа нь browser: http://127.0.0.1:8000"""),
          P("<b>Оролт ба тохиргоо.</b>"),
          table([("Талбар", "Утга", "Тайлбар"),
                 ("PID", "1 … 4194304", "Бүхэл тоо; өөр бол алдааны мэдээлэл"),
                 ("Доош гүнзгийрэх (depth)", "0 … 6", "Descendant-ын түвшний тоо"),
                 ("Node дээд тоо", "1 … 500", "Мод хэт томрохоос сэргийлнэ"),
                 ("Автомат шинэчлэл", "checkbox", "2 секунд тутамд дахин асууна"),
                 ("Гүн/Салаа (туршилтын мод)", "1..3 / 1..4", "Бодит sleep process мод үүсгэнэ")], [48, 32, 90]),
          P("<b>Ажиллуулах, зогсоох, reset.</b> Ажиллуулах: “Харуулах” (эсвэл Enter). Зогсоох: “Автомат шинэчлэл”-ийг унтраах; "
            "туршилтын process-уудыг “Цэвэрлэх” товчоор; сервер: Ctrl+C (мөн цэвэрлэнэ). Reset: “Reset” товч эсвэл хуудсыг дахин ачаалах. "
            "Module-г салгах: <font name='M'>sudo rmmod task_info</font>."),
          P("<b>Дүрслэлийн тэмдэг, өнгө, төлөв.</b>"),
          table([("Тэмдэг", "Утга"),
                 ("Ногоон node", "state 0 — TASK_RUNNING"), ("Цэнхэр", "state 1 — TASK_INTERRUPTIBLE (унтаж буй)"),
                 ("Улбар шар", "state 2 — TASK_UNINTERRUPTIBLE"), ("Саарал", "state 4/8 — stopped/traced"),
                 ("Улаан", "ZOMBIE/DEAD"), ("Хар зузаан хүрээ", "Сонгосон (асуусан) task"),
                 ("Саарал хүрээ", "Сонгосон task-ийн өвөг (ancestor)"), ("Бүдэг node", "Асуулт хооронд устсан process"),
                 ("“+” тэмдэг node дээр", "Хязгаараас болж нээгээгүй child байна"), ("Шар “MOCK” тэмдэг", "Module биш, дууриамал өгөгдөл")], [45, 125]),
          P("<b>Жишээ 1 — өөрийн shell.</b> Терминалд <font name='M'>echo $$</font> → гарсан PID-г UI-д оруулаад “Харуулах”. "
            "Дээрээс нь init → … → таны shell гэсэн гинж, доор нь таны эхлүүлсэн дэд process-ууд харагдана. "
            "Өөр терминалд <font name='M'>sleep 100 &amp;</font> эхлүүлээд auto-refresh-ийг асаагаарай — шинэ child 2 сек дотор нэмэгдэнэ."),
          P("<b>Жишээ 2 — туршилтын мод.</b> “Mод үүсгэх” (гүн 2, салаа 2) дарахад root PID автоматаар орж мод зурагдана. "
            "<font name='M'>ps -ef --forest</font>-той харьцуулаад, “Цэвэрлэх” дарж process-уудыг зогсооно."),
          P("<b>Түгээмэл алдаа ба шийдэл.</b>"),
          table([("Мэдээлэл", "Шалтгаан → шийдэл"),
                 ("“Kernel module ачаалагдаагүй” (503)", "<font name='M'>sudo insmod src/task_info.ko</font>; эсвэл <font name='M'>--mock</font>"),
                 ("“бичих эрх алга” (403)", "Module-ийг дахин ачаал (mode 0666); эсвэл server-ийг sudo-оор"),
                 ("“PID … олдсонгүй”", "Process дууссан/байхгүй — <font name='M'>ps</font>-ээр шалга"),
                 ("“бүхэл тоо биш / хүрээнээс гадуур”", "1..4194304 хоорондох бүхэл тоо оруул"),
                 ("“Backend-тэй холбогдож чадсангүй”", "<font name='M'>python3 ui/server.py</font> ажиллаж байгаа эсэх, порт 8000 чөлөөтэй эсэх"),
                 ("<font name='M'>insmod</font>: Invalid module format / Key rejected", "Headers нь ажиллаж буй kernel-тэй таарахгүй / Secure Boot — headers-ийг шинэчил, Secure Boot-ыг VM-д унтраа")], [58, 112])]
    s += [PageBreak(), P("8.2 Operational заавар", H1),
          P("<b>Repository clone.</b> <font name='M'>git clone https://github.com/temkagg1117-lab/os-bd1.git</font> (Release/Tag: <font name='M'>v1.0</font>)."),
          P("<b>OS, compiler/runtime, version.</b> Ubuntu 22.04/24.04 (kernel 5.15 / 6.8 — багийн орчин: 6.12.113+deb13-amd64), gcc ≥ 11, GNU make, Python ≥ 3.8, linux-headers-$(uname -r)."),
          P("<b>Dependency.</b> <font name='M'>sudo apt install build-essential linux-headers-$(uname -r) python3</font>. Python-д гадаад сан хэрэггүй."),
          P("<b>Build ба Run команд.</b>"),
          code("""make -C src                          # src/task_info.ko
sudo insmod src/task_info.ko         # dmesg | tail -1  -> 'task_info: loaded'
echo $$ > /proc/pid && cat /proc/pid
python3 ui/server.py [--port 8000] [--proc /proc/pid] [--mock]
sudo rmmod task_info ; make -C src clean"""),
          P("<b>Үндсэн тестийн өгөгдөл.</b>"),
          table([("Оролт", "Хүлээгдсэн үр дүн"),
                 ("<font name='M'>echo $$ > /proc/pid; cat /proc/pid</font>", "<font name='M'>command = [bash] pid = [$$] state = [1]</font> (+ state_name, ppid, ancestors, children)"),
                 ("<font name='M'>echo 1 > /proc/pid; cat /proc/pid</font>", "pid = [1]; ancestor байхгүй"),
                 ("Автомат: <font name='M'>sudo ./tests/run_module_tests.sh</font>", "Төгсгөлд “N passed, 0 failed”"),
                 ("<font name='M'>python3 tests/test_ui_api.py --module</font>", "Ran 18 tests … OK")], [75, 95]),
          P("<b>Нэмэлт boundary/error test.</b>"),
          code("""echo abc > /proc/pid          # bash: write error: Invalid argument
echo 0 > /proc/pid            # Invalid argument
echo -5 > /proc/pid           # Invalid argument
echo 99999999999 > /proc/pid  # Invalid argument
echo 4194303 > /proc/pid; cat /proc/pid | wc -c   # 0  (no such task)
dmesg | tail                  # task_info: ... сэрэмжлүүлэг"""),
          P("<b>Хүлээгдсэн үр дүн.</b> Буруу write бүр алдаа буцаана, өмнөх зөв pid хэвээр; олдохгүй pid үед read 0 byte; "
            "dmesg-д oops/BUG байхгүй; rmmod хийхэд /proc/pid устана. UI-д алдаа бүр ойлгомжтой мэдээлэлтэй."),
          P("<b>Known issues.</b>")] + bullets([
        "Ганц глобал pid (номын загвар) — зэрэг олон хэрэглэгч ажиллуулбал бие биенээ дарна.",
        "Мод агшин зуурын зураг: асуулт хооронд process үүсэх/дуусах боломжтой.",
        "Kernel хувилбарын нийцэл LINUX_VERSION_CODE-ээр; 5.6-аас доош хувилбарт туршаагүй.",
        "WSL1/Docker дотор kernel module ачаалагдахгүй (зөвхөн --mock)."])
    return s


if __name__ == "__main__":
    build(os.path.join(OUT, "BD1_Report.pdf"), "Тайлан", report())
    build(os.path.join(OUT, "BD1_Manual.pdf"), "Manual", manual())
    print("built", OUT)
