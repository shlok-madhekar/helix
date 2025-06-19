import curses
import time
import hashlib

class File:
    def __init__(self, name, content=""):
        self.name = name
        self.content = content
        self.size = len(content)

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

users = {
    "guest": {"password": None, "home": "/home/guest"},
    "admin": {"password": hashlib.sha256(b"admin123").hexdigest(), "home": "/home/admin"}
}

root = Directory("/")
home = Directory("home")
root.add(home)
home.add(Directory("guest"))
home.add(Directory("admin"))
root.add(Directory("etc"))
root.add(Directory("var"))

cwd = root
path = [root]
current_user = None
logged_in = False

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
    curses.curs_set(1)
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()
    buffer = ["TerminalOS - Login required.", "Username:"]
    input_str = ""
    global cwd, path, current_user, logged_in
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
                buffer.append("Available: help, clear, exit, ls, cd, mkdir, touch, cat, whoami, logout")
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