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

SENDER_EMAIL = "your_email@gmail.com"        # CHANGE
SENDER_PASSWORD = "your_app_password_here"   # CHANGE
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
"""
}
# ===============================================


# ---------------- Utility ----------------
def log(msg):
    log_box.insert(tk.END, msg)
    log_box.see(tk.END)


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
    global sending
    if sending:
        messagebox.showinfo("Info", "Already sending")
        return
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
root.geometry("900x760")
root.configure(bg="#1e1e1e")

fg = "#ffffff"
bg = "#1e1e1e"
entry_bg = "#2d2d2d"

def label(text):
    return tk.Label(root, text=text, fg=fg, bg=bg)

label("Cold Mail Sender – Anti-Spam Enabled").pack(pady=10)

tk.Button(root, text="Load CSV", command=load_csv).pack()
tk.Button(root, text="Add Attachment", command=select_attachment).pack(pady=4)

label("Template").pack()
template_var = tk.StringVar(value="Entry Level")
tk.OptionMenu(root, template_var, *TEMPLATES.keys()).pack()
tk.Button(root, text="Apply Template", command=apply_template).pack(pady=4)

label("Subject").pack()
subject_entry = tk.Entry(root, width=95, bg=entry_bg, fg=fg)
subject_entry.pack()

label("Email Body ({name} supported)").pack()
body_text = tk.Text(root, height=10, width=100, bg=entry_bg, fg=fg)
body_text.pack()

label("Send Limit (≤200 recommended)").pack()
limit_entry = tk.Entry(root, bg=entry_bg, fg=fg)
limit_entry.pack()

label("Delay Between Emails (seconds)").pack()
delay_entry = tk.Entry(root, bg=entry_bg, fg=fg)
delay_entry.insert(0, "5")
delay_entry.pack()

btn_frame = tk.Frame(root, bg=bg)
btn_frame.pack(pady=10)

tk.Button(btn_frame, text="SEND", bg="green", fg="white",
          width=12, command=start_sending).grid(row=0, column=0, padx=5)

tk.Button(btn_frame, text="PAUSE", bg="orange",
          width=12, command=pause_sending).grid(row=0, column=1, padx=5)

tk.Button(btn_frame, text="RESUME", bg="#00aaff", fg="white",
          width=12, command=resume_sending).grid(row=0, column=2, padx=5)

# ---------- Progress Bar ----------
progress_label = tk.Label(root, text="Progress: 0 / 0", fg=fg, bg=bg)
progress_label.pack()

progress = ttk.Progressbar(root, orient="horizontal", length=750, mode="determinate")
progress.pack(pady=5)

log_box = tk.Text(root, height=12, bg="#111", fg="#00ff9c")
log_box.pack(fill=tk.BOTH, padx=10, pady=10)

root.mainloop()
