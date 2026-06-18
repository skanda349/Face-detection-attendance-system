import re
import threading
import time
import customtkinter as ctk
from tkinter import ttk
from database import create_database, create_tables
from register import register_user
from login import login_user
from view_attendance import view_attendance

# ── Theme ──────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT      = "#4f8ef7"
ACCENT_DARK = "#1f538d"
BG_DARK     = "#0f1117"
BG_CARD     = "#1a1d27"
BG_SIDEBAR  = "#13151f"
SUCCESS     = "#2ecc71"
DANGER      = "#e74c3c"
WARNING     = "#f39c12"
TEXT_DIM    = "#8b8fa8"
TEXT_BRIGHT = "#e8eaf6"

create_database()
create_tables()

# ── Root window ────────────────────────────────────────────────────────────────
app = ctk.CTk()
app.title("Face Attendance System")
app.configure(fg_color=BG_DARK)
app.after(0, lambda: app.state("zoomed"))

try:
    app.iconbitmap("")
except Exception:
    pass

# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT SKELETON  (sidebar | main)
# ══════════════════════════════════════════════════════════════════════════════
root_frame = ctk.CTkFrame(app, fg_color=BG_DARK, corner_radius=0)
root_frame.pack(fill="both", expand=True)

sidebar = ctk.CTkFrame(root_frame, width=210, fg_color=BG_SIDEBAR, corner_radius=0)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

main_area = ctk.CTkFrame(root_frame, fg_color=BG_DARK, corner_radius=0)
main_area.pack(side="left", fill="both", expand=True)

# ── Sidebar brand ──────────────────────────────────────────────────────────────
brand_frame = ctk.CTkFrame(sidebar, fg_color=ACCENT_DARK, corner_radius=0)
brand_frame.pack(fill="x")

ctk.CTkLabel(brand_frame, text="🎓", font=ctk.CTkFont(size=32)).pack(pady=(18, 2))
ctk.CTkLabel(brand_frame, text="FaceAttend",
             font=ctk.CTkFont(size=17, weight="bold"),
             text_color=TEXT_BRIGHT).pack()
ctk.CTkLabel(brand_frame, text="Smart Attendance System",
             font=ctk.CTkFont(size=10), text_color="#a0b0d0").pack(pady=(2, 14))

# ── Live clock ─────────────────────────────────────────────────────────────────
clock_var = ctk.StringVar()
ctk.CTkLabel(sidebar, textvariable=clock_var,
             font=ctk.CTkFont(size=12, weight="bold"),
             text_color=ACCENT).pack(pady=(12, 4))

date_var = ctk.StringVar()
ctk.CTkLabel(sidebar, textvariable=date_var,
             font=ctk.CTkFont(size=10), text_color=TEXT_DIM).pack(pady=(0, 16))

def tick():
    while True:
        try:
            t = time.strftime("%I:%M:%S %p")
            d = time.strftime("%A, %d %B %Y")
            clock_var.set(t)
            date_var.set(d)
            time.sleep(1)
        except RuntimeError:
            # Main window closed, exit thread gracefully
            break

threading.Thread(target=tick, daemon=True).start()

ctk.CTkFrame(sidebar, height=1, fg_color="#2a2d3e").pack(fill="x", padx=16)

# ── Sidebar nav buttons ────────────────────────────────────────────────────────
NAV_ITEMS = [
    ("🏠", "Dashboard",       "dashboard"),
    ("📷", "Register User",   "register"),
    ("🎥", "Mark Attendance", "attendance"),
    ("📊", "View Records",    "records"),
]

active_page = ctk.StringVar(value="dashboard")
nav_buttons: dict[str, ctk.CTkButton] = {}

def nav_style(btn, active):
    if active:
        btn.configure(fg_color=ACCENT, text_color="white",
                      hover_color="#3a7de0")
    else:
        btn.configure(fg_color="transparent", text_color=TEXT_DIM,
                      hover_color="#1e2130")

def show_page(key):
    active_page.set(key)
    for k, b in nav_buttons.items():
        nav_style(b, k == key)
    for frame in pages.values():
        frame.pack_forget()
    pages[key].pack(fill="both", expand=True, padx=24, pady=20)

nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
nav_frame.pack(fill="x", pady=10)

for icon, label, key in NAV_ITEMS:
    btn = ctk.CTkButton(
        nav_frame, text=f"  {icon}  {label}",
        anchor="w", height=42, corner_radius=10,
        font=ctk.CTkFont(size=13),
        fg_color="transparent", text_color=TEXT_DIM,
        hover_color="#1e2130", border_width=0,
        command=lambda k=key: show_page(k)
    )
    btn.pack(fill="x", padx=12, pady=3)
    nav_buttons[key] = btn

# ── Sidebar footer ─────────────────────────────────────────────────────────────
ctk.CTkFrame(sidebar, height=1, fg_color="#2a2d3e").pack(fill="x", padx=16, side="bottom", pady=(0, 60))
ctk.CTkLabel(sidebar, text="v2.0  •  Face Recognition",
             font=ctk.CTkFont(size=9), text_color="#3a3d50").pack(side="bottom", pady=8)

# ══════════════════════════════════════════════════════════════════════════════
# TOAST NOTIFICATION
# ══════════════════════════════════════════════════════════════════════════════
toast_frame = ctk.CTkFrame(app, corner_radius=12, fg_color=SUCCESS,
                            border_width=0)
toast_label = ctk.CTkLabel(toast_frame, text="", font=ctk.CTkFont(size=12, weight="bold"),
                            text_color="white", padx=16, pady=10)
toast_label.pack()
_toast_job = None

def show_toast(msg: str, color: str = SUCCESS, duration: int = 3000):
    global _toast_job
    toast_frame.configure(fg_color=color)
    toast_label.configure(text=msg)
    toast_frame.place(relx=0.5, rely=0.96, anchor="s")
    app.lift(toast_frame)
    if _toast_job:
        app.after_cancel(_toast_job)
    _toast_job = app.after(duration, toast_frame.place_forget)

# ══════════════════════════════════════════════════════════════════════════════
# CARD HELPER
# ══════════════════════════════════════════════════════════════════════════════
def make_card(parent, title: str = "", pady_inner: int = 20) -> ctk.CTkFrame:
    outer = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=16,
                         border_width=1, border_color="#2a2d3e")
    if title:
        ctk.CTkLabel(outer, text=title,
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=TEXT_DIM).pack(anchor="w", padx=20, pady=(14, 0))
        ctk.CTkFrame(outer, height=1, fg_color="#2a2d3e").pack(fill="x", padx=16, pady=(8, 0))
    inner = ctk.CTkFrame(outer, fg_color="transparent")
    inner.pack(fill="both", expand=True, padx=20, pady=pady_inner)
    return inner

def fancy_entry(parent, label: str, placeholder: str, icon: str = "") -> ctk.CTkEntry:
    ctk.CTkLabel(parent, text=f"{icon}  {label}" if icon else label,
                 font=ctk.CTkFont(size=12, weight="bold"),
                 text_color=TEXT_DIM).pack(anchor="w", pady=(8, 2))
    e = ctk.CTkEntry(parent, placeholder_text=placeholder,
                     height=40, corner_radius=10,
                     border_color="#2a2d3e", fg_color="#0f1117",
                     font=ctk.CTkFont(size=13))
    e.pack(fill="x")
    return e

def fancy_button(parent, text: str, color: str = ACCENT,
                 hover: str = "#3a7de0", **kw) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent, text=text, height=44, corner_radius=12,
        font=ctk.CTkFont(size=13, weight="bold"),
        fg_color=color, hover_color=hover, **kw
    )

def run_bg(fn):
    threading.Thread(target=fn, daemon=True).start()

# ══════════════════════════════════════════════════════════════════════════════
# PAGES CONTAINER
# ══════════════════════════════════════════════════════════════════════════════
pages: dict[str, ctk.CTkFrame] = {}
for key in ("dashboard", "register", "attendance", "records"):
    pages[key] = ctk.CTkFrame(main_area, fg_color=BG_DARK, corner_radius=0)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
dp = pages["dashboard"]

ctk.CTkLabel(dp, text="Welcome back 👋",
             font=ctk.CTkFont(size=22, weight="bold"),
             text_color=TEXT_BRIGHT).pack(anchor="w")
ctk.CTkLabel(dp, text="Here's a quick overview of your attendance system.",
             font=ctk.CTkFont(size=12), text_color=TEXT_DIM).pack(anchor="w", pady=(2, 18))

stats_row = ctk.CTkFrame(dp, fg_color="transparent")
stats_row.pack(fill="x")
stats_row.columnconfigure((0, 1, 2), weight=1, uniform="s")

def stat_card(parent, col, icon, label, value_var, color):
    card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=16,
                        border_width=1, border_color="#2a2d3e")
    card.grid(row=0, column=col, padx=(0 if col == 0 else 10, 0), sticky="nsew")
    ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=28)).pack(pady=(16, 4))
    ctk.CTkLabel(card, textvariable=value_var,
                 font=ctk.CTkFont(size=26, weight="bold"),
                 text_color=color).pack()
    ctk.CTkLabel(card, text=label,
                 font=ctk.CTkFont(size=11), text_color=TEXT_DIM).pack(pady=(2, 16))

total_users_var    = ctk.StringVar(value="—")
today_present_var  = ctk.StringVar(value="—")
total_records_var  = ctk.StringVar(value="—")

stat_card(stats_row, 0, "👤", "Registered Users",    total_users_var,   ACCENT)
stat_card(stats_row, 1, "✅", "Present Today",        today_present_var, SUCCESS)
stat_card(stats_row, 2, "📋", "Total Records",        total_records_var, WARNING)

def refresh_stats():
    try:
        from database import connect
        conn = connect()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(DISTINCT userId) FROM user")
        users = str(cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM attendance WHERE date = CURDATE()")
        present = str(cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM attendance")
        total = str(cur.fetchone()[0])

        conn.close()

        # Push to main thread safely
        app.after(0, lambda: total_users_var.set(users))
        app.after(0, lambda: today_present_var.set(present))
        app.after(0, lambda: total_records_var.set(total))
    except Exception as e:
        app.after(0, lambda: total_users_var.set("0"))
        app.after(0, lambda: today_present_var.set("0"))
        app.after(0, lambda: total_records_var.set("0"))

def _refresh_stats_bg():
    refresh_stats()

run_bg(_refresh_stats_bg)

refresh_btn = fancy_button(dp, "🔄  Refresh Stats", color="#1e2130", hover="#2a2d3e")
refresh_btn.pack(anchor="e", pady=(14, 0))
refresh_btn.configure(command=lambda: run_bg(_refresh_stats_bg))

# Quick-action row
ctk.CTkLabel(dp, text="Quick Actions",
             font=ctk.CTkFont(size=14, weight="bold"),
             text_color=TEXT_BRIGHT).pack(anchor="w", pady=(22, 8))

qa_row = ctk.CTkFrame(dp, fg_color="transparent")
qa_row.pack(fill="x")

fancy_button(qa_row, "📷  Register User",   color=ACCENT_DARK, hover=ACCENT,
             command=lambda: show_page("register")).pack(side="left", padx=(0, 10), expand=True, fill="x")
fancy_button(qa_row, "🎥  Mark Attendance", color="#1a3a1a",   hover=SUCCESS,
             command=lambda: show_page("attendance")).pack(side="left", padx=(0, 10), expand=True, fill="x")
fancy_button(qa_row, "📊  View Records",    color="#3a2a10",   hover=WARNING,
             command=lambda: show_page("records")).pack(side="left", expand=True, fill="x")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: REGISTER
# ══════════════════════════════════════════════════════════════════════════════
rp = pages["register"]

# Page heading
ctk.CTkLabel(rp, text="Register New User",
             font=ctk.CTkFont(size=18, weight="bold"),
             text_color=TEXT_BRIGHT).pack(anchor="w")
ctk.CTkLabel(rp, text="Fill in the details and capture a face to register.",
             font=ctk.CTkFont(size=11), text_color=TEXT_DIM).pack(anchor="w", pady=(2, 10))

# Card centred horizontally, pinned near the top
reg_card_outer = ctk.CTkFrame(rp, fg_color=BG_CARD, corner_radius=14,
                               border_width=1, border_color="#2a2d3e")
reg_card_outer.pack(anchor="center", pady=(0, 0))

ctk.CTkLabel(reg_card_outer, text="User Information",
             font=ctk.CTkFont(size=11, weight="bold"),
             text_color=TEXT_DIM).pack(anchor="w", padx=20, pady=(12, 0))
ctk.CTkFrame(reg_card_outer, height=1, fg_color="#2a2d3e").pack(fill="x", padx=14, pady=(6, 0))

reg_card = ctk.CTkFrame(reg_card_outer, fg_color="transparent")
reg_card.pack(padx=20, pady=12)

# Compact label + entry
def small_entry(parent, label, placeholder, icon=""):
    ctk.CTkLabel(parent, text=f"{icon}  {label}" if icon else label,
                 font=ctk.CTkFont(size=11, weight="bold"),
                 text_color=TEXT_DIM).pack(anchor="w", pady=(4, 1))
    e = ctk.CTkEntry(parent, placeholder_text=placeholder,
                     height=32, corner_radius=8, width=340,
                     border_color="#2a2d3e", fg_color="#0f1117",
                     font=ctk.CTkFont(size=12))
    e.pack()
    return e

reg_id    = small_entry(reg_card, "User ID",       "e.g. STU001",      "🪪")
reg_email = small_entry(reg_card, "Email Address", "user@example.com", "📧")

reg_progress = ctk.CTkProgressBar(reg_card, mode="indeterminate",
                                   height=3, corner_radius=4, width=340,
                                   progress_color=ACCENT, fg_color="#1e2130")

reg_status = ctk.CTkLabel(reg_card, text="", font=ctk.CTkFont(size=11),
                           text_color=TEXT_DIM, wraplength=340)
reg_status.pack(pady=(6, 0))

# Register button
reg_btn = ctk.CTkButton(reg_card, text="📷  Register", height=36,
                         corner_radius=10, width=340,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         fg_color=ACCENT, hover_color="#3a7de0")
reg_btn.pack(pady=(10, 4))

def do_register():
    uid   = reg_id.get().strip()
    email = reg_email.get().strip()
    if not uid or not email:
        show_toast("⚠️  Please fill in all fields.", WARNING)
        return
    if not re.match(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$", email):
        show_toast("⚠️  Enter a valid email address.", WARNING)
        return

    reg_btn.configure(state="disabled", text="⏳  Opening camera…")
    reg_progress.pack(fill="x", pady=(8, 0))
    reg_progress.start()
    reg_status.configure(text="Camera is opening, please wait…", text_color=TEXT_DIM)
    app.update()

    ok, msg = register_user(uid, email)
    _reg_done(ok, msg)

def _reg_done(ok, msg):
    reg_progress.stop()
    reg_progress.pack_forget()
    reg_btn.configure(state="normal", text="📷  Register")
    reg_status.configure(text=msg, text_color=SUCCESS if ok else DANGER)
    show_toast(("✅  " if ok else "❌  ") + msg, SUCCESS if ok else DANGER)
    if ok:
        reg_id.delete(0, "end")
        reg_email.delete(0, "end")
        run_bg(_refresh_stats_bg)

reg_btn.configure(command=do_register)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MARK ATTENDANCE
# ══════════════════════════════════════════════════════════════════════════════
ap = pages["attendance"]

# Page heading
ctk.CTkLabel(ap, text="Mark Attendance",
             font=ctk.CTkFont(size=18, weight="bold"),
             text_color=TEXT_BRIGHT).pack(anchor="w")
ctk.CTkLabel(ap, text="Start the camera to automatically recognise and mark faces.",
             font=ctk.CTkFont(size=11), text_color=TEXT_DIM).pack(anchor="w", pady=(2, 10))

# Card centred horizontally, pinned near the top
att_card_outer = ctk.CTkFrame(ap, fg_color=BG_CARD, corner_radius=14,
                               border_width=1, border_color="#2a2d3e")
att_card_outer.pack(anchor="center", pady=(0, 0))

ctk.CTkLabel(att_card_outer, text="Face Recognition Scanner",
             font=ctk.CTkFont(size=11, weight="bold"),
             text_color=TEXT_DIM).pack(anchor="w", padx=20, pady=(12, 0))
ctk.CTkFrame(att_card_outer, height=1, fg_color="#2a2d3e").pack(fill="x", padx=14, pady=(6, 0))

att_card = ctk.CTkFrame(att_card_outer, fg_color="transparent")
att_card.pack(padx=20, pady=12)

# Camera status indicator
cam_indicator_row = ctk.CTkFrame(att_card, fg_color="transparent")
cam_indicator_row.pack(pady=(0, 8))

cam_dot = ctk.CTkLabel(cam_indicator_row, text="⬤",
                        font=ctk.CTkFont(size=12), text_color="#3a3d50")
cam_dot.pack(side="left")
cam_status_lbl = ctk.CTkLabel(cam_indicator_row, text="  Camera Idle",
                               font=ctk.CTkFont(size=11), text_color=TEXT_DIM)
cam_status_lbl.pack(side="left")

att_progress = ctk.CTkProgressBar(att_card, mode="indeterminate",
                                   height=3, corner_radius=4, width=340,
                                   progress_color=SUCCESS, fg_color="#1e2130")

att_result = ctk.CTkLabel(att_card, text="", font=ctk.CTkFont(size=11),
                           text_color=TEXT_DIM, wraplength=340)
att_result.pack(pady=(4, 0))

att_btn = ctk.CTkButton(att_card, text="📹  Start Camera", height=36,
                         corner_radius=10, width=340,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         fg_color="#1a3a1a", hover_color=SUCCESS)
att_btn.pack(pady=(10, 0))

hint = ctk.CTkLabel(att_card,
                     text="💡  Press ESC inside the camera window to stop scanning.",
                     font=ctk.CTkFont(size=10), text_color=TEXT_DIM)
hint.pack(pady=(6, 4))

def do_attendance():
    att_btn.configure(state="disabled", text="⏳  Camera Active…")
    att_progress.pack(fill="x", pady=(8, 0))
    att_progress.start()
    cam_dot.configure(text_color=SUCCESS)
    cam_status_lbl.configure(text="  Camera Active — Scanning faces…", text_color=SUCCESS)
    att_result.configure(text="")
    app.update()  # flush UI before blocking on camera

    ok, msg = login_user("", "")
    _att_done(ok, msg)

def _att_done(ok, msg):
    att_progress.stop()
    att_progress.pack_forget()
    att_btn.configure(state="normal", text="📹  Start Camera")
    cam_dot.configure(text_color="#3a3d50")
    cam_status_lbl.configure(text="  Camera Idle", text_color=TEXT_DIM)
    att_result.configure(text=msg, text_color=SUCCESS if ok else DANGER)
    show_toast(("✅  " if ok else "❌  ") + msg, SUCCESS if ok else DANGER)
    if ok:
        run_bg(_refresh_stats_bg)

att_btn.configure(command=do_attendance)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: VIEW RECORDS
# ══════════════════════════════════════════════════════════════════════════════
vp = pages["records"]
import datetime

ctk.CTkLabel(vp, text="Attendance Records",
             font=ctk.CTkFont(size=18, weight="bold"),
             text_color=TEXT_BRIGHT).pack(anchor="w")
ctk.CTkLabel(vp, text="Enter a date to list all attendance records for that day.",
             font=ctk.CTkFont(size=11), text_color=TEXT_DIM).pack(anchor="w", pady=(2, 10))

# ── Date filter row ───────────────────────────────────────────────────────────
filter_card = ctk.CTkFrame(vp, fg_color=BG_CARD, corner_radius=12,
                            border_width=1, border_color="#2a2d3e")
filter_card.pack(fill="x", pady=(0, 10))

filter_inner = ctk.CTkFrame(filter_card, fg_color="transparent")
filter_inner.pack(fill="x", padx=16, pady=10)

ctk.CTkLabel(filter_inner, text="📅  Date",
             font=ctk.CTkFont(size=11, weight="bold"),
             text_color=TEXT_DIM).pack(side="left", padx=(0, 8))

view_date = ctk.CTkEntry(filter_inner, placeholder_text="YYYY-MM-DD",
                          height=34, corner_radius=8, width=160,
                          border_color="#2a2d3e", fg_color="#0f1117",
                          font=ctk.CTkFont(size=12))
view_date.pack(side="left", padx=(0, 10))
view_date.insert(0, datetime.date.today().strftime("%Y-%m-%d"))

search_btn = ctk.CTkButton(filter_inner, text="🔍  Search", height=34,
                            corner_radius=8, width=110,
                            font=ctk.CTkFont(size=12, weight="bold"),
                            fg_color=ACCENT, hover_color="#3a7de0")
search_btn.pack(side="left", padx=(0, 6))

clear_btn = ctk.CTkButton(filter_inner, text="🗑  Clear", height=34,
                           corner_radius=8, width=80,
                           font=ctk.CTkFont(size=12, weight="bold"),
                           fg_color="#2a2d3e", hover_color="#3a3d50")
clear_btn.pack(side="left")

record_count_var = ctk.StringVar(value="")
ctk.CTkLabel(filter_inner, textvariable=record_count_var,
             font=ctk.CTkFont(size=11), text_color=ACCENT).pack(side="right")

# ── Results table ────────────────────────────────────────────────────────────
results_card_outer = ctk.CTkFrame(vp, fg_color=BG_CARD, corner_radius=12,
                                   border_width=1, border_color="#2a2d3e")
results_card_outer.pack(fill="both", expand=True)

table_wrap = ctk.CTkFrame(results_card_outer, fg_color="transparent")
table_wrap.pack(fill="both", expand=True, padx=12, pady=10)

style = ttk.Style()
style.theme_use("clam")
style.configure("FAS.Treeview",
                background=BG_CARD, foreground=TEXT_BRIGHT,
                fieldbackground=BG_CARD, rowheight=26,
                font=("Segoe UI", 11), borderwidth=0)
style.configure("FAS.Treeview.Heading",
                background=ACCENT_DARK, foreground="white",
                font=("Segoe UI", 11, "bold"), relief="flat")
style.map("FAS.Treeview",
          background=[("selected", ACCENT)],
          foreground=[("selected", "white")])

tree = ttk.Treeview(table_wrap,
                    columns=("ID", "Email", "Date", "Status"),
                    show="headings", style="FAS.Treeview")
for col, w, anchor in [("ID", 120, "center"), ("Email", 240, "w"),
                        ("Date", 120, "center"), ("Status", 100, "center")]:
    tree.heading(col, text=col)
    tree.column(col, width=w, anchor=anchor, minwidth=60)

tree.tag_configure("even",    background="#1e2130")
tree.tag_configure("odd",     background=BG_CARD)
tree.tag_configure("present", foreground=SUCCESS)
tree.tag_configure("absent",  foreground=DANGER)

vsb = ttk.Scrollbar(table_wrap, orient="vertical",   command=tree.yview)
hsb = ttk.Scrollbar(table_wrap, orient="horizontal",  command=tree.xview)
tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
tree.grid(row=0, column=0, sticky="nsew")
vsb.grid(row=0, column=1, sticky="ns")
hsb.grid(row=1, column=0, sticky="ew")
table_wrap.rowconfigure(0, weight=1)
table_wrap.columnconfigure(0, weight=1)

def do_view():
    d = view_date.get().strip()

    if not d:
        show_toast("⚠️  Please enter a date.", WARNING)
        return
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
        show_toast("⚠️  Date must be in YYYY-MM-DD format.", WARNING)
        return

    for row in tree.get_children():
        tree.delete(row)
    record_count_var.set("")

    records, err = view_attendance(d)

    if err:
        show_toast("❌  " + err, DANGER)
        return

    if not records:
        show_toast("ℹ️  No records found for " + d, WARNING, 4000)
        record_count_var.set("0 records")
        return

    for i, r in enumerate(records):
        tag_row  = "even" if i % 2 == 0 else "odd"
        tag_stat = "present" if str(r[3]).lower() == "present" else "absent"
        tree.insert("", "end", values=(r[0], r[1], str(r[2]), r[3]),
                    tags=(tag_row, tag_stat))

    record_count_var.set(f"{len(records)} record(s) found")
    show_toast(f"✅  {len(records)} record(s) loaded for {d}.", SUCCESS)

def do_clear():
    view_date.delete(0, "end")
    for row in tree.get_children():
        tree.delete(row)
    record_count_var.set("")

search_btn.configure(command=do_view)
clear_btn.configure(command=do_clear)

# ══════════════════════════════════════════════════════════════════════════════
# BOOT
# ══════════════════════════════════════════════════════════════════════════════
show_page("dashboard")
app.mainloop()
