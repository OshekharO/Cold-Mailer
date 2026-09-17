## 2024-09-12 - Pre-encoding Email Attachments in Bulk Email Loops

**Learning:** Re-reading attachment files from disk and re-executing `encoders.encode_base64` inside per-recipient loops adds significant redundant disk I/O and CPU overhead (~370x slower for 2MB files across 100 emails). Base64 encoding the attachment payload once outside the loop and setting `part["Content-Transfer-Encoding"] = "base64"` reduces MIME construction overhead to near-zero (~0.007s vs ~2.69s).

**Action:** Whenever sending emails or processing file-based payloads in batch loops, always cache/pre-encode immutable attachments or shared assets outside the loop.

## 2026-03-30 - Fast-path Email Parsing for Plain Strings in Bulk CSV Loading

**Learning:** Calling `email.utils.parseaddr` on plain email strings (which lack `<name@domain.com>` formatting) introduces heavy string parsing and regex overhead in `email._header_value_parser`. Fast-pathing plain email strings by bypassing `parseaddr` when angle brackets are absent speeds up bulk email validation by ~8x / ~88% reduction in runtime (e.g. 2.73s vs 0.34s for 110k contacts).

**Action:** When validating batch user-input email addresses, check for angle brackets before invoking `parseaddr` to fast-path standard plain email addresses.
