import curses
import time
import hashlib
import json
import os
import random
import re

class File:
    def __init__(self, name, content="", owner="guest", mode=644):
        self.name = name
        self.content = content
        self.size = len(content)
        self.owner = owner
        self.mode = mode
    def to_dict(self):
        return {"type": "file", "name": self.name, "content": self.content, "owner": self.owner, "mode": self.mode}
    @staticmethod
    def from_dict(data):
        return File(data["name"], data.get("content", ""), data.get("owner", "guest"), data.get("mode", 644))

class Symlink:
    def __init__(self, name, target, owner="guest", mode=777):
        self.name = name
        self.target = target  # Path string
        self.owner = owner
        self.mode = mode
    def to_dict(self):
        return {"type": "symlink", "name": self.name, "target": self.target, "owner": self.owner, "mode": self.mode}
    @staticmethod
    def from_dict(data):
        return Symlink(data["name"], data["target"], data.get("owner", "guest"), data.get("mode", 777))

class Hardlink:
    def __init__(self, name, target_file, owner="guest", mode=644):
        self.name = name
        self.target_file = target_file  # Reference to File object
        self.owner = owner
        self.mode = mode
    def to_dict(self):
        return {"type": "hardlink", "name": self.name, "target": self.target_file.name, "owner": self.owner, "mode": self.mode}
    @staticmethod
    def from_dict(data, directory):
        # Find the file in the directory by name
        target = directory.get(data["target"])
        return Hardlink(data["name"], target, data.get("owner", "guest"), data.get("mode", 644))

class Directory:
    def __init__(self, name, owner="guest", mode=755, max_size=None):
        self.name = name
        self.contents = {}
        self.owner = owner
        self.mode = mode
        self.max_size = max_size  # in bytes, None means unlimited
    def add(self, obj):
        self.contents[obj.name] = obj
    def get(self, name):
        return self.contents.get(name)
    def list(self):
        return list(self.contents.keys())
    def to_dict(self):
        return {"type": "dir", "name": self.name, "contents": {k: v.to_dict() for k, v in self.contents.items()}, "owner": self.owner, "mode": self.mode, "max_size": self.max_size}
    @staticmethod
    def from_dict(data):
        d = Directory(data["name"], data.get("owner", "guest"), data.get("mode", 755), data.get("max_size"))
        for k, v in data.get("contents", {}).items():
            if v["type"] == "file":
                d.add(File.from_dict(v))
            elif v["type"] == "dir":
                d.add(Directory.from_dict(v))
            elif v["type"] == "symlink":
                d.add(Symlink.from_dict(v))
            elif v["type"] == "hardlink":
                pass
        for k, v in data.get("contents", {}).items():
            if v["type"] == "hardlink":
                d.add(Hardlink.from_dict(v, d))
        return d
    def get_size(self, seen=None):
        if seen is None:
            seen = set()
        size = 0
        for obj in self.contents.values():
            if isinstance(obj, File):
                if id(obj) not in seen:
                    size += obj.size
                    seen.add(id(obj))
            elif isinstance(obj, Directory):
                size += obj.get_size(seen)
            elif isinstance(obj, Hardlink):
                if id(obj.target_file) not in seen:
                    size += obj.target_file.size
                    seen.add(id(obj.target_file))
            # Symlinks do not add to disk usage (just a pointer)
        return size

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
    "guest": {"password": None, "home": "/home/guest", "uid": 1000},
    "admin": {"password": hashlib.sha256(b"admin123").hexdigest(), "home": "/home/admin", "uid": 0}
}

root = load_filesystem()
if not root:
    root = Directory("/", max_size=1024*1024)  # 1MB
    home = Directory("home", max_size=512*1024)  # 512KB
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

class MountManager:
    def __init__(self):
        self.mounts = {
            "/": {"device": "/dev/sda1", "type": "ext4", "mounted": True},
            "/home": {"device": "/dev/sda2", "type": "ext4", "mounted": True}
        }
        self.available_devices = {
            "usb1": {"path": "/media/usb1", "file": "usb1.tos", "mounted": False},
            "usb2": {"path": "/media/usb2", "file": "usb2.tos", "mounted": False}
        }
    def mount_device(self, device):
        if device in self.available_devices and not self.available_devices[device]["mounted"]:
            self.available_devices[device]["mounted"] = True
            mount_point = self.available_devices[device]["path"]
            self.mounts[mount_point] = {
                "device": f"/dev/{device}",
                "type": "vfat",
                "mounted": True
            }
            return True, mount_point
        return False, None
    def unmount_device(self, device):
        if device in self.available_devices and self.available_devices[device]["mounted"]:
            self.available_devices[device]["mounted"] = False
            mount_point = self.available_devices[device]["path"]
            if mount_point in self.mounts:
                del self.mounts[mount_point]
            return True
        return False

procman = ProcessManager()
pkgman = PackageManager()
mountman = MountManager()

network_up = True
ip_address = "192.168.1.100"

class TerminalWindow:
    def __init__(self, id):
        self.id = id
        self.buffer = ["TerminalOS - Login required.", "Username:"]
        self.input_str = ""
        self.cwd = root
        self.path = [root]
        self.current_user = None
        self.logged_in = False
        self.login_state = "username"
        self.temp_username = ""
        self.sudo_mode = False
        self.sudo_timestamp = 0
        self.command_history = []
        self.history_index = -1
        self.help_active = False
        self.help_scroll_offset = 0

windows = [TerminalWindow(0)]
current_window = 0

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

def is_root(username):
    return users.get(username, {}).get("uid", 1000) == 0

def parse_symbolic_chmod(symbolic, current_mode):
    # Only supports u/g/o/a, +-=, and rwx
    mode = current_mode
    for clause in symbolic.split(","):
        m = re.match(r"([ugoa]*)([+-=])([rwx]+)", clause)
        if not m:
            continue
        who, op, perms = m.groups()
        if not who:
            who = "a"
        for w in who:
            for p in perms:
                shift = {"u": 6, "g": 3, "o": 0}[w] if w in "ugo" else None
                if w == "a":
                    for subw in "ugo":
                        shift = {"u": 6, "g": 3, "o": 0}[subw]
                        bit = {"r": 4, "w": 2, "x": 1}[p] << shift
                        if op == "+":
                            mode |= bit
                        elif op == "-":
                            mode &= ~bit
                        elif op == "=":
                            # Clear then set
                            mask = 7 << shift
                            mode &= ~mask
                            mode |= {"r": 4, "w": 2, "x": 1}[p] << shift
                else:
                    bit = {"r": 4, "w": 2, "x": 1}[p] << shift
                    if op == "+":
                        mode |= bit
                    elif op == "-":
                        mode &= ~bit
                    elif op == "=":
                        mask = 7 << shift
                        mode &= ~mask
                        mode |= {"r": 4, "w": 2, "x": 1}[p] << shift
    return mode

def main(stdscr):
    global root
    curses.curs_set(1)
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()
    global current_window, network_up
    running = True

    def draw():
        stdscr.clear()
        win = windows[current_window]
        if win.help_active:
            help_lines = [
                "Available commands:",
                "help",
                "clear",
                "exit",
                "ls",
                "cd",
                "mkdir",
                "touch",
                "cat",
                "whoami",
                "logout",
                "save",
                "load",
                "ps",
                "kill",
                "top",
                "pkg",
                "ping",
                "ifconfig",
                "curl",
                "mount",
                "umount",
                "chmod",
                "chown",
                "sudo",
                "df",
                "du",
                "ln"
            ]
            start = win.help_scroll_offset
            end = min(start + max_y - 3, len(help_lines))
            for idx, line in enumerate(help_lines[start:end]):
                stdscr.addstr(idx+1, 2, line[:max_x-4])
            stdscr.addstr(max_y-2, 2, "(UP/DOWN to scroll, any key to exit help)")
            status = f"Win {current_window+1}/{len(windows)}"
            stdscr.addstr(0, max_x-len(status)-2, status)
            stdscr.refresh()
            return
        for idx, line in enumerate(win.buffer[-(max_y-3):]):
            stdscr.addstr(idx+1, 2, line[:max_x-4])
        if win.logged_in:
            stdscr.addstr(max_y-2, 2, (f"{get_path(win)}$ " + win.input_str)[:max_x-4])
        else:
            if win.login_state == "password":
                stdscr.addstr(max_y-2, 2, ("Password: " + "*"*len(win.input_str))[:max_x-4])
            else:
                stdscr.addstr(max_y-2, 2, ("Username: " + win.input_str)[:max_x-4])
        status = f"Win {current_window+1}/{len(windows)}"
        stdscr.addstr(0, max_x-len(status)-2, status)
        stdscr.refresh()

    def get_path(win):
        return "/" + "/".join(d.name for d in win.path[1:])

    def autocomplete(fragment, win):
        opts = list(win.cwd.contents.keys()) + [
            "help", "clear", "exit", "ls", "cd", "mkdir", "touch", "cat", "whoami", "logout", "save", "load", "ps", "kill", "top", "pkg", "ping", "ifconfig", "curl", "mount", "umount", "chmod", "chown", "sudo"
        ]
        return [o for o in opts if o.startswith(fragment)]

    draw()
    while running:
        key = stdscr.getch()
        win = windows[current_window]
        if win.help_active:
            if key == curses.KEY_UP:
                if win.help_scroll_offset > 0:
                    win.help_scroll_offset -= 1
            elif key == curses.KEY_DOWN:
                help_lines = 25  # number of help lines
                if win.help_scroll_offset < help_lines - (max_y - 3):
                    win.help_scroll_offset += 1
            else:
                win.help_active = False
                win.help_scroll_offset = 0
            draw()
            continue
        elif key in (curses.KEY_BACKSPACE, 127):
            win.input_str = win.input_str[:-1]
        elif key == 9:
            if win.logged_in:
                frag = win.input_str.split()[-1] if win.input_str.split() else ""
                comps = autocomplete(frag, win)
                if comps:
                    win.input_str = " ".join(win.input_str.split()[:-1] + [comps[0]]) if win.input_str.split() else comps[0]
        elif key == curses.KEY_UP:
            if win.logged_in and win.command_history:
                if win.history_index == -1:
                    win.history_index = len(win.command_history) - 1
                elif win.history_index > 0:
                    win.history_index -= 1
                if win.history_index >= 0:
                    win.input_str = win.command_history[win.history_index]
        elif key == curses.KEY_DOWN:
            if win.logged_in and win.command_history and win.history_index != -1:
                if win.history_index < len(win.command_history) - 1:
                    win.history_index += 1
                    win.input_str = win.command_history[win.history_index]
                else:
                    win.history_index = -1
                    win.input_str = ""
        elif key == 10:
            if not win.logged_in:
                if win.login_state == "username":
                    win.temp_username = win.input_str.strip()
                    if win.temp_username in users:
                        win.login_state = "password"
                        win.buffer.append("Password:")
                    else:
                        win.buffer.append("Invalid username. Username:")
                    win.input_str = ""
                elif win.login_state == "password":
                    pw = win.input_str.strip()
                    u = users[win.temp_username]
                    if u["password"] is None or u["password"] == hashlib.sha256(pw.encode()).hexdigest():
                        win.current_user = win.temp_username
                        win.logged_in = True
                        win.login_state = "logged_in"
                        win.cwd = get_home_dir(win.current_user)
                        win.path = [root, root.get("home"), root.get("home").get(win.current_user)]
                        win.buffer.append(f"Login successful. Welcome, {win.current_user}!")
                    else:
                        win.buffer.append("Invalid password. Username:")
                        win.login_state = "username"
                    win.input_str = ""
                draw()
                continue
            win.buffer.append(f"{get_path(win)}$ " + win.input_str)
            if win.input_str.strip():
                win.command_history.append(win.input_str.strip())
                if len(win.command_history) > 100:
                    win.command_history = win.command_history[-100:]
            win.history_index = -1
            cmd = win.input_str.strip()
            parts = cmd.split()
            if not parts:
                win.input_str = ""
                draw()
                continue
            c = parts[0]
            args = parts[1:]
            if c == "sudo":
                if not is_root(win.current_user) and win.current_user != "admin":
                    win.buffer.append("sudo: user not in sudoers file")
                elif not args:
                    win.buffer.append("sudo: missing command")
                else:
                    win.sudo_mode = True
                    sudo_cmd = " ".join(args)
                    result = handle_command(sudo_cmd, win)
                    win.sudo_mode = False
                    win.buffer.extend(result)
                win.input_str = ""
                draw()
                continue
            if c == "help":
                win.help_active = True
                win.help_scroll_offset = 0
                draw()
                continue
            result = handle_command(cmd, win)
            win.buffer.extend(result)
            win.input_str = ""
        elif key == curses.KEY_F2:
            windows.append(TerminalWindow(len(windows)))
            current_window = len(windows) - 1
        elif key == curses.KEY_F1:
            current_window = (current_window - 1) % len(windows)
        elif key == curses.KEY_F3:
            current_window = (current_window + 1) % len(windows)
        elif key == curses.KEY_F5:
            network_up = not network_up
            win.buffer.append(f"Network: {'UP' if network_up else 'DOWN'}")
        elif 0 <= key <= 255:
            win.input_str += chr(key)
        draw()

def resolve_obj(obj, cwd):
    # Resolves symlinks recursively, returns the final object
    seen = set()
    while isinstance(obj, Symlink):
        if obj.target.startswith("/"):
            # Absolute path
            parts = obj.target.strip("/").split("/")
            d = root
        else:
            # Relative path
            d = cwd
            parts = obj.target.split("/")
        for p in parts:
            if isinstance(d, Directory):
                d = d.get(p)
            else:
                d = None
            if d is None:
                break
        obj = d
        if id(obj) in seen:
            break  # Prevent infinite loop
        seen.add(id(obj))
    if isinstance(obj, Hardlink):
        return obj.target_file
    return obj

def handle_command(cmd, win):
    global root, home
    parts = cmd.strip().split()
    if not parts:
        return []
    c = parts[0]
    args = parts[1:]
    output = []
    if c == "help":
        output.append("Available: help, clear, exit, ls, cd, mkdir, touch, cat, whoami, logout, save, load, ps, kill, top, pkg, ping, ifconfig, curl, mount, umount, chmod, chown, sudo")
    elif c == "clear":
        win.buffer = []
    elif c == "exit":
        output.append("Use Ctrl+C to quit TerminalOS.")
    elif c == "ls":
        items = win.cwd.list()
        if not items:
            output.append("")
        else:
            # Show type and permissions
            def permstr(obj):
                if isinstance(obj, Directory):
                    t = 'd'
                elif isinstance(obj, Symlink):
                    t = 'l'
                elif isinstance(obj, Hardlink):
                    t = 'h'
                else:
                    t = '-'
                m = obj.mode if hasattr(obj, 'mode') else 0o777
                perms = ''.join([('r' if m & (1<<8-i*3) else '-') + ('w' if m & (1<<7-i*3) else '-') + ('x' if m & (1<<6-i*3) else '-') for i in range(3)])
                return t + perms
            lines = []
            for k in sorted(items):
                obj = win.cwd.contents[k]
                pstr = permstr(obj)
                if isinstance(obj, Symlink):
                    lines.append(f"{pstr} {obj.owner:8} {k} -> {obj.target}")
                else:
                    lines.append(f"{pstr} {obj.owner:8} {k}")
            output.extend(lines)
    elif c == "cd":
        if not args:
            return []
        if args[0] == "..":
            if len(win.path) > 1:
                win.path.pop()
                win.cwd = win.path[-1]
        elif args[0] in win.cwd.contents and isinstance(win.cwd.contents[args[0]], Directory):
            win.cwd = win.cwd.contents[args[0]]
            win.path.append(win.cwd)
        else:
            output.append(f"cd: no such directory: {args[0]}")
    elif c == "mkdir":
        if not args:
            output.append("mkdir: missing operand")
        elif args[0] in win.cwd.contents:
            output.append(f"mkdir: cannot create directory '{args[0]}': File exists")
        else:
            d = Directory(args[0], win.current_user if win.current_user else "guest")
            win.cwd.add(d)
    elif c == "touch":
        if not args:
            output.append("touch: missing file operand")
        elif args[0] in win.cwd.contents:
            obj = win.cwd.contents[args[0]]
            if isinstance(obj, File):
                obj.size = len(obj.content)
        else:
            f = File(args[0], "", win.current_user if win.current_user else "guest")
            win.cwd.add(f)
    elif c == "cat":
        if not args:
            output.append("cat: missing file operand")
        elif args[0] in win.cwd.contents:
            obj = resolve_obj(win.cwd.contents[args[0]], win.cwd)
            if isinstance(obj, File):
                output.extend(obj.content.splitlines() or [""])
            else:
                output.append(f"cat: {args[0]}: Not a file")
        else:
            output.append(f"cat: {args[0]}: No such file")
    elif c == "whoami":
        output.append(win.current_user)
    elif c == "logout":
        win.logged_in = False
        win.current_user = None
        win.login_state = "username"
        output.append("Logged out. Username:")
    elif c == "save":
        try:
            save_filesystem(root)
            save_users(users)
            output.append("System state saved.")
        except Exception as e:
            output.append(f"Save failed: {e}")
    elif c == "load":
        try:
            r = load_filesystem()
            if r:
                root = r
                home = root.get("home")
                win.cwd = get_home_dir(win.current_user) if win.current_user else root
                win.path = [root, root.get("home"), root.get("home").get(win.current_user)] if win.current_user else [root]
                output.append("Filesystem loaded.")
            u = load_users()
            if u:
                users.clear()
                users.update(u)
                output.append("User data loaded.")
        except Exception as e:
            output.append(f"Load failed: {e}")
    elif c == "ps":
        procs = procman.get_list()
        output.append("  PID USER     CPU  MEM COMMAND")
        for p in sorted(procs, key=lambda x: x.pid):
            output.append(f"{p.pid:5} {p.owner:8} {p.cpu:4.1f} {p.mem:4.1f} {p.name}")
    elif c == "kill":
        if not args:
            output.append("kill: missing process ID")
        else:
            try:
                pid = int(args[0])
                if procman.kill(pid):
                    output.append(f"Process {pid} killed")
                else:
                    output.append(f"kill: ({pid}) - No such process")
            except Exception:
                output.append("kill: invalid process ID")
    elif c == "top":
        procs = procman.get_list()
        output.append("  PID USER     CPU  MEM COMMAND")
        for p in sorted(procs, key=lambda x: -x.cpu)[:10]:
            output.append(f"{p.pid:5} {p.owner:8} {p.cpu:4.1f} {p.mem:4.1f} {p.name}")
    elif c == "pkg":
        if not args:
            output.append("Usage: pkg [install|list|available] [package]")
        elif args[0] == "install":
            if len(args) > 1:
                ok, ver = pkgman.install(args[1])
                if ok:
                    output.append(f"Installed {args[1]} {ver}")
                else:
                    output.append(f"pkg: package '{args[1]}' not found")
            else:
                output.append("pkg install: missing package name")
        elif args[0] == "list":
            inst = pkgman.list_installed()
            output.append("Installed packages:")
            for k, v in inst.items():
                output.append(f"  {k} {v}")
        elif args[0] == "available":
            avail = pkgman.list_available()
            output.append("Available packages:")
            for k, v in avail.items():
                if not pkgman.is_installed(k):
                    output.append(f"  {k} {v}")
    elif c == "ping":
        if not args:
            output.append("ping: missing destination")
        elif not network_up:
            output.append(f"ping: {args[0]}: Network is unreachable")
        else:
            target = args[0]
            output.append(f"PING {target} (192.168.1.{random.randint(1,254)}) 56(84) bytes of data.")
            output.append(f"64 bytes from {target}: icmp_seq=1 ttl=64 time={random.randint(1,50)}ms")
            output.append(f"64 bytes from {target}: icmp_seq=2 ttl=64 time={random.randint(1,50)}ms")
            output.append("--- ping statistics ---")
            output.append("2 packets transmitted, 2 received, 0% packet loss")
    elif c == "ifconfig":
        if network_up:
            output.append("eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500")
            output.append(f"        inet {ip_address}  netmask 255.255.255.0  broadcast 192.168.1.255")
            output.append("        inet6 fe80::a00:27ff:fe4e:66a1  prefixlen 64  scopeid 0x20<link>")
            output.append("        ether 08:00:27:4e:66:a1  txqueuelen 1000  (Ethernet)")
            output.append("        RX packets 1234  bytes 567890 (554.5 KiB)")
            output.append("        TX packets 987  bytes 123456 (120.5 KiB)")
        else:
            output.append("Network interface down")
    elif c == "curl":
        if not args:
            output.append("curl: missing URL")
        elif not network_up:
            output.append("curl: Network is unreachable")
        else:
            url = args[0]
            output.append(f"Connecting to {url}...")
            output.append("HTTP/1.1 200 OK")
            output.append("Content-Type: text/html")
            output.append("")
            output.append("<html><body><h1>Fake webpage content</h1></body></html>")
    elif c == "mount":
        if not args:
            output.append("Mounted filesystems:")
            for mount_point, info in mountman.mounts.items():
                output.append(f"{info['device']} on {mount_point} type {info['type']}")
        else:
            device = args[0]
            success, mount_point = mountman.mount_device(device)
            if success:
                output.append(f"Mounted {device} at {mount_point}")
            else:
                output.append(f"mount: cannot mount {device}")
    elif c == "umount":
        if not args:
            output.append("umount: missing device")
        else:
            device = args[0]
            if mountman.unmount_device(device):
                output.append(f"Unmounted {device}")
            else:
                output.append(f"umount: {device} not mounted")
    elif c == "chmod":
        if len(args) >= 2:
            mode = args[0]
            filename = args[1]
            if filename in win.cwd.contents:
                obj = resolve_obj(win.cwd.contents[filename], win.cwd)
                try:
                    if re.match(r"^[0-7]{3,4}$", mode):
                        obj.mode = int(mode, 8)
                    else:
                        obj.mode = parse_symbolic_chmod(mode, getattr(obj, 'mode', 0o644))
                    output.append(f"Changed permissions of '{filename}' to {oct(obj.mode)[2:]}")
                except Exception:
                    output.append(f"chmod: invalid mode: {mode}")
            else:
                output.append(f"chmod: cannot access '{filename}': No such file or directory")
        else:
            output.append("chmod: missing operand")
    elif c == "chown":
        if len(args) >= 2:
            owner = args[0]
            filename = args[1]
            if filename in win.cwd.contents:
                obj = resolve_obj(win.cwd.contents[filename], win.cwd)
                obj.owner = owner
                output.append(f"Changed ownership of '{filename}' to {owner}")
            else:
                output.append(f"chown: cannot access '{filename}': No such file or directory")
        else:
            output.append("chown: missing operand")
    elif c == "df":
        # Show disk usage for each mount (simulate only root and home for now)
        mounts = [("/", root), ("/home", root.get("home"))]
        output.append("Filesystem   Size     Used    Avail   Use%  Mounted on")
        for mnt, d in mounts:
            if d and d.max_size:
                used = d.get_size()
                size = d.max_size
                avail = size - used
                usep = int(used/size*100) if size else 0
                output.append(f"fakefs      {size//1024}K   {used//1024}K   {avail//1024}K   {usep}%   {mnt}")
    elif c == "du":
        # Show disk usage for current dir or given dir
        def du_dir(d, path, seen=None):
            if seen is None:
                seen = set()
            size = d.get_size(seen)
            lines = [f"{size} {path}"]
            for obj in d.contents.values():
                if isinstance(obj, Directory):
                    lines += du_dir(obj, os.path.join(path, obj.name), seen)
            return lines
        target = win.cwd
        path = "/" + "/".join(d.name for d in win.path[1:])
        if args and args[0] in win.cwd.contents and isinstance(win.cwd.contents[args[0]], Directory):
            target = win.cwd.contents[args[0]]
            path = os.path.join(path, args[0])
        output += du_dir(target, path)
    elif c == "ln":
        if not args or len(args) < 2:
            output.append("Usage: ln [-s] target linkname")
        elif args[0] == "-s":
            # Symlink
            if len(args) < 3:
                output.append("Usage: ln -s target linkname")
            else:
                target, linkname = args[1], args[2]
                if linkname in win.cwd.contents:
                    output.append(f"ln: failed to create symlink '{linkname}': File exists")
                else:
                    win.cwd.add(Symlink(linkname, target, win.current_user))
        else:
            # Hardlink
            target, linkname = args[0], args[1]
            if linkname in win.cwd.contents:
                output.append(f"ln: failed to create hard link '{linkname}': File exists")
            elif target not in win.cwd.contents or not isinstance(win.cwd.contents[target], File):
                output.append(f"ln: failed to access '{target}': No such file")
            else:
                win.cwd.add(Hardlink(linkname, win.cwd.contents[target], win.current_user))
    else:
        output.append(f"Unknown command: {cmd}")
    return output

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\nShutting down TerminalOS...") 
