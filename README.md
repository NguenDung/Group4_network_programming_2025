## Network Programming Final Project – Multimedia Chat System

## 1. Group Members & Contributions

* **23BI14116	Nguyễn Tiến Dũng** (Leader)
* 23BI14105	Phạm Võ Toàn Đức
* 23BI14059	Đoàn Xuân Bách
* 23BI14031	Đào Quang Anh
* 23BI14029	Lê Nam Anh
* 23BI14006	Nguyễn Hoàng An

## 2. Build & Run Instructions

1. **Requirements**: Python 3.x, `tkinter` (usually pre‑installed on Linux/Mac).
2. **Dependencies** (if any):

   ```bash
   pip install -r requirements.txt  # (none currently required)
   ```
3. **Start the server**:

   ```bash
   python3 server.py
   ```
4. **Start each client**:

   ```bash
   python3 client.py
   ```

## 3. Features Implemented

* Multi‑client text chat over TCP sockets with threading
* Core commands:

  * Global context: `/help`, `/room`, `/create`, `/join`, `/quit`, `/online`, `/count`
  * In‑room context: `/leave`, `/users`, `/delete`, `/recall [id]`, `/reply [id] [msg]`
* **Private messaging**: `/msg @user1 @user2 ... [text]`
* **File transfer** with `/sendfile [@user...]`:

  * Supports: mp3, wav, pdf, txt, jpg/jpeg, png
  * GUI picker, progress display, MD5 checksum
* **ANSI‑color highlights** for `@username` tags (256‑color palette)
* **Heartbeat** ping/pong to detect stale connections
* **Thread safety** via `threading.Lock()` on shared data structures

## 4. Protocol Definition & Communication Patterns

1. **Text messages**: UTF‑8 plain text, newline‑delimited
2. **JSON packets** (newline‑delimited):

   * **file\_start**:

     ```json
     { "type": "file_start", "filename": "<file>", "size": <bytes>, "to": ["user..."], "from": "<sender>", "md5": "<checksum>" }
     ```
   * **file\_chunk**:

     ```json
     { "type": "file_chunk", "filename": "<file>", "data": "<base64>", "from": "<sender>" }
     ```
   * **msg** (private):

     ```json
     { "type": "msg", "to": ["user..."], "text": "<message>", "from": "<sender>" }
     ```
   * **ping/pong** (heartbeat):

     ```json
     { "type": "ping" } ↔ { "type": "pong" }
     ```
3. **Framing**: each JSON packet ends with `\n`, ensuring clear boundaries between messages and binary data.

## 5. Known Limitations & Future Improvements

* **Terminal vs GUI**: current client is terminal‑based with a file picker; consider a full curses or graphical UI for richer UX.
* **History search**: implement message filtering/search by keyword, username, message ID, or timestamp.
* **Resume file transfers**: support chunk indexing and resume interrupted transfers without restarting.
* **Enhanced checksum & retry**: upgrade to SHA‑256 and automatic retry of failed chunks.
* **Timeout & back‑off**: implement connection retry with exponential back‑off on failures.
* **Authentication & authorization**: add login/password, user roles (admin/moderator), and command permissions.
* **End‑to‑end encryption**: integrate encryption (e.g., NaCl or TLS) so only clients can decrypt messages/files.
* **Containerization & orchestration**: Dockerize the server and explore Kubernetes deployment for scalability.
* **CI/CD & unit testing**: add automated tests (command parsing, protocol handling) and continuous integration pipelines.
* **Persistent storage**: store rooms, message history, and logs in a database (SQLite, PostgreSQL) to survive restarts.
* **Voice/video chat**: extend to real‑time audio/video using WebRTC or similar libraries.
* **Bot/plugin architecture**: enable custom bots or plugins for notifications, moderation, or integrations.
* **Web/Mobile clients**: develop browser‑based or mobile app clients using WebSockets for broader accessibility.
