import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import csv
import smtplib
import time
import os
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# ================= SMTP CONFIG =================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

SENDER_EMAIL = "omeepd009@gmail.com"
SENDER_PASSWORD = "hjzd yhjx fvgb yyte"
# ===============================================

email_list = []
attachment_path = None

paused = False
sending = False
current_index = 0
total_emails = 0

# ================= TEMPLATES ===================
TEMPLATES = {
    "Entry Level": """Hi {name},

I hope this email finds you well.

I am reaching out to explore entry-level opportunities at your organization.

Best regards,
Your Name
""",
    "General Cold Mail": """Hello {name},

I wanted to connect regarding potential opportunities.

Kind regards,
Your Name
""",
    "Follow Up": """Hello {name},

I wanted to circle back on my previous email. Please let me know if you had a chance to review it.

Thanks,
Your Name
""",
    "Internship": """Hi {name},

I am seeking internship opportunities and would love to contribute and learn from your team.

Best,
Your Name
""",
    "Freelance": """Hello {name},

I provide freelance services and would be happy to help with your upcoming projects.

Regards,
Your Name
"""
}
# ===============================================


# ---------------- Utility ----------------
def log(msg):
    def _append():
        log_box.insert(tk.END, msg)
        log_box.see(tk.END)
    root.after(0, _append)


# ---------------- CSV ----------------
def load_csv():
    email_list.clear()
    path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if not path:
        return
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "name" in row and "email" in row:
                    email_list.append({
                        "name": row["name"].strip(),
                        "email": row["email"].strip()
                    })
        log(f"📄 Loaded {len(email_list)} contacts\n")
    except Exception as e:
        messagebox.showerror("CSV Error", str(e))


# ---------------- Attachment ----------------
def select_attachment():
    global attachment_path
    attachment_path = filedialog.askopenfilename()
    if attachment_path:
        log(f"📎 Attachment: {os.path.basename(attachment_path)}\n")


# ---------------- Template ----------------
def apply_template():
    body_text.delete("1.0", tk.END)
    body_text.insert(tk.END, TEMPLATES[template_var.get()])


# ---------------- Pause / Resume ----------------
def pause_sending():
    global paused
    paused = True
    log("⏸ Sending paused\n")


def resume_sending():
    global paused
    paused = False
    log("▶ Sending resumed\n")


# ---------------- Progress ----------------
def update_progress():
    progress["value"] = current_index
    progress_label.config(
        text=f"Progress: {current_index} / {total_emails}"
    )


# ---------------- Sending ----------------
def start_sending():
    global sending, paused, current_index, total_emails
    if sending:
        messagebox.showinfo("Info", "Already sending")
        return
    paused = False
    current_index = 0
    total_emails = 0
    threading.Thread(target=send_emails, daemon=True).start()


def send_emails():
    global paused, sending, current_index, total_emails

    if not email_list:
        messagebox.showwarning("No Data", "Load CSV first")
        return

    subject = subject_entry.get().strip()
    body = body_text.get("1.0", tk.END).strip()

    if not subject or not body:
        messagebox.showwarning("Missing", "Subject and body required")
        return

    try:
        limit = int(limit_entry.get()) if limit_entry.get() else len(email_list)
        delay = int(delay_entry.get()) if delay_entry.get() else 5
    except ValueError:
        messagebox.showerror("Error", "Limit & delay must be numbers")
        return

    recipients = email_list[:limit]
    total_emails = len(recipients)

    root.after(0, lambda: progress.config(maximum=total_emails, value=current_index))
    root.after(0, update_progress)

    sending = True

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
    except Exception as e:
        sending = False
        messagebox.showerror("SMTP Error", str(e))
        return

    while current_index < total_emails:
        if paused:
            time.sleep(1)
            continue

        person = recipients[current_index]

        try:
            msg = MIMEMultipart()
            msg["From"] = SENDER_EMAIL
            msg["To"] = person["email"]
            msg["Subject"] = subject

            msg.attach(MIMEText(body.format(name=person["name"]), "plain"))

            if attachment_path:
                with open(attachment_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{os.path.basename(attachment_path)}"'
                )
                msg.attach(part)

            server.sendmail(SENDER_EMAIL, person["email"], msg.as_string())
            log(f"✔ Sent to {person['email']}\n")

        except Exception as e:
            log(f"✖ Failed {person['email']} | {e}\n")

        current_index += 1
        root.after(0, update_progress)
        time.sleep(delay)

    server.quit()
    sending = False
    current_index = 0

    root.after(0, lambda: progress.config(value=0))
    root.after(0, lambda: progress_label.config(text="Progress: 0 / 0"))

    log("✅ All emails processed\n")
    messagebox.showinfo("Completed", "Email sending finished")


# ================= DARK MODE UI =================
root = tk.Tk()
root.title("Cold Mailer Pro")
root.geometry("980x820")

fg = "#f5f5f5"
bg = "#0f1115"
surface = "#1c1f26"
entry_bg = "#12151c"
muted = "#b7bec9"
accent = "#4fa8f4"
accent_secondary = "#25c46f"

root.configure(bg=bg)
root.option_add("*Font", ("Segoe UI", 10))

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

header = tk.Label(
    root,
    text="Cold Mail Sender – Anti-Spam Enabled",
    fg=fg,
    bg=bg,
    font=("Segoe UI Semibold", 18, "bold"),
)
header.pack(pady=(18, 2))

subheader = tk.Label(
    root,
    text="Automated outreach with pacing, templates, and attachment support",
    fg=muted,
    bg=bg,
    font=("Segoe UI", 10),
)
subheader.pack(pady=(0, 12))

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

def label(text, parent=None, **kwargs):
    return tk.Label(parent or card, text=text, fg=fg, bg=surface, anchor="w", **kwargs)

def action_button(parent, text, command, color=accent):
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

top_actions = tk.Frame(card, bg=surface)
top_actions.pack(fill=tk.X)

action_button(top_actions, "Load CSV", load_csv).pack(side=tk.LEFT, padx=(0, 8))
action_button(top_actions, "Add Attachment", select_attachment, color="#3b82f6").pack(side=tk.LEFT)

label("Template").pack(pady=(14, 4), fill=tk.X)
template_var = tk.StringVar(value="Entry Level")
template_dropdown = tk.OptionMenu(card, template_var, *TEMPLATES.keys())
template_dropdown.config(bg=entry_bg, fg=fg, activebackground=entry_bg, activeforeground=fg, relief="flat")
template_dropdown["menu"].config(bg=entry_bg, fg=fg, activebackground=accent, activeforeground=fg)
template_dropdown.pack(fill=tk.X)
action_button(card, "Apply Template", apply_template, color="#64748b").pack(pady=(6, 12), fill=tk.X)

label("Subject").pack(pady=(4, 4), fill=tk.X)
subject_entry = tk.Entry(card, width=95, bg=entry_bg, fg=fg, relief="flat", insertbackground=fg, highlightthickness=1, highlightbackground="#2f3440")
subject_entry.pack(fill=tk.X)

label("Email Body ({name} supported)").pack(pady=(10, 4), fill=tk.X)
body_text = tk.Text(card, height=10, width=100, bg=entry_bg, fg=fg, relief="flat", insertbackground=fg, highlightthickness=1, highlightbackground="#2f3440")
body_text.pack(fill=tk.BOTH)

options_frame = tk.Frame(card, bg=surface)
options_frame.pack(fill=tk.X, pady=(12, 4))

label("Send Limit (≤200 recommended)", parent=options_frame).grid(row=0, column=0, sticky="w")
label("Delay Between Emails (seconds)", parent=options_frame).grid(row=0, column=1, sticky="w", padx=(18, 0))

limit_entry = tk.Entry(options_frame, bg=entry_bg, fg=fg, relief="flat", insertbackground=fg, highlightthickness=1, highlightbackground="#2f3440")
limit_entry.grid(row=1, column=0, sticky="we", pady=(4, 0))

delay_entry = tk.Entry(options_frame, bg=entry_bg, fg=fg, relief="flat", insertbackground=fg, highlightthickness=1, highlightbackground="#2f3440")
delay_entry.insert(0, "5")
delay_entry.grid(row=1, column=1, sticky="we", padx=(18, 0), pady=(4, 0))

options_frame.columnconfigure(0, weight=1)
options_frame.columnconfigure(1, weight=1)

btn_frame = tk.Frame(card, bg=surface)
btn_frame.pack(pady=12, fill=tk.X)

action_button(btn_frame, "SEND", start_sending, color=accent_secondary).grid(row=0, column=0, padx=5, sticky="we")
action_button(btn_frame, "PAUSE", pause_sending, color="#f59e0b").grid(row=0, column=1, padx=5, sticky="we")
action_button(btn_frame, "RESUME", resume_sending, color="#3b82f6").grid(row=0, column=2, padx=5, sticky="we")

btn_frame.columnconfigure(0, weight=1)
btn_frame.columnconfigure(1, weight=1)
btn_frame.columnconfigure(2, weight=1)

# ---------- Progress Bar ----------
progress_label = tk.Label(card, text="Progress: 0 / 0", fg=muted, bg=surface, anchor="w")
progress_label.pack(fill=tk.X)

progress = ttk.Progressbar(card, orient="horizontal", length=750, mode="determinate")
progress.pack(fill=tk.X, pady=6)

log_box = tk.Text(card, height=12, bg="#0e1117", fg="#8afac9", relief="flat", insertbackground=fg, highlightthickness=1, highlightbackground="#2f3440")
log_box.pack(fill=tk.BOTH, padx=2, pady=(2, 0))

footer = tk.Label(
    root,
    text="Developed By Saksham Shekher",
    fg=muted,
    bg=bg,
    font=("Segoe UI", 9, "bold"),
)
footer.pack(pady=(6, 14))

if __name__ == "__main__":
    root.mainloop()
