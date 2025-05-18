# Network Programming Final Project – **Multimedia Chat System**

---

## 1 · Group Members & Contributions

| Student ID    | Name                          | Key Responsibilities                          |
| ------------- | ----------------------------- | --------------------------------------------- |
| **23BI14116** | **Nguyễn Tiến Dũng** (Leader) | Server architecture, `/help` UX, thread model |
| 23BI14105     | Phạm Võ Toàn Đức              | Client CLI loop, Tk pop-ups, progress bars    |
| 23BI14059     | Đoàn Xuân Bách                | File-transfer framing, history replay         |
| 23BI14031     | Đào Quang Anh                 | Reply / recall / pin / forward logic          |
| 23BI14029     | Lê Nam Anh                    | Friend system, invite workflow                |
| 23BI14006     | Nguyễn Hoàng An               | Thread-safety, error handling, `/clean`       |

---

## 2 · Build & Run Instructions

1. **Prerequisites**

   * Python ≥ 3.8
   * `tkinter` (built-in on Win/macOS · `sudo apt install python3-tk` on Ubuntu)
   * Pillow  -- install once:

   ```bash
   pip install Pillow
   ```

2. **Start the server**

   ```bash
   cd server
   python3 server.py          # default 127.0.0.1:12345
   ```

3. **Start one or more clients**

   ```bash
   cd client
   python3 client.py
   ```

---

## 3 · Feature Matrix

| Domain            | Highlights & Commands                                                                              |
| ----------------- | -------------------------------------------------------------------------------------------------- |
| **Room Mgmt**     | `/room`, `/create`, `/join`, `/leave`, `/delete`, `/count`, `/online`, `/quit`                     |
| **Help/UX**       | `/help` with numbered pages **1-4** · TAB-completion · `/clean` (menu only)                        |
| **Messaging**     | Broadcast with `[MSG #id]`.   DM → `/msg @user text`                                               |
|                   | **Reply** `/reply <id> text` · **Recall** `/recall <id>`                                           |
|                   | **Pin** `/pin`, list `/pinned`, remove `/unpin`                                                    |
|                   | **Forward** any message/file notice to another room: `/forward <id> <room>` (tagged “FWD by User”) |
| **Files & Media** | Send: `/sendfile`, `/pic`, `/mp3`, `/mp4`, `/text`, **`/pdf`**, `/gif <url>`                       |
|                   | ASCII progress bars · 50 MB server limit · corruption check (byte-count)                           |
|                   | GUI choice on receive **Open & Save / Save / Skip**; later `/open`, `/save`                        |
| **Friend System** | `/addfriend`, `/acceptfriend`, `/myfriends`, `/unfriend`, `/block`                                 |
|                   | Online/offline alerts · `/invitefriend` with GUI pop-up                                            |
| **Tech**          | Thread-per-client server (lock-protected), threaded uploads on client                              |

---

## 4 · Protocol Overview

* **Plain text lines** – chat & commands, UTF-8, newline terminated.
* **JSON packets** – one per line (`\n` framing).

| Packet type  | Mandatory fields                            |
| ------------ | ------------------------------------------- |
| `file_start` | `filename`, `size`, `from`, *optional* `to` |
| `file_chunk` | `filename`, `data` (base64), `from`         |
| `file_end`   | `filename`, `from`                          |
| `msg` (DM)   | `to` (list), `text`, `from`                 |
| `invite`     | `room`, `from`                              |
| `friendreq`  | `from`                                      |

---

## 5 · Internal Mechanisms

* **Thread model**

  * **Server**: one thread / client + global `Lock` for all shared dicts.
  * **Client**: reader thread + CLI thread; each file upload in its own thread (non-blocking).

* **File transfer**

  * Base64 4 kB chunks inside JSON.
  * Receiver writes to disk, tracks `got` vs `size`; mismatch → “ERROR corrupted”.
  * Active transfers table cleaned when sender disconnects.

* **History**

  * Each room stores last 1000 items; auto-increment `msg_id`.
  * On `/join`, server replays history then pinned list.

* **Safety limits**

  * Upload size > 50 MB → server rejects.
  * `/block` prevents DM & file delivery from blocked user.

---

## 6 · Known Limitations & Future Work

| Area        | Current state         | Improvement idea                                 |
| ----------- | --------------------- | ------------------------------------------------ |
| Security    | Plain TCP             | TLS (`ssl`), end-to-end encryption               |
| Integrity   | Byte-count check only | SHA-256 checksum + automatic re-request          |
| Persistence | All state in RAM      | Persist rooms/history/friends to SQLite or Redis |
| Scalability | Thread-per-client     | Migrate to `asyncio` or epoll                    |
| UX          | Text-based            | Full GUI/Web (React + WebSocket)                 |
| Media       | File uploads only     | Live voice/video via WebRTC                      |

---

## 7 · Build Log & Tests

| Test                                         | Result                                     |
| -------------------------------------------- | ------------------------------------------ |
| 3 clients chat / swap rooms                  | OK                                         |
| Mixed jpg / mp3 / pdf upload (under 50 MB)   | Progress & save verified                   |
| Send > 50 MB file                            | Server replies “File exceeds 50 MB limit.” |
| Corrupt transfer (kill sender mid-file)      | Receiver prints *ERROR corrupted*          |
| Friend request + invite                      | Pop-ups & room join OK                     |
| `/forward` message & file notice room1→room2 | Arrives with “FWD by” tag                  |

*Environment*: Python 3.12 • Windows 11 & Ubuntu 22.04

---

> *README generated 18 May 2025 for code versions:*
> **client v15** | **server v18-fix**
