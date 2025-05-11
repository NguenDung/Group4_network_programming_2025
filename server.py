#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Server v17d – multi-room chat, file-transfer (progress), pin/unpin, recall,
friend-request (accept), block, invitefriend, detailed vertical /help,
/clean chỉ ở menu, late-join thấy file-notice.
"""

import socket, threading, datetime, json, sys
from collections import deque

HOST, PORT, ENC = '127.0.0.1', 12345, 'utf-8'

# ──────────────── global state ────────────────
clients, user_rooms = {}, {}
rooms = {"room1": [], "room2": [], "room3": []}
msg_id   = {r: 1 for r in rooms}
history  = {r: deque(maxlen=1000) for r in rooms}   # (id, sender, line)
pins     = {r: [] for r in rooms}                   # (pin_no, id, line)
pin_no   = {r: 1 for r in rooms}
active   = {}                                       # (sock,fname)->{'rec':[…]}

friends, blocks, pending = {}, {}, {}               # friend system
lock = threading.Lock()

# ──────────────── helpers ──────────────────────
def ts(fmt="[%H:%M:%S]"): return datetime.datetime.now().strftime(fmt)
def safe(sock, data):
    try: sock.sendall(data if isinstance(data,bytes) else data.encode(ENC))
    except: pass
def bc(room, line, exc=None):
    with lock: rec = list(rooms.get(room, []))
    for c in rec:
        if c is not exc: safe(c, line + "\n")
def bc_pkt(pkt, rec, exc=None):
    data = (json.dumps(pkt) + "\n").encode(ENC)
    for c in rec:
        if c is not exc: safe(c, data)
def snippet(line, n=60):
    txt = line.split('»: ',1)[-1] if '»: ' in line else line.split(': ',1)[-1]
    return (txt[:n] + "…") if len(txt) > n else txt
def notify_friend(name, online=True):
    msg = f"[Friend] {name} is now " + ("online" if online else "offline")
    with lock:
        for c,u in clients.items():
            if name in friends.get(u,set()):
                safe(c, msg + "\n")

# ──────────────── file-transfer ────────────────
def ft_start(sock, p):
    sender = clients[sock]
    fname, size, to = p["filename"], p["size"], p.get("to")
    with lock:
        room = user_rooms[sock]
        if not room:
            safe(sock, "Join a room first.\n"); return
        rec = [c for c,u in clients.items()
               if (not to or u in to) and c in rooms[room]
               and sender not in blocks.get(u,set())]
        active[(sock,fname)] = {'rec': rec}

        # log để người vào sau nhìn thấy đã gửi file gì
        fid = msg_id[room]; msg_id[room] += 1
        line = f"[FILE #{fid}] {sender} sent {fname} ({size} B)"
        history[room].append((fid, sender, line))

    bc(room, line)            # thông báo văn bản cho cả phòng
    bc_pkt(p, rec, exc=sock)  # truyền dữ liệu cho người nhận

def ft_chunk(sock, p):
    rec = active.get((sock,p["filename"]),{}).get("rec",[])
    bc_pkt(p, rec, exc=sock)

def ft_end(sock, p):
    rec = active.pop((sock,p["filename"]),{}).get("rec",[])
    bc_pkt(p, rec, exc=sock)

# ──────────────── help text ────────────────────
CAT = {"1":"menu","2":"chat","3":"file","4":"friend",
       "menu":"menu","chat":"chat","file":"file","friend":"friend"}

def help_root():
    return (
        "Help categories (press 1-4 or /help <number>):\n"
        "  1) menu   – commands outside any room\n"
        "  2) chat   – commands inside a room\n"
        "  3) file   – send / receive files & PM\n"
        "  4) friend – add / block / invite friends\n"
    )

HELP = {
"menu":(
"/room               – list rooms\n"
"/create <name>      – create room\n"
"/join   <name>      – join room\n"
"/rename <new>       – change username\n"
"/delete <room>      – delete room\n"
"/count              – user count per room\n"
"/online             – total online users\n"
"/clean              – clear screen (menu only)\n"
"/quit               – logout"),
"chat":(
"/leave              – leave room\n"
"/rename <new>       – change username\n"
"/users              – list users in room\n"
"/recall <id>        – recall *your* msg\n"
"/reply <id> <txt>   – reply message\n"
"/pin   <id>         – pin msg\n"
"/pinned             – list pins\n"
"/unpin <pin_no>     – remove pin\n"
"/msg @User <txt>    – private message\n"
"/invitefriend <usr> – invite friend to room"),
"file":(
"/sendfile           – any file\n"
"/pic                – image (.jpg/.png)\n"
"/mp3                – audio (.mp3/.wav)\n"
"/mp4                – video (.mp4)\n"
"/text               – text file (.txt)\n"
"/gif <url>          – fetch & send GIF\n"
"/open <file>        – open file\n"
"/save <file>        – save skipped file"),
"friend":(
"/addfriend <usr>    – send request\n"
"/acceptfriend <usr> – accept request\n"
"/myfriends          – list friends\n"
"/unfriend  <usr>    – remove friend\n"
"/block     <usr>    – block/unblock user")
}

# ──────────────── command handler ──────────────
def cmd(cli, text):
    args = text.split(); cmd = args[0]
    usr  = clients[cli]; room = user_rooms[cli]
    tell = lambda m: safe(cli, f"{ts()} {m}\n")

    # ----- help -----
    if cmd == "/help":
        tell(help_root() if len(args)==1 else HELP.get(CAT.get(args[1].lower()),"Unknown")); return
    if cmd in CAT: tell(HELP[CAT[cmd]]); return

    # client-side handled
    if cmd in ("/sendfile","/pic","/mp3","/mp4","/text","/gif","/msg"):
        return

    # ===== menu =====
    if cmd == "/room":  tell("Rooms: " + ", ".join(rooms)); return
    if cmd == "/create":
        if len(args)<2: tell("Usage: /create <room>"); return
        r=args[1]
        with lock:
            if r in rooms: tell("Room exists"); return
            rooms[r]=[]; msg_id[r]=1; history[r]=deque(maxlen=1000); pins[r]=[]; pin_no[r]=1
        tell(f"Room '{r}' created."); return
    if cmd == "/join":
        if len(args)<2: tell("Usage: /join <room>"); return
        r=args[1]
        with lock:
            if r not in rooms: tell("Room not found"); return
            prev=user_rooms[cli]
            if prev and cli in rooms[prev]: rooms[prev].remove(cli)
            rooms[r].append(cli); user_rooms[cli]=r
        safe(cli, f"{ts()} Joined {r}\n")
        with lock:
            for _i,_s,ln in history[r]: safe(cli, ln+"\n")
            if pins[r]:
                safe(cli,"-- PINNED --\n")
                for no,_i,pl in pins[r]: safe(cli,f"{no}) {pl}\n")
                safe(cli,"-------------\n")
        bc(r, f"{ts()} **{usr} joined the room.**", exc=cli); return
    if cmd == "/rename":
        if len(args)<2: tell("Usage: /rename <new>"); return
        new=args[1]
        with lock:
            if new in clients.values(): tell("Username taken"); return
            friends[new]=friends.pop(usr,set()); blocks[new]=blocks.pop(usr,set()); pending[new]=pending.pop(usr,set())
            clients[cli]=new; usr=new
        tell(f"Renamed to {new}"); return
    if cmd == "/delete":
        if len(args)<2: tell("Usage: /delete <room>"); return
        r=args[1]
        with lock:
            if r not in rooms: tell("Room not found"); return
            for c in rooms[r]:
                user_rooms[c]=None; safe(c,f"{ts()} Room '{r}' deleted\n")
            del rooms[r]; msg_id.pop(r); history.pop(r); pins.pop(r); pin_no.pop(r)
        tell(f"Room '{r}' deleted."); return
    if cmd == "/count":
        with lock: tell(", ".join(f"{r}:{len(lst)}" for r,lst in rooms.items())); return
    if cmd == "/online":
        with lock: tell(f"Online users: {len(clients)}"); return
    if cmd == "/clean":
        safe(cli, "\033c"); return
    if cmd == "/quit":
        safe(cli, "Bye!\n"); disconnect(cli); return

    # ===== friend system =====
    if cmd in ("/addfriend","/acceptfriend","/myfriends","/unfriend","/block","/invitefriend"):
        with lock:
            friends.setdefault(usr,set()); blocks.setdefault(usr,set()); pending.setdefault(usr,set())

    if cmd == "/addfriend":
        if len(args)<2: tell("Usage: /addfriend <user>"); return
        target=args[1]
        with lock: tgt_cli=next((c for c,u in clients.items() if u==target),None)
        if not tgt_cli: tell("User not online."); return
        if target in friends[usr] or usr in pending[target]:
            tell("Already friends or pending."); return
        pending[target].add(usr)
        safe(tgt_cli, json.dumps({"type":"friendreq","from":usr})+"\n")
        tell("Request sent."); return

    if cmd == "/acceptfriend":
        if len(args)<2: tell("Usage: /acceptfriend <user>"); return
        req=args[1]
        if req not in pending[usr]: tell("No pending request."); return
        pending[usr].remove(req)
        friends[usr].add(req); friends.setdefault(req,set()).add(usr)
        with lock: req_cli=next((c for c,u in clients.items() if u==req),None)
        if req_cli: safe(req_cli,f"[Friend] {usr} accepted your request.\n")
        tell("Friend added."); return

    if cmd == "/myfriends": tell("Friends: "+", ".join(sorted(friends[usr]) or ["(none)"])); return
    if cmd == "/unfriend":
        if len(args)<2: tell("Usage: /unfriend <user>"); return
        tgt=args[1]; friends[usr].discard(tgt); friends.get(tgt,set()).discard(usr)
        tell("Removed."); return
    if cmd == "/block":
        if len(args)<2: tell("Usage: /block <user>"); return
        tgt=args[1]
        if tgt in blocks[usr]:
            blocks[usr].remove(tgt); tell(f"Unblocked {tgt}")
        else:
            blocks[usr].add(tgt); tell(f"Blocked {tgt}")
        return
    if cmd == "/invitefriend":
        if not room: tell("Join a room first."); return
        if len(args)<2: tell("Usage: /invitefriend <user>"); return
        tgt=args[1]
        with lock: tgt_cli=next((c for c,u in clients.items() if u==tgt),None)
        if tgt_cli:
            safe(tgt_cli,json.dumps({"type":"invite","from":usr,"room":room})+"\n")
            tell("Invite sent."); return
        tell("User not online."); return

    # ===== chat & file (need room) =====
    if cmd in ("/leave","/users","/recall","/reply","/pin","/pinned","/unpin"):
        if not room:
            tell("Join a room first."); return

    if cmd == "/leave":
        with lock: rooms[room].remove(cli); user_rooms[cli]=None
        safe(cli,f"{ts()} Left room\n"); bc(room,f"{ts()} **{usr} left.**",exc=cli); return
    if cmd == "/users":
        with lock: tell("Users: "+", ".join(clients[c] for c in rooms[room])); return
    if cmd == "/recall":
        if len(args)<2 or not args[1].isdigit(): tell("Usage: /recall <id>"); return
        rid=int(args[1])
        with lock:
            idx,rec=next(((i,h) for i,h in enumerate(history[room]) if h[0]==rid),(None,None))
            if not rec: tell("ID not found"); return
            if rec[1]!=usr: tell("Only recall own msg"); return
            history[room][idx]=(rid,usr,f"[MSG #{rid}] (recalled)")
        bc(room,f"[MSG #{rid}] (recalled)"); return
    if cmd == "/reply":
        if len(args)<3 or not args[1].isdigit(): tell("Usage: /reply <id> <txt>"); return
        oid=int(args[1]); txt=" ".join(args[2:])
        with lock: orig=next((h for h in history[room] if h[0]==oid),None)
        if not orig: tell("ID not found"); return
        mid=msg_id[room]; msg_id[room]+=1
        line=(f"[MSG #{mid}] {usr} reply {orig[1]} →#{oid} "
              f"«{orig[1]}: {snippet(orig[2])}»: {txt}")
        with lock: history[room].append((mid,usr,line))
        bc(room,line); return
    if cmd == "/pin":
        if len(args)<2 or not args[1].isdigit(): tell("Usage: /pin <id>"); return
        mid=int(args[1])
        with lock: rec=next((h for h in history[room] if h[0]==mid),None)
        if not rec: tell("ID not found"); return
        no=pin_no[room]; pin_no[room]+=1; pins[room].append((no,mid,rec[2]))
        bc(room,f"{ts()} **{usr} pinned message #{mid} (pin {no})**"); return
    if cmd == "/pinned":
        with lock: plist=pins[room][:]
        if not plist: bc(room,"No pinned items."); return
        bc(room,"-- PINNED LIST --")
        for no,_i,pl in plist: bc(room,f"{no}) {pl}")
        bc(room,"-----------------"); return
    if cmd == "/unpin":
        if len(args)<2 or not args[1].isdigit(): tell("Usage: /unpin <pin_no>"); return
        no=int(args[1])
        with lock:
            if not any(p[0]==no for p in pins[room]): tell("Pin not found"); return
            pins[room]=[p for p in pins[room] if p[0]!=no]
        bc(room,f"{ts()} **{usr} unpinned item {no}**"); return

    tell("Unknown command.")

# ──────────────── routing ────────────────────────
def handle_text(cli,msg):
    if msg.startswith("/"):
        cmd(cli,msg); return
    room=user_rooms[cli]
    if not room:
        safe(cli,"Join a room first\n"); return
    mid=msg_id[room]; msg_id[room]+=1
    line=f"[MSG #{mid}] {clients[cli]}: {msg}"
    with lock: history[room].append((mid,clients[cli],line))
    bc(room,line)

def handle_private(cli,pk):
    to=pk.get("to",[]); sender=clients[cli]
    with lock:
        rec=[c for c,u in clients.items() if u in to and sender not in blocks.get(u,set())]
    bc_pkt(pk,rec,exc=cli)

# ──────────────── client thread ───────────────────
def client_thread(sock,addr):
    try:
        # login
        while True:
            safe(sock,"Enter username:\n")
            name=sock.recv(1024).decode(ENC).strip() or f"Anon{addr[1]}"
            with lock:
                if name not in clients.values(): break
            safe(sock,"Username taken, try again.\n")
        with lock:
            clients[sock]=name; user_rooms[sock]=None
            friends.setdefault(name,set()); blocks.setdefault(name,set()); pending.setdefault(name,set())
        notify_friend(name,True)
        safe(sock,f"{ts()} Hello {name}! Type /help\n")

        buf=""
        while True:
            data=sock.recv(65536)
            if not data: break
            buf+=data.decode(ENC)
            while "\n" in buf:
                line,buf=buf.split("\n",1)
                if not line: continue
                try:
                    obj=json.loads(line)
                    if isinstance(obj,dict) and obj.get("type"):
                        t=obj["type"]
                        if t=="file_start": ft_start(sock,obj)
                        elif t=="file_chunk": ft_chunk(sock,obj)
                        elif t=="file_end": ft_end(sock,obj)
                        elif t=="msg": handle_private(sock,obj)
                    else:
                        handle_text(sock,line)
                except json.JSONDecodeError:
                    handle_text(sock,line)
    finally:
        disconnect(sock)

def disconnect(sock):
    name=clients.pop(sock,"?")
    notify_friend(name,False)
    r=user_rooms.pop(sock,None)
    with lock:
        if r and sock in rooms.get(r,[]): rooms[r].remove(sock)
    if r: bc(r,f"{ts()} **{name} disconnected.**",exc=sock)
    try: sock.close()
    except: pass

# ──────────────── main ───────────────────────────
def main():
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        s.bind((HOST,PORT)); s.listen()
        print(ts(),"Server listening",HOST,PORT)
        while True:
            threading.Thread(target=client_thread,args=s.accept(),daemon=True).start()

if __name__=="__main__":
    try: main()
    except KeyboardInterrupt: sys.exit()
