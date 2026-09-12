## 2024-09-12 - Pre-encoding Email Attachments in Bulk Email Loops

**Learning:** Re-reading attachment files from disk and re-executing `encoders.encode_base64` inside per-recipient loops adds significant redundant disk I/O and CPU overhead (~370x slower for 2MB files across 100 emails). Base64 encoding the attachment payload once outside the loop and setting `part["Content-Transfer-Encoding"] = "base64"` reduces MIME construction overhead to near-zero (~0.007s vs ~2.69s).

**Action:** Whenever sending emails or processing file-based payloads in batch loops, always cache/pre-encode immutable attachments or shared assets outside the loop.
