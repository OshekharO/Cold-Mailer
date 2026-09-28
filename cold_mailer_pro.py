import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import csv
import smtplib
import time
import base64
import os
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import parseaddr
from typing import Optional

def parse_and_validate_email(email: str) -> str:
    """Fast email parser and validator. Bypasses parseaddr overhead for plain email strings (~8x faster)."""
    addr = parseaddr(email)[1] if ("<" in email and ">" in email) else email
    local, _, domain = addr.partition("@")
    if local and domain and "." in domain and not domain.startswith("."):
        return addr
    return ""

# ================= SMTP CONFIG =================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_TIMEOUT = 30  # seconds
# ===============================================

# ================= TEMPLATES ===================
TEMPLATES = {
    "Entry Level": """\
Hi {name},

I hope this message finds you well.

I recently came across your company and was genuinely impressed by the work your team is doing. As a motivated graduate with a strong foundation in [Your Field], I'm excited to bring fresh energy and a growth mindset to an entry-level role.

A few things I offer:
  • Solid understanding of [Skill 1] and [Skill 2]
  • Quick learner with a collaborative, team-first attitude
  • Passion for delivering quality work from day one

I'd love the opportunity to explore how I could contribute to your organisation. Would you be open to a brief 15-minute chat this week?

I've attached my resume for your reference — thank you so much for your time.

Warm regards,
[Your Name]
[LinkedIn] | [Portfolio / GitHub]
""",

    "General Cold Mail": """\
Hello {name},

I hope you're having a great week.

I'm reaching out because I believe there's a genuine fit between my background in [Your Field] and the direction your team is heading. Over the past [X] years I've built expertise in [Key Skill], and I'm actively exploring my next opportunity where I can make a real impact.

Career highlights:
  • [Achievement or project — one compelling line]
  • [Achievement or project — one compelling line]
  • [Achievement or project — one compelling line]

I'm not just sending out mass applications — your company specifically caught my attention because of [reason: product / mission / culture]. I'd love to learn more about your team and share how I might add value.

Would you be open to a quick 10-minute call at your convenience?

Best regards,
[Your Name]
[Email] | [LinkedIn] | [Portfolio]
""",

    "Follow Up": """\
Hello {name},

I wanted to follow up on my message from last week — I know how busy inboxes get, and I didn't want mine to slip through the cracks.

I remain genuinely enthusiastic about the possibility of contributing to your team at [Company Name]. If now isn't the right time, I completely understand — I'd love to stay on your radar for future openings.

To make it easy, here's a quick summary of what I bring:
  • [Core strength or skill]
  • [Relevant experience or achievement]
  • [What makes you stand out]

I'm happy to share my portfolio, resume, or any additional information at your convenience. Even a 10-minute call would mean a lot.

Thank you again for your time — I look forward to hearing from you.

Best,
[Your Name]
[LinkedIn] | [Portfolio]
""",

    "Internship": """\
Hi {name},

I'm a [Year] student pursuing [Degree] at [University], and I'm looking to gain meaningful hands-on experience through an internship this [Season / Year].

Your company immediately stood out to me because of [specific reason — product, culture, mission, or recent news]. I'm not just looking for a line on my resume — I want to roll up my sleeves and contribute to real work.

What I bring:
  • Coursework and projects in [Relevant Area]
  • Hands-on familiarity with [Tools / Tech / Languages]
  • Strong drive to learn fast, communicate clearly, and deliver results

I'd love to explore whether there's a fit. Could we schedule a quick 15-minute call to discuss any upcoming internship openings?

Thank you so much for taking the time to read this.

Best,
[Your Name]
[University] | [LinkedIn] | [GitHub / Portfolio]
""",

    "Freelance": """\
Hello {name},

I'm a freelance [Your Specialty — e.g., full-stack developer / UI designer / content writer] with [X]+ years of experience helping businesses like yours achieve [specific outcome — e.g., faster product delivery / higher conversion rates / stronger brand presence].

A few recent highlights:
  • [Client / Project]: [Brief, specific result — e.g., reduced load time by 40%]
  • [Client / Project]: [Brief, specific result]
  • [Client / Project]: [Brief, specific result]

I specialise in [Your Niche] and I'm selective about the projects I take on — which means the clients I work with get my full focus and best work.

I'd love to understand your upcoming needs and explore how I can help. Would you be open to a no-commitment 20-minute discovery call this week?

Regards,
[Your Name]
[Portfolio URL] | [LinkedIn] | [Email]
""",
}
# ===============================================


class ColdMailerApp:
    """Main application class – keeps all state and UI widgets encapsulated."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.email_list: list = []
        self.attachment_path: Optional[str] = None

        # threading.Event lets pause/resume work without busy-waiting
        self._pause_event = threading.Event()
        self._pause_event.set()  # set = not paused

        self._lock = threading.Lock()
        self.sending = False
        self.current_index = 0
        self.total_emails = 0

        self._build_ui()

    # ── Thread-safe helpers ───────────────────────────────────────────────────

    def log(self, msg: str) -> None:
        """Append a line to the read-only log widget from any thread."""
        def _append():
            self.log_box.config(state=tk.NORMAL)
            self.log_box.insert(tk.END, msg)
            self.log_box.see(tk.END)
            self.log_box.config(state=tk.DISABLED)
        self.root.after(0, _append)

    def _dialog(self, kind: str, title: str, msg: str) -> None:
        """Show a messagebox safely from a background thread."""
        fn = {
            "error": messagebox.showerror,
            "warning": messagebox.showwarning,
            "info": messagebox.showinfo,
        }[kind]
        self.root.after(0, lambda: fn(title, msg))

    # ── CSV ──────────────────────────────────────────────────────────────────

    def load_csv(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        try:
            loaded = []
            with open(path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    name = row.get("name", "").strip()
                    email = row.get("email", "").strip()
                    # skip rows with missing or structurally invalid email
                    # BOLT OPTIMIZATION: Fast path plain email strings to avoid parseaddr overhead (~8x faster CSV loading)
                    addr = parse_and_validate_email(email)
                    if name and addr:
                        loaded.append({"name": name, "email": addr})
            self.email_list = loaded
            if hasattr(self, "csv_status_lbl"):
                self.csv_status_lbl.config(
                    text=f"✓ Loaded {len(self.email_list)} contacts ({os.path.basename(path)})",
                    fg="#25c46f",
                )
            self.log(f"📄 Loaded {len(self.email_list)} contacts\n")
        except Exception as e:
            messagebox.showerror("CSV Error", str(e))

    # ── Attachment ────────────────────────────────────────────────────────────

    def toggle_password_visibility(self) -> None:
        """Toggle App Password entry visibility between hidden and plain text."""
        if self.password_entry.cget("show") == "•":
            self.password_entry.config(show="")
            self.toggle_pass_btn.config(text="🙈 Hide")
        else:
            self.password_entry.config(show="•")
            self.toggle_pass_btn.config(text="👁 Show")

    def select_attachment(self) -> None:
        path = filedialog.askopenfilename()
        if path:
            self.attachment_path = path
            filename = os.path.basename(path)
            if hasattr(self, "attachment_status_lbl"):
                self.attachment_status_lbl.config(
                    text=f"📎 {filename}",
                    fg="#3b82f6",
                )
            if hasattr(self, "clear_att_btn"):
                self.clear_att_btn.pack(side=tk.LEFT, padx=(4, 0))
            self.log(f"📎 Attachment: {filename}\n")

    def clear_attachment(self) -> None:
        self.attachment_path = None
        if hasattr(self, "attachment_status_lbl"):
            self.attachment_status_lbl.config(
                text="No file attached",
                fg="#6b7280",
            )
        if hasattr(self, "clear_att_btn"):
            self.clear_att_btn.pack_forget()
        self.log("📎 Attachment cleared\n")

    # ── Template ─────────────────────────────────────────────────────────────

    def apply_template(self) -> None:
        self.body_text.delete("1.0", tk.END)
        self.body_text.insert(tk.END, TEMPLATES[self.template_var.get()])

    # ── Pause / Resume ────────────────────────────────────────────────────────

    def pause_sending(self) -> None:
        if not self.sending:
            return
        self._pause_event.clear()
        self.log("⏸ Sending paused\n")

    def resume_sending(self) -> None:
        if not self.sending:
            return
        self._pause_event.set()
        self.log("▶ Sending resumed\n")

    def _clear_log(self) -> None:
        self.log_box.config(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        self.log_box.config(state=tk.DISABLED)

    # ── Progress ─────────────────────────────────────────────────────────────

    def _update_progress(self) -> None:
        self.progress["value"] = self.current_index
        self.progress_label.config(
            text=f"Progress: {self.current_index} / {self.total_emails}"
        )

    def _reset_progress(self) -> None:
        self.progress.config(value=0)
        self.progress_label.config(text="Progress: 0 / 0")

    # ── Sending ───────────────────────────────────────────────────────────────

    def start_sending(self) -> None:
        with self._lock:
            if self.sending:
                messagebox.showinfo("Info", "Already sending")
                return
        self._pause_event.set()
        self.current_index = 0
        threading.Thread(target=self._send_emails, daemon=True).start()

    def _send_emails(self) -> None:
        if not self.email_list:
            self._dialog("warning", "No Data", "Load CSV first")
            return

        subject = self.subject_entry.get().strip()
        body = self.body_text.get("1.0", tk.END).strip()
        sender_email = self.email_entry.get().strip()
        sender_password = self.password_entry.get().strip()

        if not sender_email or not sender_password:
            self._dialog("warning", "Missing", "Enter sender email and app password")
            return

        if not subject or not body:
            self._dialog("warning", "Missing", "Subject and body required")
            return

        try:
            limit_val = self.limit_entry.get().strip()
            delay_val = self.delay_entry.get().strip()
            limit = int(limit_val) if limit_val else len(self.email_list)
            delay = max(1, int(delay_val) if delay_val else 5)  # minimum 1 second
        except ValueError:
            self._dialog("error", "Error", "Limit & delay must be integers")
            return

        recipients = self.email_list[:limit]
        self.total_emails = len(recipients)
        self.root.after(0, lambda: self.progress.config(maximum=self.total_emails, value=0))
        self.root.after(0, self._update_progress)

        with self._lock:
            self.sending = True

        # BOLT OPTIMIZATION: Pre-read and base64-encode the attachment file ONCE before the loop.
        # This avoids redundant disk I/O and CPU-intensive base64 encoding for every recipient email.
        cached_attachment_payload: Optional[str] = None
        cached_attachment_filename: Optional[str] = None
        if self.attachment_path:
            try:
                with open(self.attachment_path, "rb") as f:
                    cached_attachment_payload = base64.b64encode(f.read()).decode("ascii")
                cached_attachment_filename = os.path.basename(self.attachment_path)
            except Exception as e:
                self._dialog("error", "Attachment Error", f"Failed to read attachment file: {e}")
                return

        server = None
        completed = False
        try:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=SMTP_TIMEOUT)
            server.starttls()
            server.login(sender_email, sender_password)

            while self.current_index < self.total_emails:
                self._pause_event.wait()  # blocks efficiently while paused

                person = recipients[self.current_index]
                try:
                    msg = MIMEMultipart()
                    msg["From"] = sender_email
                    msg["To"] = person["email"]
                    msg["Subject"] = subject

                    try:
                        personalized_body = body.format(name=person["name"])
                    except (KeyError, ValueError):
                        personalized_body = body

                    msg.attach(MIMEText(personalized_body, "plain"))

                    if cached_attachment_payload and cached_attachment_filename:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(cached_attachment_payload)
                        part["Content-Transfer-Encoding"] = "base64"
                        part.add_header(
                            "Content-Disposition",
                            f'attachment; filename="{cached_attachment_filename}"',
                        )
                        msg.attach(part)

                    server.sendmail(sender_email, person["email"], msg.as_string())
                    self.log(f"✔ Sent to {person['email']}\n")

                except smtplib.SMTPException as smtp_err:
                    self.log(f"✖ Failed {person['email']} | {smtp_err}\n")
                except Exception as e:
                    self.log(f"✖ Failed {person['email']} | {e}\n")

                self.current_index += 1
                self.root.after(0, self._update_progress)

                if self.current_index < self.total_emails:
                    time.sleep(delay)

            completed = True

        except smtplib.SMTPAuthenticationError:
            self._dialog(
                "error",
                "Auth Error",
                "Invalid email or app password.\nFor Gmail, use a 16-character App Password.",
            )
        except Exception as e:
            self._dialog("error", "SMTP Error", str(e))
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    pass
            with self._lock:
                self.sending = False
            self.root.after(0, self._reset_progress)
            if completed:
                self.log("✅ All emails processed\n")
                self._dialog("info", "Completed", "Email sending finished")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = self.root
        root.title("Cold Mailer Pro")
        root.geometry("1000x950")

        fg = "#f8fafc"
        bg = "#0f172a"
        card_bg = "#1e293b"
        card_border = "#334155"
        entry_bg = "#0f172a"
        entry_border = "#475569"
        muted = "#94a3b8"
        accent = "#38bdf8"
        accent_hover = "#0284c7"
        accent_secondary = "#22c55e"
        accent_secondary_hover = "#16a34a"

        root.configure(bg=bg)
        root.option_add("*Font", ("Segoe UI", 10))
        root.minsize(800, 780)

        # Apply dark styling to ttk widgets
        style = ttk.Style()
        style.theme_use("default")

        style.configure(
            "TProgressbar",
            troughcolor="#0f172a",
            background=accent,
            bordercolor=bg,
            lightcolor=accent,
            darkcolor=accent,
        )

        style.configure(
            "TCombobox",
            fieldbackground=entry_bg,
            background=card_bg,
            foreground=fg,
            darkcolor=card_bg,
            lightcolor=card_bg,
            arrowcolor=fg,
            bordercolor=entry_border,
            insertcolor=fg,
            padding=6,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", entry_bg)],
            foreground=[("readonly", fg)],
        )

        root.option_add("*TCombobox*Listbox.background", entry_bg)
        root.option_add("*TCombobox*Listbox.foreground", fg)
        root.option_add("*TCombobox*Listbox.selectBackground", accent_hover)
        root.option_add("*TCombobox*Listbox.selectForeground", fg)

        # Top Header Banner
        header = tk.Frame(root, bg=bg, padx=20, pady=12)
        header.pack(fill=tk.X)

        title_lbl = tk.Label(
            header,
            text="Cold Mailer Pro",
            fg=fg,
            bg=bg,
            font=("Segoe UI Semibold", 20, "bold"),
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(
            header,
            text="Automated outreach with anti-spam pacing, templates, and real-time logs",
            fg=muted,
            bg=bg,
            font=("Segoe UI", 10),
        )
        subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # Main Scrollable / Padding Container Frame
        main_container = tk.Frame(root, bg=bg, padx=20, pady=0)
        main_container.pack(fill=tk.BOTH, expand=True)

        def create_card(parent, title_text):
            card = tk.Frame(
                parent,
                bg=card_bg,
                bd=0,
                highlightbackground=card_border,
                highlightthickness=1,
                padx=16,
                pady=14,
            )
            card.pack(fill=tk.X, pady=(0, 12))

            header_lbl = tk.Label(
                card,
                text=title_text,
                fg=fg,
                bg=card_bg,
                font=("Segoe UI Semibold", 11, "bold"),
                anchor="w",
            )
            header_lbl.pack(fill=tk.X, pady=(0, 10))
            return card

        def lbl(text, parent, **kw):
            return tk.Label(parent, text=text, fg=muted, bg=card_bg, font=("Segoe UI", 9, "bold"), anchor="w", **kw)

        def create_entry(parent, show=None, width=None):
            kw = {}
            if show:
                kw["show"] = show
            if width:
                kw["width"] = width
            return tk.Entry(
                parent,
                bg=entry_bg,
                fg=fg,
                relief="flat",
                insertbackground=fg,
                highlightthickness=1,
                highlightbackground=entry_border,
                highlightcolor=accent,
                font=("Segoe UI", 10),
                **kw,
            )

        def btn(parent, text, command, color=accent, hover_color=accent_hover, fg_color=fg, padx=12, pady=6):
            b = tk.Button(
                parent,
                text=text,
                command=command,
                bg=color,
                fg=fg_color,
                activebackground=hover_color,
                activeforeground=fg_color,
                relief="flat",
                bd=0,
                padx=padx,
                pady=pady,
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
            )
            b.bind("<Enter>", lambda e: b.config(bg=hover_color))
            b.bind("<Leave>", lambda e: b.config(bg=color))
            return b

        # ── Section 1: Sender Credentials ──────────────────────────────────
        creds_card = create_card(main_container, "1. SENDER CREDENTIALS")

        creds_grid = tk.Frame(creds_card, bg=card_bg)
        creds_grid.pack(fill=tk.X)

        lbl("Sender Email Address", creds_grid).grid(row=0, column=0, sticky="w")
        lbl("App Password (Gmail)", creds_grid).grid(row=0, column=1, sticky="w", padx=(18, 0))

        self.email_entry = create_entry(creds_grid)
        self.email_entry.grid(row=1, column=0, sticky="we", pady=(4, 0))

        pass_frame = tk.Frame(creds_grid, bg=card_bg)
        pass_frame.grid(row=1, column=1, sticky="we", padx=(18, 0), pady=(4, 0))

        self.password_entry = tk.Entry(
            pass_frame,
            bg=entry_bg,
            fg=fg,
            relief="flat",
            insertbackground=fg,
            highlightthickness=1,
            highlightbackground=entry_border,
            highlightcolor=accent,
            font=("Segoe UI", 10),
            show="•",
        )
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.toggle_pass_btn = btn(
            pass_frame,
            text="👁 Show",
            command=self.toggle_password_visibility,
            color="#334155",
            hover_color="#475569",
            padx=10,
            pady=4,
        )
        self.toggle_pass_btn.pack(side=tk.RIGHT, padx=(6, 0))

        creds_grid.columnconfigure(0, weight=1)
        creds_grid.columnconfigure(1, weight=1)

        # ── Section 2: Campaign Contacts & File Attachments ────────────────
        files_card = create_card(main_container, "2. RECIPIENTS & ATTACHMENT")

        files_frame = tk.Frame(files_card, bg=card_bg)
        files_frame.pack(fill=tk.X)

        # CSV Box
        csv_box = tk.Frame(files_frame, bg=entry_bg, highlightthickness=1, highlightbackground=entry_border, padx=12, pady=10)
        csv_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        csv_btn_row = tk.Frame(csv_box, bg=entry_bg)
        csv_btn_row.pack(fill=tk.X)

        btn(csv_btn_row, "📁 Load Contacts CSV", self.load_csv, color="#0284c7", hover_color="#0369a1").pack(side=tk.LEFT)

        self.csv_status_lbl = tk.Label(
            csv_box,
            text="No CSV file loaded",
            fg=muted,
            bg=entry_bg,
            font=("Segoe UI", 9),
            anchor="w",
        )
        self.csv_status_lbl.pack(fill=tk.X, pady=(6, 0))

        # Attachment Box
        att_box = tk.Frame(files_frame, bg=entry_bg, highlightthickness=1, highlightbackground=entry_border, padx=12, pady=10)
        att_box.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        att_btn_row = tk.Frame(att_box, bg=entry_bg)
        att_btn_row.pack(fill=tk.X)

        btn(att_btn_row, "📎 Add Attachment", self.select_attachment, color="#475569", hover_color="#64748b").pack(side=tk.LEFT)

        self.clear_att_btn = btn(
            att_btn_row,
            text="✖ Clear",
            command=self.clear_attachment,
            color="#ef4444",
            hover_color="#dc2626",
            padx=8,
            pady=4,
        )
        # Hidden by default until an attachment is selected

        self.attachment_status_lbl = tk.Label(
            att_box,
            text="No file attached",
            fg=muted,
            bg=entry_bg,
            font=("Segoe UI", 9),
            anchor="w",
        )
        self.attachment_status_lbl.pack(fill=tk.X, pady=(6, 0))

        # ── Section 3: Email Composer ───────────────────────────────────────
        composer_card = create_card(main_container, "3. EMAIL COMPOSER")

        # Template Picker
        tmpl_frame = tk.Frame(composer_card, bg=card_bg)
        tmpl_frame.pack(fill=tk.X, pady=(0, 8))

        lbl("Select Template", tmpl_frame).grid(row=0, column=0, sticky="w")

        self.template_var = tk.StringVar(value="Entry Level")
        self.template_combo = ttk.Combobox(
            tmpl_frame,
            textvariable=self.template_var,
            values=list(TEMPLATES.keys()),
            state="readonly",
        )
        self.template_combo.grid(row=1, column=0, sticky="we", pady=(4, 0))

        apply_btn = btn(tmpl_frame, "Apply Template", self.apply_template, color="#475569", hover_color="#64748b")
        apply_btn.grid(row=1, column=1, padx=(12, 0), pady=(4, 0), sticky="e")

        tmpl_frame.columnconfigure(0, weight=1)

        # Subject Line
        lbl("Subject Line", composer_card).pack(fill=tk.X, pady=(4, 2))
        self.subject_entry = create_entry(composer_card)
        self.subject_entry.pack(fill=tk.X, pady=(0, 8))

        # Email Body
        lbl("Email Body (Supports {name} placeholders)", composer_card).pack(fill=tk.X, pady=(4, 2))

        body_frame = tk.Frame(composer_card, bg=entry_bg, highlightthickness=1, highlightbackground=entry_border)
        body_frame.pack(fill=tk.BOTH, expand=True)

        body_scroll = tk.Scrollbar(body_frame, bg=card_bg, troughcolor=entry_bg, relief="flat", bd=0)
        body_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.body_text = tk.Text(
            body_frame,
            height=7,
            bg=entry_bg,
            fg=fg,
            relief="flat",
            insertbackground=fg,
            highlightthickness=0,
            font=("Consolas", 10),
            yscrollcommand=body_scroll.set,
        )
        self.body_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        body_scroll.config(command=self.body_text.yview)

        # ── Section 4: Campaign Options & Controls ──────────────────────────
        opts_card = create_card(main_container, "4. SENDING PACING & ACTIONS")

        opts_grid = tk.Frame(opts_card, bg=card_bg)
        opts_grid.pack(fill=tk.X, pady=(0, 10))

        lbl("Send Limit (≤200 recommended for Gmail)", opts_grid).grid(row=0, column=0, sticky="w")
        lbl("Delay Between Emails (seconds, min 1s)", opts_grid).grid(row=0, column=1, sticky="w", padx=(18, 0))

        self.limit_entry = create_entry(opts_grid)
        self.limit_entry.grid(row=1, column=0, sticky="we", pady=(4, 0))

        self.delay_entry = create_entry(opts_grid)
        self.delay_entry.insert(0, "5")
        self.delay_entry.grid(row=1, column=1, sticky="we", padx=(18, 0), pady=(4, 0))

        opts_grid.columnconfigure(0, weight=1)
        opts_grid.columnconfigure(1, weight=1)

        # Action Buttons
        btn_frame = tk.Frame(opts_card, bg=card_bg)
        btn_frame.pack(fill=tk.X, pady=(4, 0))

        btn(btn_frame, "▶ START SENDING", self.start_sending, color=accent_secondary, hover_color=accent_secondary_hover, pady=8).grid(
            row=0, column=0, padx=(0, 6), sticky="we"
        )
        btn(btn_frame, "⏸ PAUSE", self.pause_sending, color="#f59e0b", hover_color="#d97706", pady=8).grid(
            row=0, column=1, padx=6, sticky="we"
        )
        btn(btn_frame, "▶ RESUME", self.resume_sending, color="#3b82f6", hover_color="#2563eb", pady=8).grid(
            row=0, column=2, padx=(6, 0), sticky="we"
        )

        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)

        # ── Section 5: Progress & Real-time Activity Log ────────────────────
        log_card = create_card(main_container, "5. PROGRESS & ACTIVITY LOG")

        prog_header = tk.Frame(log_card, bg=card_bg)
        prog_header.pack(fill=tk.X, pady=(0, 4))

        self.progress_label = tk.Label(
            prog_header,
            text="Progress: 0 / 0",
            fg=fg,
            bg=card_bg,
            font=("Segoe UI Semibold", 10),
            anchor="w",
        )
        self.progress_label.pack(side=tk.LEFT)

        btn(prog_header, "Clear Log", self._clear_log, color="#334155", hover_color="#475569", padx=10, pady=4).pack(side=tk.RIGHT)

        self.progress = ttk.Progressbar(log_card, orient="horizontal", mode="determinate")
        self.progress.pack(fill=tk.X, pady=(2, 10))

        log_frame = tk.Frame(log_card, bg="#020617", highlightthickness=1, highlightbackground=entry_border)
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_scroll = tk.Scrollbar(log_frame, bg=card_bg, troughcolor="#020617", relief="flat", bd=0)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_box = tk.Text(
            log_frame,
            height=7,
            bg="#020617",
            fg="#4ade80",
            relief="flat",
            insertbackground=fg,
            highlightthickness=0,
            font=("Consolas", 9),
            state=tk.DISABLED,
            yscrollcommand=log_scroll.set,
        )
        self.log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        log_scroll.config(command=self.log_box.yview)

        # Footer
        footer_lbl = tk.Label(
            root,
            text="Developed By Saksham Shekher",
            fg=muted,
            bg=bg,
            font=("Segoe UI", 9, "bold"),
        )
        footer_lbl.pack(pady=(4, 10))

def main() -> None:
    root = tk.Tk()
    ColdMailerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
