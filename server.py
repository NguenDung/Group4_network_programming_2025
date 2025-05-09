import socket
import threading
import datetime
from collections import deque
import json

HOST = '127.0.0.1'
PORT = 12345

clients = {}
user_rooms = {}
rooms = {"room1": [], "room2": [], "room3": []}
msg_id_counter = {r: 1 for r in rooms}
history = {r: deque(maxlen=1000) for r in rooms}
active_transfers = {}  # (client, filename) -> list of recipients

data_lock = threading.Lock()

def timestamp():
    return datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

def broadcast_message(message, room, exclude=None):
    with data_lock:
        recipients = list(rooms.get(room, []))
    for c in recipients:
        if c != exclude:
            try:
                c.sendall((message + "\n").encode())
            except:
                pass

def broadcast_packet(packet, recipients, exclude=None):
    data = json.dumps(packet) + "\n"
    for c in recipients:
        if c != exclude:
            try:
                c.sendall(data.encode())
            except:
                pass

def handle_client(client, address):
    try:
        client.sendall(f"{timestamp()} Welcome! Please enter your username:\n".encode())
        username = client.recv(1024).decode().strip()
        with data_lock:
            clients[client] = username
            user_rooms[client] = None
        print(f"{timestamp()} {username} connected from {address}")
        client.sendall(f"{timestamp()} Hello {username}! Use /help to see commands.\n".encode())

        buffer = ""
        while True:
            data = client.recv(65536)
            if not data:
                break
            buffer += data.decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line:
                    continue
                try:
                    packet = json.loads(line)
                    ptype = packet.get("type")
                    if ptype == "file_start":
                        handle_file_start(client, packet)
                    elif ptype == "file_chunk":
                        handle_file_chunk(client, packet)
                    elif ptype == "msg":
                        handle_private_msg(client, packet)
                except json.JSONDecodeError:
                    handle_text_message(client, line)
    except Exception as e:
        print(f"{timestamp()} Error: {e}")
    finally:
        disconnect_client(client)

def handle_text_message(client, msg):
    with data_lock:
        room = user_rooms.get(client)
    if msg.startswith("/"):
        handle_command(client, msg, room)
    else:
        if room:
            with data_lock:
                mid = msg_id_counter[room]; msg_id_counter[room] += 1
                ts = timestamp(); sender = clients[client]
                history[room].append((mid, ts, sender, msg))
            log = f"{ts} [MSG #{mid}] {sender}: {msg}"
            broadcast_message(f"[MSG #{mid}] {sender}: {msg}", room)
            print(log)
        else:
            client.sendall(f"{timestamp()} You must join a room to chat.\n".encode())

def handle_file_start(client, packet):
    filename = packet["filename"]
    to = packet.get("to")
    with data_lock:
        room = user_rooms.get(client)
        if to:
            recipients = [c for c,u in clients.items() if u in to and c in rooms.get(room,[])]
        else:
            recipients = list(rooms.get(room, []))
        active_transfers[(client, filename)] = recipients
    broadcast_packet(packet, recipients, exclude=client)

def handle_file_chunk(client, packet):
    filename = packet["filename"]
    with data_lock:
        recipients = active_transfers.get((client, filename), [])
    broadcast_packet(packet, recipients, exclude=client)

def handle_private_msg(client, packet):
    to = packet.get("to", [])
    recipients = [c for c,u in clients.items() if u in to]
    broadcast_packet(packet, recipients, exclude=client)

def handle_command(client, msg, room):
    args = msg.split()
    cmd = args[0]

    if cmd == "/help":
        help_menu = (
            "/room, /create [name], /join [name], /leave, /rename [name], /users, "
            "/count, /online, /delete [room], /recall [id], /reply [id] [msg], "
            "/sendfile [@user...], /msg @user... [text], /quit\n"
        )
        client.sendall(f"{timestamp()} {help_menu}".encode())

    elif cmd == "/room":
        with data_lock:
            room_list = ", ".join(rooms.keys())
        client.sendall(f"{timestamp()} Available rooms: {room_list}\n".encode())

    elif cmd == "/create":
        if len(args) < 2:
            client.sendall(f"{timestamp()} Usage: /create [room_name]\n".encode())
        else:
            room_name = args[1]
            with data_lock:
                if room_name in rooms:
                    exists = True
                else:
                    rooms[room_name] = []
                    msg_id_counter[room_name] = 1
                    history[room_name] = deque(maxlen=1000)
                    exists = False
            if exists:
                client.sendall(f"{timestamp()} Room already exists.\n".encode())
            else:
                client.sendall(f"{timestamp()} Room '{room_name}' created successfully.\n".encode())

    elif cmd == "/join":
        if len(args) < 2:
            client.sendall(f"{timestamp()} Usage: /join [room_name]\n".encode())
        else:
            room_name = args[1]
            with data_lock:
                if room_name not in rooms:
                    client.sendall(f"{timestamp()} Room doesn't exist.\n".encode())
                    return
                prev_room = user_rooms[client]
                if prev_room and client in rooms[prev_room]:
                    rooms[prev_room].remove(client)
                rooms[room_name].append(client)
                user_rooms[client] = room_name
            client.sendall(f"{timestamp()} Joined {room_name}.\n".encode())

    elif cmd == "/leave":
        if room:
            with data_lock:
                rooms[room].remove(client)
                user_rooms[client] = None
            client.sendall(f"{timestamp()} Left the room.\n".encode())
        else:
            client.sendall(f"{timestamp()} You are not in any room.\n".encode())

    elif cmd == "/rename":
        if len(args) < 2:
            client.sendall(f"{timestamp()} Usage: /rename [new_name]\n".encode())
        else:
            new_name = args[1]
            with data_lock:
                old_name = clients[client]
                clients[client] = new_name
            client.sendall(f"{timestamp()} Renamed from {old_name} to {new_name}.\n".encode())

    elif cmd == "/users":
        if room:
            with data_lock:
                names = [clients[c] for c in rooms[room]]
            client.sendall(f"{timestamp()} Users in {room}: {', '.join(names)}\n".encode())
        else:
            client.sendall(f"{timestamp()} You are not in a room.\n".encode())

    elif cmd == "/count":
        with data_lock:
            cnt = ", ".join([f"{r}: {len(lst)}" for r,lst in rooms.items()])
        client.sendall(f"{timestamp()} Room users count: {cnt}\n".encode())

    elif cmd == "/online":
        with data_lock:
            total = len(clients)
        client.sendall(f"{timestamp()} Total online users: {total}\n".encode())

    elif cmd == "/delete":
        if len(args) < 2:
            client.sendall(f"{timestamp()} Usage: /delete [room_name]\n".encode())
        else:
            room_name = args[1]
            with data_lock:
                if room_name in rooms:
                    for c in rooms[room_name]:
                        user_rooms[c] = None
                        c.sendall(f"{timestamp()} Room '{room_name}' was deleted.\n".encode())
                    del rooms[room_name]
                    del msg_id_counter[room_name]
                    del history[room_name]
                    deleted = True
                else:
                    deleted = False
            if deleted:
                client.sendall(f"{timestamp()} Room '{room_name}' deleted.\n".encode())
            else:
                client.sendall(f"{timestamp()} Room does not exist.\n".encode())

    elif cmd == "/recall":
        if not room:
            client.sendall(f"{timestamp()} You are not in a room.\n".encode())
        elif len(args) < 2:
            client.sendall(f"{timestamp()} Usage: /recall [id]\n".encode())
        else:
            try:
                rid = int(args[1])
            except:
                client.sendall(f"{timestamp()} Invalid message ID.\n".encode())
                return
            with data_lock:
                rec = next((h for h in history[room] if h[0] == rid), None)
                if rec:
                    user_orig = rec[2]
                    history[room] = deque([h for h in history[room] if h[0] != rid], maxlen=1000)
            if rec:
                broadcast_message(f"[MSG #{rid}] {user_orig} đã thu hồi tin nhắn.", room)
                print(f"{timestamp()} [MSG #{rid}] {user_orig} đã thu hồi tin nhắn.")
            else:
                client.sendall(f"{timestamp()} Message ID {rid} not found.\n".encode())

    elif cmd == "/reply":
        if not room:
            client.sendall(f"{timestamp()} You are not in a room.\n".encode())
        elif len(args) < 3:
            client.sendall(f"{timestamp()} Usage: /reply [id] [msg]\n".encode())
        else:
            try:
                orig_id = int(args[1])
            except:
                client.sendall(f"{timestamp()} Invalid message ID.\n".encode())
                return
            reply_msg = " ".join(args[2:])
            with data_lock:
                rec = next((h for h in history[room] if h[0] == orig_id), None)
            if not rec:
                client.sendall(f"{timestamp()} Message ID {orig_id} not found.\n".encode())
            else:
                with data_lock:
                    new_id = msg_id_counter[room]; msg_id_counter[room] += 1
                    ts = timestamp(); sender = clients[client]
                    history[room].append((new_id, ts, sender, reply_msg))
                orig_user = rec[2]
                log = f"{ts} [MSG #{new_id}] {sender} replied to [MSG #{orig_id}] {orig_user}: {reply_msg}"
                broadcast_message(f"{log}", room)
                print(log)

    elif cmd == "/sendfile" or cmd == "/msg":
        # Handled client-side
        pass

    elif cmd == "/quit":
        client.sendall(f"{timestamp()} Bye!\n".encode())
        disconnect_client(client)

    else:
        client.sendall(f"{timestamp()} Unknown command. Type /help.\n".encode())

def disconnect_client(client):
    with data_lock:
        name = clients.pop(client, "Unknown")
        room = user_rooms.pop(client, None)
        if room and client in rooms.get(room, []):
            rooms[room].remove(client)
    print(f"{timestamp()} Disconnected: {name}")
    try: client.close()
    except: pass

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT)); s.listen()
        print(f"{timestamp()} Server running on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()