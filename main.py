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

    draw()
    while running:
        key = stdscr.getch()
        win = windows[current_window]
        if key in (curses.KEY_BACKSPACE, 127):
            win.input_str = win.input_str[:-1]
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
            cmd = win.input_str.strip()
            parts = cmd.split()
            if not parts:
                win.input_str = ""
                draw()
                continue
            c = parts[0]
            args = parts[1:]
            if c == "help":
                win.buffer.append("Available: help, clear, exit, ls, cd, mkdir, touch, cat, whoami, logout, save, load, ps, kill, top, pkg, ping, ifconfig, curl, mount, umount")
            elif c == "clear":
                win.buffer = []
            elif c == "exit":
                win.buffer.append("Exiting TerminalOS...")
                draw()
                time.sleep(1)
                running = False
                break
            elif c == "ls":
                items = win.cwd.list()
                if not items:
                    win.buffer.append("")
                else:
                    win.buffer.append("  ".join(sorted(items)))
            elif c == "cd":
                if not args:
                    win.input_str = ""
                    draw()
                    continue
                if args[0] == "..":
                    if len(win.path) > 1:
                        win.path.pop()
                        win.cwd = win.path[-1]
                elif args[0] in win.cwd.contents and isinstance(win.cwd.contents[args[0]], Directory):
                    win.cwd = win.cwd.contents[args[0]]
                    win.path.append(win.cwd)
                else:
                    win.buffer.append(f"cd: no such directory: {args[0]}")
            elif c == "mkdir":
                if not args:
                    win.buffer.append("mkdir: missing operand")
                elif args[0] in win.cwd.contents:
                    win.buffer.append(f"mkdir: cannot create directory '{args[0]}': File exists")
                else:
                    win.cwd.add(Directory(args[0]))
            elif c == "touch":
                if not args:
                    win.buffer.append("touch: missing file operand")
                elif args[0] in win.cwd.contents:
                    obj = win.cwd.contents[args[0]]
                    if isinstance(obj, File):
                        obj.size = len(obj.content)
                else:
                    win.cwd.add(File(args[0], ""))
            elif c == "cat":
                if not args:
                    win.buffer.append("cat: missing file operand")
                elif args[0] in win.cwd.contents and isinstance(win.cwd.contents[args[0]], File):
                    win.buffer.extend(win.cwd.contents[args[0]].content.splitlines() or [""])
                else:
                    win.buffer.append(f"cat: {args[0]}: No such file")
            elif c == "whoami":
                win.buffer.append(win.current_user)
            elif c == "logout":
                win.logged_in = False
                win.current_user = None
                win.login_state = "username"
                win.buffer.append("Logged out. Username:")
            elif c == "save":
                try:
                    save_filesystem(root)
                    save_users(users)
                    win.buffer.append("System state saved.")
                except Exception as e:
                    win.buffer.append(f"Save failed: {e}")
            elif c == "load":
                try:
                    r = load_filesystem()
                    if r:
                        root = r
                        home = root.get("home")
                        win.cwd = get_home_dir(win.current_user) if win.current_user else root
                        win.path = [root, root.get("home"), root.get("home").get(win.current_user)] if win.current_user else [root]
                        win.buffer.append("Filesystem loaded.")
                    u = load_users()
                    if u:
                        users.clear()
                        users.update(u)
                        win.buffer.append("User data loaded.")
                except Exception as e:
                    win.buffer.append(f"Load failed: {e}")
            elif c == "ps":
                procs = procman.get_list()
                win.buffer.append("  PID USER     CPU  MEM COMMAND")
                for p in sorted(procs, key=lambda x: x.pid):
                    win.buffer.append(f"{p.pid:5} {p.owner:8} {p.cpu:4.1f} {p.mem:4.1f} {p.name}")
            elif c == "kill":
                if not args:
                    win.buffer.append("kill: missing process ID")
                else:
                    try:
                        pid = int(args[0])
                        if procman.kill(pid):
                            win.buffer.append(f"Process {pid} killed")
                        else:
                            win.buffer.append(f"kill: ({pid}) - No such process")
                    except Exception:
                        win.buffer.append("kill: invalid process ID")
            elif c == "top":
                procs = procman.get_list()
                win.buffer.append("  PID USER     CPU  MEM COMMAND")
                for p in sorted(procs, key=lambda x: -x.cpu)[:10]:
                    win.buffer.append(f"{p.pid:5} {p.owner:8} {p.cpu:4.1f} {p.mem:4.1f} {p.name}")
            elif c == "pkg":
                if not args:
                    win.buffer.append("Usage: pkg [install|list|available] [package]")
                elif args[0] == "install":
                    if len(args) > 1:
                        ok, ver = pkgman.install(args[1])
                        if ok:
                            win.buffer.append(f"Installed {args[1]} {ver}")
                        else:
                            win.buffer.append(f"pkg: package '{args[1]}' not found")
                    else:
                        win.buffer.append("pkg install: missing package name")
                elif args[0] == "list":
                    inst = pkgman.list_installed()
                    win.buffer.append("Installed packages:")
                    for k, v in inst.items():
                        win.buffer.append(f"  {k} {v}")
                elif args[0] == "available":
                    avail = pkgman.list_available()
                    win.buffer.append("Available packages:")
                    for k, v in avail.items():
                        if not pkgman.is_installed(k):
                            win.buffer.append(f"  {k} {v}")
            elif c == "ping":
                if not args:
                    win.buffer.append("ping: missing destination")
                elif not network_up:
                    win.buffer.append(f"ping: {args[0]}: Network is unreachable")
                else:
                    target = args[0]
                    win.buffer.append(f"PING {target} (192.168.1.{random.randint(1,254)}) 56(84) bytes of data.")
                    win.buffer.append(f"64 bytes from {target}: icmp_seq=1 ttl=64 time={random.randint(1,50)}ms")
                    win.buffer.append(f"64 bytes from {target}: icmp_seq=2 ttl=64 time={random.randint(1,50)}ms")
                    win.buffer.append("--- ping statistics ---")
                    win.buffer.append("2 packets transmitted, 2 received, 0% packet loss")
            elif c == "ifconfig":
                if network_up:
                    win.buffer.append("eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500")
                    win.buffer.append(f"        inet {ip_address}  netmask 255.255.255.0  broadcast 192.168.1.255")
                    win.buffer.append("        inet6 fe80::a00:27ff:fe4e:66a1  prefixlen 64  scopeid 0x20<link>")
                    win.buffer.append("        ether 08:00:27:4e:66:a1  txqueuelen 1000  (Ethernet)")
                    win.buffer.append("        RX packets 1234  bytes 567890 (554.5 KiB)")
                    win.buffer.append("        TX packets 987  bytes 123456 (120.5 KiB)")
                else:
                    win.buffer.append("Network interface down")
            elif c == "curl":
                if not args:
                    win.buffer.append("curl: missing URL")
                elif not network_up:
                    win.buffer.append("curl: Network is unreachable")
                else:
                    url = args[0]
                    win.buffer.append(f"Connecting to {url}...")
                    win.buffer.append("HTTP/1.1 200 OK")
                    win.buffer.append("Content-Type: text/html")
                    win.buffer.append("")
                    win.buffer.append("<html><body><h1>Fake webpage content</h1></body></html>")
            elif c == "mount":
                if not args:
                    win.buffer.append("Mounted filesystems:")
                    for mount_point, info in mountman.mounts.items():
                        win.buffer.append(f"{info['device']} on {mount_point} type {info['type']}")
                else:
                    device = args[0]
                    success, mount_point = mountman.mount_device(device)
                    if success:
                        win.buffer.append(f"Mounted {device} at {mount_point}")
                    else:
                        win.buffer.append(f"mount: cannot mount {device}")
            elif c == "umount":
                if not args:
                    win.buffer.append("umount: missing device")
                else:
                    device = args[0]
                    if mountman.unmount_device(device):
                        win.buffer.append(f"Unmounted {device}")
                    else:
                        win.buffer.append(f"umount: {device} not mounted")
            else:
                win.buffer.append(f"Unknown command: {cmd}")
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

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\nShutting down TerminalOS...") 