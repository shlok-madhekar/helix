import curses
import time
import hashlib
import json
import os
import random

class File:
    def __init__(self, name, content=""):
        self.name = name
        self.content = content
        self.size = len(content)
    def to_dict(self):
        return {"type": "file", "name": self.name, "content": self.content}
    @staticmethod
    def from_dict(data):
        return File(data["name"], data.get("content", ""))

class Directory:
    def __init__(self, name):
        self.name = name
        self.contents = {}
    def add(self, obj):
        self.contents[obj.name] = obj
    def get(self, name):
        return self.contents.get(name)
    def list(self):
        return list(self.contents.keys())
    def to_dict(self):
        return {"type": "dir", "name": self.name, "contents": {k: v.to_dict() for k, v in self.contents.items()}}
    @staticmethod
    def from_dict(data):
        d = Directory(data["name"])
        for k, v in data.get("contents", {}).items():
            if v["type"] == "file":
                d.add(File.from_dict(v))
            else:
                d.add(Directory.from_dict(v))
        return d

def save_filesystem(root):
    with open("filesystem.tos", "w") as f:
        json.dump(root.to_dict(), f)

def load_filesystem():
    if os.path.exists("filesystem.tos"):
        with open("filesystem.tos", "r") as f:
            return Directory.from_dict(json.load(f))
    return None

def save_users(users):
    with open("users.tos", "w") as f:
        json.dump(users, f)

def load_users():
    if os.path.exists("users.tos"):
        with open("users.tos", "r") as f:
            return json.load(f)
    return None

users = {
    "guest": {"password": None, "home": "/home/guest"},
    "admin": {"password": hashlib.sha256(b"admin123").hexdigest(), "home": "/home/admin"}
}

root = load_filesystem()
if not root:
    root = Directory("/")
    home = Directory("home")
    root.add(home)
    home.add(Directory("guest"))
    home.add(Directory("admin"))
    root.add(Directory("etc"))
    root.add(Directory("var"))
else:
    home = root.get("home")

loaded_users = load_users()
if loaded_users:
    users.update(loaded_users)

cwd = root
path = [root]
current_user = None
logged_in = False

class Process:
    def __init__(self, pid, name, cpu=0.0, mem=0.0, owner="guest"):
        self.pid = pid
        self.name = name
        self.cpu = cpu
        self.mem = mem
        self.owner = owner

class ProcessManager:
    def __init__(self):
        self.processes = {}
        self.next_pid = 1000
        self.init_system()
    def init_system(self):
        procs = [
            (1, "systemd", 0.1, 2.5, "root"),
            (2, "kthreadd", 0.0, 0.0, "root"),
            (1234, "terminal-os", 1.2, 15.3, "guest"),
            (1235, "python3", 2.1, 25.7, "guest")
        ]
        for pid, name, cpu, mem, owner in procs:
            self.processes[pid] = Process(pid, name, cpu, mem, owner)
    def get_list(self):
        return list(self.processes.values())
    def kill(self, pid):
        if pid in self.processes and pid > 100:
            del self.processes[pid]
            return True
        return False

class PackageManager:
    def __init__(self):
        self.installed = {"coreutils": "8.32", "nano": "5.4"}
        self.available = {
            "cowsay": "3.04",
            "figlet": "2.2.5",
            "fortune": "1.99.1",
            "htop": "3.0.5",
            "vim": "8.2",
            "emacs": "27.2",
            "git": "2.34.1",
            "python3": "3.9.7",
            "nodejs": "16.13.0"
        }
    def install(self, name):
        if name in self.available:
            self.installed[name] = self.available[name]
            return True, self.available[name]
        return False, None
    def list_installed(self):
        return self.installed
    def list_available(self):
        return self.available
    def is_installed(self, name):
        return name in self.installed

procman = ProcessManager()
pkgman = PackageManager()

def get_home_dir(username):
    u = users.get(username)
    if u:
        parts = u["home"].strip("/").split("/")
        d = root
        for p in parts:
            d = d.get(p)
            if not d:
                return root
        return d
    return root

def main(stdscr):
    global cwd, path, current_user, logged_in, root
    curses.curs_set(1)
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()
    buffer = ["TerminalOS - Login required.", "Username:"]
    input_str = ""
    login_state = "username"
    temp_username = ""
    running = True

    def draw():
        stdscr.clear()
        for idx, line in enumerate(buffer[-(max_y-3):]):
            stdscr.addstr(idx+1, 2, line[:max_x-4])
        if logged_in:
            stdscr.addstr(max_y-2, 2, (f"{get_path()}$ " + input_str)[:max_x-4])
        else:
            if login_state == "password":
                stdscr.addstr(max_y-2, 2, ("Password: " + "*"*len(input_str))[:max_x-4])
            else:
                stdscr.addstr(max_y-2, 2, ("Username: " + input_str)[:max_x-4])
        stdscr.refresh()

    def get_path():
        return "/" + "/".join(d.name for d in path[1:])

    draw()
    while running:
        key = stdscr.getch()
        if key in (curses.KEY_BACKSPACE, 127):
            input_str = input_str[:-1]
        elif key == 10:
            if not logged_in:
                if login_state == "username":
                    temp_username = input_str.strip()
                    if temp_username in users:
                        login_state = "password"
                        buffer.append("Password:")
                    else:
                        buffer.append("Invalid username. Username:")
                    input_str = ""
                elif login_state == "password":
                    pw = input_str.strip()
                    u = users[temp_username]
                    if u["password"] is None or u["password"] == hashlib.sha256(pw.encode()).hexdigest():
                        current_user = temp_username
                        logged_in = True
                        login_state = "logged_in"
                        cwd = get_home_dir(current_user)
                        path = [root, root.get("home"), root.get("home").get(current_user)]
                        buffer.append(f"Login successful. Welcome, {current_user}!")
                    else:
                        buffer.append("Invalid password. Username:")
                        login_state = "username"
                    input_str = ""
                draw()
                continue
            buffer.append(f"{get_path()}$ " + input_str)
            cmd = input_str.strip()
            parts = cmd.split()
            if not parts:
                input_str = ""
                draw()
                continue
            c = parts[0]
            args = parts[1:]
            if c == "help":
                buffer.append("Available: help, clear, exit, ls, cd, mkdir, touch, cat, whoami, logout, save, load, ps, kill, top, pkg")
            elif c == "clear":
                buffer = []
            elif c == "exit":
                buffer.append("Exiting TerminalOS...")
                draw()
                time.sleep(1)
                break
            elif c == "ls":
                items = cwd.list()
                if not items:
                    buffer.append("")
                else:
                    buffer.append("  ".join(sorted(items)))
            elif c == "cd":
                if not args:
                    input_str = ""
                    draw()
                    continue
                if args[0] == "..":
                    if len(path) > 1:
                        path.pop()
                        cwd = path[-1]
                elif args[0] in cwd.contents and isinstance(cwd.contents[args[0]], Directory):
                    cwd = cwd.contents[args[0]]
                    path.append(cwd)
                else:
                    buffer.append(f"cd: no such directory: {args[0]}")
            elif c == "mkdir":
                if not args:
                    buffer.append("mkdir: missing operand")
                elif args[0] in cwd.contents:
                    buffer.append(f"mkdir: cannot create directory '{args[0]}': File exists")
                else:
                    cwd.add(Directory(args[0]))
            elif c == "touch":
                if not args:
                    buffer.append("touch: missing file operand")
                elif args[0] in cwd.contents:
                    obj = cwd.contents[args[0]]
                    if isinstance(obj, File):
                        obj.size = len(obj.content)
                else:
                    cwd.add(File(args[0], ""))
            elif c == "cat":
                if not args:
                    buffer.append("cat: missing file operand")
                elif args[0] in cwd.contents and isinstance(cwd.contents[args[0]], File):
                    buffer.extend(cwd.contents[args[0]].content.splitlines() or [""])
                else:
                    buffer.append(f"cat: {args[0]}: No such file")
            elif c == "whoami":
                buffer.append(current_user)
            elif c == "logout":
                logged_in = False
                current_user = None
                login_state = "username"
                buffer.append("Logged out. Username:")
            elif c == "save":
                try:
                    save_filesystem(root)
                    save_users(users)
                    buffer.append("System state saved.")
                except Exception as e:
                    buffer.append(f"Save failed: {e}")
            elif c == "load":
                try:
                    r = load_filesystem()
                    if r:
                        root = r
                        home = root.get("home")
                        cwd = get_home_dir(current_user) if current_user else root
                        path = [root, root.get("home"), root.get("home").get(current_user)] if current_user else [root]
                        buffer.append("Filesystem loaded.")
                    u = load_users()
                    if u:
                        users.clear()
                        users.update(u)
                        buffer.append("User data loaded.")
                except Exception as e:
                    buffer.append(f"Load failed: {e}")
            elif c == "ps":
                procs = procman.get_list()
                buffer.append("  PID USER     CPU  MEM COMMAND")
                for p in sorted(procs, key=lambda x: x.pid):
                    buffer.append(f"{p.pid:5} {p.owner:8} {p.cpu:4.1f} {p.mem:4.1f} {p.name}")
            elif c == "kill":
                if not args:
                    buffer.append("kill: missing process ID")
                else:
                    try:
                        pid = int(args[0])
                        if procman.kill(pid):
                            buffer.append(f"Process {pid} killed")
                        else:
                            buffer.append(f"kill: ({pid}) - No such process")
                    except Exception:
                        buffer.append("kill: invalid process ID")
            elif c == "top":
                procs = procman.get_list()
                buffer.append("  PID USER     CPU  MEM COMMAND")
                for p in sorted(procs, key=lambda x: -x.cpu)[:10]:
                    buffer.append(f"{p.pid:5} {p.owner:8} {p.cpu:4.1f} {p.mem:4.1f} {p.name}")
            elif c == "pkg":
                if not args:
                    buffer.append("Usage: pkg [install|list|available] [package]")
                elif args[0] == "install":
                    if len(args) > 1:
                        ok, ver = pkgman.install(args[1])
                        if ok:
                            buffer.append(f"Installed {args[1]} {ver}")
                        else:
                            buffer.append(f"pkg: package '{args[1]}' not found")
                    else:
                        buffer.append("pkg install: missing package name")
                elif args[0] == "list":
                    inst = pkgman.list_installed()
                    buffer.append("Installed packages:")
                    for k, v in inst.items():
                        buffer.append(f"  {k} {v}")
                elif args[0] == "available":
                    avail = pkgman.list_available()
                    buffer.append("Available packages:")
                    for k, v in avail.items():
                        if not pkgman.is_installed(k):
                            buffer.append(f"  {k} {v}")
            else:
                buffer.append(f"Unknown command: {cmd}")
            input_str = ""
        elif 0 <= key <= 255:
            input_str += chr(key)
        draw()

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\nShutting down TerminalOS...") 