# 📧 Cold Mailer (Python + Tkinter)

A **desktop-based bulk email sender** built using **Python and Tkinter**.  
It allows users to load HR contact data from a CSV file and send personalized cold emails safely with **anti-spam features**, **pause/resume**, **progress tracking**, and **attachment support**.

## 🚀 Features

### ✅ Core Features
- Load HR **name & email** from CSV
- Custom **email subject & body**
- `{name}` placeholder personalization
- Pre-configured cold email templates
- Attachment support (PDF, DOCX, etc.)

### 🛡️ Anti-Spam & Safety
- Rate limiting (delay between emails)
- Send limit (e.g. 100 / 200 / all)
- Gmail-safe bulk sending
- Graceful error handling (no crash)

### ⏯️ Controls
- Start sending
- Pause sending
- Resume from same position
- No duplicate emails

### 📊 UI Enhancements
- Dark mode UI
- Real-time logs
- Progress bar (emails sent / total)
- Responsive & non-blocking UI (threaded)

---

## 🖥️ Tech Stack

- **Language:** Python 3.8+
- **GUI:** Tkinter
- **Email:** SMTP (Gmail supported)
- **CSV Handling:** csv module
- **Threading:** threading module

➡️ Uses **only Python standard library**  
➡️ No external dependencies

---

## 📂 Project Structure

```

cold_mailer_pro/
│
├── cold_mailer_pro.py
├── requirements.txt
└── README.md

````

---

## 📄 CSV File Format (Required)

Your CSV file **must** contain the following headers:

```csv
name,email
Rahul Sharma,rahul@gmail.com
Anita Verma,anita@company.com
````

---

## 🔐 Email Setup (Gmail)

To use Gmail SMTP:

1. Enable **2-Step Verification**
2. Generate **App Password**
3. Use App Password in code

```python
SENDER_EMAIL = "your_email@gmail.com"
SENDER_PASSWORD = "your_app_password"
```

❌ Do NOT use your normal Gmail password

---

## ▶️ How to Run

### 1️⃣ Install Python

Make sure Python **3.8 or above** is installed.

```bash
python --version
```

### 2️⃣ Run the Application

```bash
python cold_mailer_pro.py
```

---

## 🧪 How It Works

1. Load CSV file
2. Choose template or write custom email
3. Set subject, body, delay & send limit
4. (Optional) Add attachment
5. Click **SEND**
6. Pause / Resume anytime
7. Track progress via progress bar

---

## 📊 Anti-Spam Best Practices (Built-in)

| Feature              | Status |
| -------------------- | ------ |
| Rate limiting        | ✅      |
| Daily send limit     | ✅      |
| Personalization      | ✅      |
| Error isolation      | ✅      |
| UI freeze protection | ✅      |

Recommended:

* Delay ≥ 5 seconds
* ≤ 200 emails/day (Gmail safe)

---

## 🛠️ Customization Ideas

You can extend this project with:

* HTML email templates
* Resume auto-attach per row
* OAuth2 (password-less Gmail login)
* Email open tracking
* Convert to `.exe` using PyInstaller
* ETA (time remaining)
* Sent / Failed counters

---

## 📜 License

This project is created for **educational and personal use**.
Use responsibly and follow email outreach laws and policies.

---

## 👤 Author

Developed by **Saksham Shekher**
MCA | Python | Web | Cloud | DevOps Enthusiast
