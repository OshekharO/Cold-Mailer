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
            self.log(f"📎 Attachment: {os.path.basename(path)}\n")

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
        root.geometry("980x920")

        fg = "#f5f5f5"
        bg = "#0f1115"
        surface = "#1c1f26"
        entry_bg = "#12151c"
        muted = "#b7bec9"
        accent = "#4fa8f4"
        accent_secondary = "#25c46f"

        root.configure(bg=bg)
        root.option_add("*Font", ("Segoe UI", 10))
        root.minsize(760, 740)

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "TProgressbar",
            troughcolor="#0c0f14",
            background=accent,
            bordercolor=bg,
            lightcolor=accent,
            darkcolor=accent,
        )

        tk.Label(
            root,
            text="Cold Mail Sender – Anti-Spam Enabled",
            fg=fg,
            bg=bg,
            font=("Segoe UI Semibold", 18, "bold"),
        ).pack(pady=(18, 2))

        tk.Label(
            root,
            text="Automated outreach with pacing, templates, and attachment support",
            fg=muted,
            bg=bg,
            font=("Segoe UI", 10),
        ).pack(pady=(0, 12))

        card = tk.Frame(
            root,
            bg=surface,
            bd=0,
            highlightbackground="#2a2f36",
            highlightthickness=1,
            padx=18,
            pady=18,
        )
        card.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        def lbl(text, parent=None, **kw):
            return tk.Label(parent or card, text=text, fg=fg, bg=surface, anchor="w", **kw)

        def btn(parent, text, command, color=accent):
            return tk.Button(
                parent,
                text=text,
                command=command,
                bg=color,
                fg=fg,
                activebackground=color,
                activeforeground=fg,
                relief="flat",
                bd=0,
                padx=14,
                pady=8,
                font=("Segoe UI", 10, "bold"),
                cursor="hand2",
            )

        # ── Credentials ──────────────────────────────────────────────────────
        creds_frame = tk.Frame(card, bg=surface)
        creds_frame.pack(fill=tk.X, pady=(0, 10))

        lbl("Sender Email", parent=creds_frame).grid(row=0, column=0, sticky="w")
        lbl("App Password", parent=creds_frame).grid(row=0, column=1, sticky="w", padx=(18, 0))

        self.email_entry = tk.Entry(
            creds_frame,
            bg=entry_bg, fg=fg, relief="flat",
            insertbackground=fg, highlightthickness=1, highlightbackground="#2f3440",
        )
        self.email_entry.grid(row=1, column=0, sticky="we", pady=(4, 0))

        pass_frame = tk.Frame(creds_frame, bg=surface)
        pass_frame.grid(row=1, column=1, sticky="we", padx=(18, 0), pady=(4, 0))

        self.password_entry = tk.Entry(
            pass_frame,
            bg=entry_bg, fg=fg, relief="flat",
            insertbackground=fg, highlightthickness=1, highlightbackground="#2f3440",
            show="•",
        )
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.toggle_pass_btn = tk.Button(
            pass_frame,
            text="👁 Show",
            command=self.toggle_password_visibility,
            bg="#2a2f36",
            fg=fg,
            activebackground="#2a2f36",
            activeforeground=fg,
            relief="flat",
            bd=0,
            padx=8,
            pady=4,
            font=("Segoe UI", 9),
            cursor="hand2",
        )
        self.toggle_pass_btn.pack(side=tk.RIGHT, padx=(6, 0))

        creds_frame.columnconfigure(0, weight=1)
        creds_frame.columnconfigure(1, weight=1)

        # ── CSV / Attachment ─────────────────────────────────────────────────
        top_actions = tk.Frame(card, bg=surface)
        top_actions.pack(fill=tk.X)

        btn(top_actions, "Load CSV", self.load_csv).pack(side=tk.LEFT, padx=(0, 8))
        btn(top_actions, "Add Attachment", self.select_attachment, color="#3b82f6").pack(side=tk.LEFT)

        # ── Template ─────────────────────────────────────────────────────────
        lbl("Template").pack(pady=(14, 4), fill=tk.X)
        self.template_var = tk.StringVar(value="Entry Level")
        dropdown = tk.OptionMenu(card, self.template_var, *TEMPLATES.keys())
        dropdown.config(bg=entry_bg, fg=fg, activebackground=entry_bg, activeforeground=fg, relief="flat")
        dropdown["menu"].config(bg=entry_bg, fg=fg, activebackground=accent, activeforeground=fg)
        dropdown.pack(fill=tk.X)
        btn(card, "Apply Template", self.apply_template, color="#64748b").pack(pady=(6, 12), fill=tk.X)

        # ── Subject ──────────────────────────────────────────────────────────
        lbl("Subject").pack(pady=(4, 4), fill=tk.X)
        self.subject_entry = tk.Entry(
            card, width=95,
            bg=entry_bg, fg=fg, relief="flat",
            insertbackground=fg, highlightthickness=1, highlightbackground="#2f3440",
        )
        self.subject_entry.pack(fill=tk.X)

        # ── Body ─────────────────────────────────────────────────────────────
        lbl("Email Body ({name} supported)").pack(pady=(10, 4), fill=tk.X)
        body_frame = tk.Frame(card, bg=entry_bg, highlightthickness=1, highlightbackground="#2f3440")
        body_frame.pack(fill=tk.BOTH)
        body_scroll = tk.Scrollbar(body_frame, bg=surface, troughcolor=entry_bg, relief="flat", bd=0)
        body_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.body_text = tk.Text(
            body_frame, height=10, width=100,
            bg=entry_bg, fg=fg, relief="flat",
            insertbackground=fg, highlightthickness=0,
            yscrollcommand=body_scroll.set,
        )
        self.body_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        body_scroll.config(command=self.body_text.yview)

        # ── Options ──────────────────────────────────────────────────────────
        options_frame = tk.Frame(card, bg=surface)
        options_frame.pack(fill=tk.X, pady=(12, 4))

        lbl("Send Limit (≤200 recommended)", parent=options_frame).grid(row=0, column=0, sticky="w")
        lbl("Delay Between Emails (seconds, min 1)", parent=options_frame).grid(row=0, column=1, sticky="w", padx=(18, 0))

        self.limit_entry = tk.Entry(
            options_frame,
            bg=entry_bg, fg=fg, relief="flat",
            insertbackground=fg, highlightthickness=1, highlightbackground="#2f3440",
        )
        self.limit_entry.grid(row=1, column=0, sticky="we", pady=(4, 0))

        self.delay_entry = tk.Entry(
            options_frame,
            bg=entry_bg, fg=fg, relief="flat",
            insertbackground=fg, highlightthickness=1, highlightbackground="#2f3440",
        )
        self.delay_entry.insert(0, "5")
        self.delay_entry.grid(row=1, column=1, sticky="we", padx=(18, 0), pady=(4, 0))

        options_frame.columnconfigure(0, weight=1)
        options_frame.columnconfigure(1, weight=1)

        # ── Action buttons ────────────────────────────────────────────────────
        btn_frame = tk.Frame(card, bg=surface)
        btn_frame.pack(pady=12, fill=tk.X)

        btn(btn_frame, "SEND", self.start_sending, color=accent_secondary).grid(row=0, column=0, padx=5, sticky="we")
        btn(btn_frame, "PAUSE", self.pause_sending, color="#f59e0b").grid(row=0, column=1, padx=5, sticky="we")
        btn(btn_frame, "RESUME", self.resume_sending, color="#3b82f6").grid(row=0, column=2, padx=5, sticky="we")

        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)

        # ── Progress bar ──────────────────────────────────────────────────────
        prog_header = tk.Frame(card, bg=surface)
        prog_header.pack(fill=tk.X)
        self.progress_label = tk.Label(prog_header, text="Progress: 0 / 0", fg=muted, bg=surface, anchor="w")
        self.progress_label.pack(side=tk.LEFT)
        btn(prog_header, "Clear Log", self._clear_log, color="#374151").pack(side=tk.RIGHT)

        self.progress = ttk.Progressbar(card, orient="horizontal", length=750, mode="determinate")
        self.progress.pack(fill=tk.X, pady=6)

        # ── Log ───────────────────────────────────────────────────────────────
        log_frame = tk.Frame(card, bg="#0e1117", highlightthickness=1, highlightbackground="#2f3440")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=(2, 0))
        log_scroll = tk.Scrollbar(log_frame, bg=surface, troughcolor="#0e1117", relief="flat", bd=0)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_box = tk.Text(
            log_frame, height=12,
            bg="#0e1117", fg="#8afac9", relief="flat",
            insertbackground=fg, highlightthickness=0,
            state=tk.DISABLED,
            yscrollcommand=log_scroll.set,
        )
        self.log_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log_box.yview)

        tk.Label(
            root,
            text="Developed By Saksham Shekher",
            fg=muted,
            bg=bg,
            font=("Segoe UI", 9, "bold"),
        ).pack(pady=(6, 14))


def main() -> None:
    root = tk.Tk()
    ColdMailerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
