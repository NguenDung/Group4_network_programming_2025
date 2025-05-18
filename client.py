#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Client v15 – +/pdf, async transfer thread, corruption check, forward support.
"""

import socket, threading, datetime, json, base64, os, shlex, tempfile, subprocess, platform, shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from urllib.request import urlretrieve
from PIL import Image, ImageTk
try: import readline
except ImportError: readline=None

HOST, PORT = '127.0.0.1', 12345
CHUNK, BAR = 4096, 20

username=""; current_room=[None]
transfers, skipped, cmdq = {}, {}, []

# ───── command groups ─────
MENU ={"/room","/create","/join","/rename","/delete","/count","/online","/clean","/quit"}
CHAT ={"/leave","/rename","/users","/recall","/reply","/pin","/pinned","/unpin","/msg",
       "/invitefriend","/forward"}
FILE ={"/sendfile","/pic","/mp3","/mp4","/text","/gif","/pdf","/open","/save"}
FRI  ={"/addfriend","/acceptfriend","/myfriends","/unfriend","/block"}

ALL_CMDS = sorted(MENU|CHAT|FILE|FRI|{"/help"})
if readline:
    readline.parse_and_bind("tab: complete")
    readline.set_completer(lambda t,s:[c for c in ALL_CMDS if c.startswith(t)][s]
                           if s<len([c for c in ALL_CMDS if c.startswith(t)]) else None)

def ts(): return datetime.datetime.now().strftime("[%H:%M]")
def bar(p): f=int(p/BAR); return "#"*f+"."*(BAR-f)
def sname(n): return n[:20]+"…" if len(n)>20 else n

# ───── pop-ups ─────
def gif_popup(p):
    img=Image.open(p); frames=[]
    try:
        while True:
            frames.append(ImageTk.PhotoImage(img.copy())); img.seek(len(frames))
    except EOFError: pass
    root=tk.Tk(); root.title(os.path.basename(p)); lbl=tk.Label(root); lbl.pack()
    delay=img.info.get("duration",100)
    def loop(i=0): lbl.configure(image=frames[i]); root.after(delay,loop,(i+1)%len(frames))
    loop(); root.mainloop()

def open_file(p):
    if p.lower().endswith(".gif"):
        threading.Thread(target=gif_popup,args=(p,),daemon=True).start()
    elif platform.system()=="Windows": os.startfile(p)
    elif platform.system()=="Darwin": subprocess.Popen(["open",p])
    else: subprocess.Popen(["xdg-open",p])

def invite_popup(pk):
    root=tk.Tk(); root.withdraw()
    if messagebox.askyesno("Invite",f"{pk['from']} invites you to {pk['room']}.\nJoin?"):
        cmdq.append(f"/join {pk['room']}")
    root.destroy()

def friend_popup(pk):
    root=tk.Tk(); root.withdraw()
    if messagebox.askyesno("Friend request",f"{pk['from']} wants to be friends.\nAccept?"):
        cmdq.append(f"/acceptfriend {pk['from']}")
    root.destroy()

# ───── network receive ─────
def send_json(s,o): s.sendall((json.dumps(o)+"\n").encode())

def recv_thread(sock):
    buf=""
    while True:
        try:
            d=sock.recv(65536)
            if not d: print(ts(),"Disconnected"); break
            buf+=d.decode()
            while "\n" in buf:
                line,buf=buf.split("\n",1)
                if not line: continue
                try:
                    pk=json.loads(line); t=pk.get("type")
                    if t=="file_start": file_start(pk)
                    elif t=="file_chunk": file_chunk(pk)
                    elif t=="file_end": file_end(pk)
                    elif t=="invite": invite_popup(pk)
                    elif t=="friendreq": friend_popup(pk)
                    elif t=="msg": print(f"{ts()} [PM] {pk['from']}: {pk['text']}")
                except json.JSONDecodeError:
                    print(line)
        except: break

def file_start(pk):
    fn, sz, sender = pk["filename"], pk["size"], pk["from"]
    root=tk.Tk(); root.withdraw()
    choice = messagebox.askyesnocancel(
        "Incoming file",
        f"{sender} sent {fn} ({sz} B).\n"
        "Yes = Open & Save   No = Save   Cancel = Skip"
    )
    keep = choice is not None
    view = choice is True
    root.destroy()
    os.makedirs("downloads",exist_ok=True)
    f=open(os.path.join("downloads",fn),"wb") if keep else tempfile.NamedTemporaryFile(delete=False)
    transfers[fn]={"f":f,"got":0,"size":sz,"keep":keep,"view":view}

def file_chunk(pk):
    tr=transfers.get(pk["filename"])
    if tr:
        chunk=base64.b64decode(pk["data"]); tr["f"].write(chunk); tr["got"]+=len(chunk)
        pct=tr["got"]/tr["size"]*100
        print(f"\r{ts()} Recv {sname(pk['filename'])} [{bar(pct)}] {pct:5.1f}%",end="",flush=True)

def file_end(pk):
    fn=pk["filename"]; tr=transfers.pop(fn,None)
    if not tr: return
    tr["f"].close()
    ok = tr["got"] == tr["size"]
    p = os.path.join("downloads",fn) if tr["keep"] else tr["f"].name
    if ok:
        print(f"\r{ts()} Saved {fn}",' '*8)
        if tr["view"]: open_file(p)
        if not tr["keep"]: skipped[fn]=p
    else:
        print(f"\r{ts()} ERROR: {fn} corrupted (expected {tr['size']}, got {tr['got']})",' '*8)
        if not tr["keep"]: os.remove(p)

# ───── send-file helpers ─────
def transfer(sock,path,tags):
    fn,sz=os.path.basename(path),os.path.getsize(path)
    send_json(sock,{"type":"file_start","filename":fn,"size":sz,"to":tags,"from":username})
    sent=0
    with open(path,"rb") as fp:
        while (chunk:=fp.read(CHUNK)):
            sent+=len(chunk); pct=sent/sz*100
            send_json(sock,{"type":"file_chunk","filename":fn,
                            "data":base64.b64encode(chunk).decode(),"from":username})
            print(f"\r{ts()} Send {sname(fn)} [{bar(pct)}] {pct:5.1f}%",end="",flush=True)
    send_json(sock,{"type":"file_end","filename":fn,"from":username})
    print(f"\r{ts()} File {fn} sent.",' '*8)

def browse(ftype,tags,sock):
    root=tk.Tk(); root.withdraw()
    p=filedialog.askopenfilename(filetypes=[ftype]); root.destroy()
    if p:
        threading.Thread(target=transfer,args=(sock,p,tags),daemon=True).start()

def fetch_gif(sock,url,tags):
    tmp=os.path.join(tempfile.gettempdir(), os.path.basename(url.split('/')[-1] or "tmp.gif"))
    urlretrieve(url,tmp)
    transfer(sock,tmp,tags)
    os.remove(tmp)

# ───── sender loop ─────
def sender(sock):
    FT={"/sendfile":("All","*.*"),
        "/pic":     ("Images","*.jpg *.jpeg *.png"),
        "/mp3":     ("Audio","*.mp3 *.wav"),
        "/mp4":     ("Video","*.mp4"),
        "/text":    ("Text","*.txt"),
        "/pdf":     ("PDF","*.pdf")}
    while True:
        raw=cmdq.pop(0) if cmdq else input(">> ")
        if raw in {"1","2","3","4"}: raw=f"/help {raw}"
        if not raw: continue

        parts=shlex.split(raw); cmd=parts[0]
        tags=[p[1:] for p in parts[1:] if p.startswith("@")]
        room=current_room[0]

        if cmd in CHAT|FILE and not room and cmd not in {"/rename","/forward"}:
            print("Join a room first."); continue
        if cmd=="/clean" and room:
            print("Cannot /clean inside a room."); continue

        if cmd in FT:
            browse(FT[cmd],tags,sock)
        elif cmd=="/gif":
            if len(parts)<2: print("Usage /gif <url>"); continue
            threading.Thread(target=fetch_gif,args=(sock,parts[1],tags),daemon=True).start()
        elif cmd=="/open":
            if len(parts)<2: print("Usage /open <file>"); continue
            fn=parts[1]
            p=os.path.join("downloads",fn) if os.path.exists(os.path.join("downloads",fn)) else skipped.get(fn)
            open_file(p) if p and os.path.exists(p) else print("File not found.")
        elif cmd=="/save":
            if len(parts)<2 or parts[1] not in skipped: print("Usage /save <skipped_file>"); continue
            fn=parts[1]; os.makedirs("downloads",exist_ok=True)
            shutil.move(skipped[fn],os.path.join("downloads",fn)); del skipped[fn]; print("Saved.")
        elif cmd=="/clean":
            os.system("cls" if platform.system()=="Windows" else "clear")
            sock.sendall((cmd+"\n").encode())
        elif cmd=="/msg":
            txt=" ".join(p for p in parts[1:] if not p.startswith("@"))
            send_json(sock,{"type":"msg","to":tags,"text":txt,"from":username})
        else:
            sock.sendall((raw+"\n").encode())
            if cmd=="/join" and len(parts)>1: current_room[0]=parts[1]
            if cmd=="/leave": current_room[0]=None
            if cmd=="/quit": break

# ───── main ─────
def main():
    global username
    sock=socket.socket(); sock.connect((HOST,PORT))
    print(sock.recv(1024).decode(),end='')
    username=input(">> ").strip()
    sock.sendall((username+"\n").encode())
    print(sock.recv(1024).decode(),end='')
    threading.Thread(target=recv_thread,args=(sock,),daemon=True).start()
    sender(sock); sock.close()

if __name__=="__main__":
    main()
