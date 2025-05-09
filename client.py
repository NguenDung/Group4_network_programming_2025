import socket
import threading
import datetime
import re
import sys
import tkinter as tk
from tkinter import filedialog
import json
import base64
import os
import shlex

HOST = '127.0.0.1'
PORT = 12345

username = ""
room = None
user_colors = {}
file_receivers = {}

# Generate ANSI color code based on username hash (256-color)
def get_color_for_user(user):
    code = 16 + (abs(hash(user)) % 224)
    return f"\033[38;5;{code}m"
RESET_COLOR = "\033[0m"

# Timestamp only hour:minute
def timestamp():
    return datetime.datetime.now().strftime("[%H:%M]")

# Print with tagged users highlighted
def print_message(message):
    def repl(match):
        user = match.group(1)
        if user not in user_colors:
            user_colors[user] = get_color_for_user(user)
        return f"{user_colors[user]}@{user}{RESET_COLOR}"
    highlighted = re.sub(r"@(\w+)", repl, message)
    print(highlighted, end='')

# Receive thread
def receive_messages(sock):
    buffer = ""
    while True:
        try:
            data = sock.recv(65536)
            if not data:
                break
            buffer += data.decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line:
                    continue
                # JSON packet handling
                try:
                    packet = json.loads(line)
                    ptype = packet.get("type")
                    if ptype == "file_start":
                        fname = packet["filename"]
                        size = packet["size"]
                        sender = packet.get("from")
                        print(f"{timestamp()} Receiving {fname} ({size} bytes) from {sender}")
                        os.makedirs("downloads", exist_ok=True)
                        fobj = open(os.path.join("downloads", fname), "wb")
                        file_receivers[fname] = {'f': fobj, 'size': size, 'recv': 0}
                    elif ptype == "file_chunk":
                        fname = packet["filename"]
                        rec = file_receivers.get(fname)
                        if rec:
                            try:
                                chunk = base64.b64decode(packet["data"].encode())
                                rec['f'].write(chunk)
                                rec['recv'] += len(chunk)
                                pct = rec['recv'] / rec['size'] * 100
                                print(f"{timestamp()} Receiving {fname}: {pct:.2f}%")
                                if rec['recv'] >= rec['size']:
                                    rec['f'].close()
                                    print(f"{timestamp()} File {fname} received.")
                                    del file_receivers[fname]
                            except Exception as e:
                                print(f"{timestamp()} Error receiving chunk for {fname}: {e}")
                    elif ptype == "msg":
                        sender = packet.get("from")
                        text = packet.get("text")
                        print(f"{timestamp()} [PRIVATE] {sender}: {text}")
                except json.JSONDecodeError:
                    # Plain text
                    print_message(line + "\n")
                except Exception as e:
                    print(f"{timestamp()} Error processing incoming packet: {e}")
        except Exception:
            print(f"{timestamp()} Connection lost.")
            break

# Send thread
def send_messages(sock):
    global username
    while True:
        try:
            raw = input(">> ")
            parts = shlex.split(raw)
            if not parts:
                continue
            cmd = parts[0]
            if cmd == "/sendfile":
                to_list = [p[1:] for p in parts[1:] if p.startswith("@")]
                # File types filter: audio, pdf, text, images
                root = tk.Tk(); root.withdraw()
                file_path = filedialog.askopenfilename(
                    filetypes=[
                        ("Audio files", "*.mp3 *.wav"),
                        ("PDF files", "*.pdf"),
                        ("Text files", "*.txt"),
                        ("Image files", "*.jpg *.jpeg *.png")
                    ]
                )
                root.destroy()
                if not file_path:
                    continue
                fname = os.path.basename(file_path)
                size = os.path.getsize(file_path)
                try:
                    # Send header
                    packet = {'type':'file_start','filename':fname,'size':size,'to':to_list,'from':username}
                    sock.sendall((json.dumps(packet)+"\n").encode())
                    sent = 0
                    # Send chunks
                    with open(file_path, "rb") as f:
                        while True:
                            chunk = f.read(4096)
                            if not chunk:
                                break
                            packet = {'type':'file_chunk','filename':fname,'data':base64.b64encode(chunk).decode(),'from':username}
                            sock.sendall((json.dumps(packet)+"\n").encode())
                            sent += len(chunk)
                            pct = sent / size * 100
                            print(f"{timestamp()} Sending {fname}: {pct:.2f}%")
                    print(f"{timestamp()} File {fname} sent.")
                except Exception as e:
                    print(f"{timestamp()} Error sending file {fname}: {e}")
            elif cmd == "/msg":
                to_list = [p[1:] for p in parts[1:] if p.startswith("@")]
                text = " ".join([p for p in parts[1:] if not p.startswith("@")])
                packet = {'type':'msg','to':to_list,'text':text,'from':username}
                sock.sendall((json.dumps(packet)+"\n").encode())
            else:
                sock.sendall((raw+"\n").encode())
                if cmd == "/quit":
                    break
        except Exception as e:
            print(f"{timestamp()} Error processing command: {e}")
            break

# Main
def main():
    global username
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
    except Exception:
        print(f"{timestamp()} Cannot connect to server.")
        sys.exit()
    welcome = sock.recv(2048).decode()
    print(welcome, end='')
    username = input(">> ")
    sock.sendall((username+"\n").encode())
    greeting = sock.recv(2048).decode()
    print(greeting, end='')
    threading.Thread(target=receive_messages, args=(sock,), daemon=True).start()
    send_messages(sock)
    sock.close()

if __name__ == "__main__":
    main()
