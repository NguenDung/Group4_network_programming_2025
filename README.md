# Network Programming Final Project – Multimedia Chat System

## 1. Group Members & Contributions

* **23BI14116 Nguyễn Tiến Dũng** (Leader)
* 23BI14105 Phạm Võ Toàn Đức
* 23BI14059 Đoàn Xuân Bách
* 23BI14031 Đào Quang Anh
* 23BI14029 Lê Nam Anh
* 23BI14006 Nguyễn Hoàng An

## 2. Build & Run Instructions

1. **Requirements**: Python 3.x, `tkinter` (pre-installed on Linux/Mac).
2. **Dependencies** (install via `requirements.txt` if updated):

   ```bash
   pip install -r requirements.txt  # currently only Pillow
   ```
3. **Start the server**:

   ```bash
   cd server
   python3 server.py
   ```
4. **Start the client(s)**:

   ```bash
   cd client
   python3 client.py
   ```

## 3. Features Implemented

### 3.1. Core Chat & Room Management

* **Rooms**: `/room`, `/create <name>`, `/join <name>`, `/leave`, `/delete <name>`, `/count`, `/online`, `/quit`
* **Help & UI**: `/help` with vertical lists + shortcuts `1–4`; `/clean` only works outside rooms
* **Messaging**:

  * Public chat broadcast (`[MSG #id] User: text`)
  * Private messaging: `/msg @user [text]`
  * Reply: `/reply <id> <text>` (`reply User →#id`)
  * Recall: `/recall <id>` (only own messages)

### 3.2. File & Multimedia Support

* **Transfer commands**:

  * `/sendfile` (any file)
  * `/pic`, `/mp3`, `/mp4`, `/text` (filter by extension)
  * `/gif <url>` fetch & send GIFs
* **Progress bars**: ASCII bar for send/receive chunks
* **GUI pop-up** on receive with **Open & Save / Save / Skip**
* **View & Save**: `/open <file>`, `/save <filename>` for skipped files
* **Late-join users** see history including `[FILE #id] User sent name (size B)` notices

### 3.3. Message Management

* **Pin/unpin**: `/pin <id>`, `/pinned`, `/unpin <pin_no>` with global notifications
* **History sync**: new users receive full chat + pinned list on `/join`

### 3.4. Friend System & Invites

* **Commands**: `/addfriend <user>`, `/acceptfriend <user>`, `/myfriends`, `/unfriend <user>`, `/block <user>`
* **Notifications**: GUI pop-up for friend requests + server text for accept; online/offline pings
* **Invite**: `/invitefriend <user>` with GUI pop-up to join current room

### 3.5. Advanced & Misc

* **ANSI-color**: highlights `@username` in 256-color palette
* **Tab completion**: for all commands in client
* **Thread safety**: `threading.Lock()` for shared state
* **Graceful disconnect**: ping/pong removed stale, broadcast offline messages

## 4. Protocol & Data Formats

1. **Text**: UTF-8 plain text (newline-delimited)
2. **JSON packets** (newline-delimited):

   * **file\_start**:

     ```json
     { "type": "file_start", "filename": "<name>", "size": <bytes>, "to": ["user"...], "from": "<sender>" }
     ```
   * **file\_chunk**:

     ```json
     { "type": "file_chunk", "filename": "<name>", "data": "<base64>", "from": "<sender>" }
     ```
   * **file\_end**:

     ```json
     { "type": "file_end", "filename": "<name>", "from": "<sender>" }
     ```
   * **msg** (private):

     ```json
     { "type": "msg", "to": ["user"...], "text": "<msg>", "from": "<sender>" }
     ```
   * **invite** / **friendreq**:

     ```json
     { "type": "invite", "from": "<sender>", "room": "<room>" }
     { "type": "friendreq", "from": "<sender>" }
     ```
3. **Framing**: each packet ends with `\n` for clear boundaries

## 5. Known Limitations & Future Improvements

* Transition to SHA‑256 + retry logic for file integrity
* Persistent storage of rooms/history/pins (DB)
* Full GUI or web client for richer UX
* Authentication & authorization, end-to-end encryption
* CI/CD, unit tests, Docker/K8s deployment
* Real-time voice/video integration via WebRTC

## 6. Contributors

* **Nguyễn Tiến Dũng (23BI14116)**: Leader, server architecture, `/help` logic
* **Phạm Võ Toàn Đức (23BI14105)**: Client-side I/O, pop-ups, progress bars
* **Đoàn Xuân Bách (23BI14059)**: File-transfer protocol and history sync
* **Đào Quang Anh (23BI14031)**: Message management (reply, recall, pin)
* **Lê Nam Anh (23BI14029)**: Friend-system, invite GUI
* **Nguyễn Hoàng An (23BI14006)**: Thread safety, error handling, clean command

---

*End of README*
