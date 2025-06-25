# TerminalOS (Helix)

TerminalOS is a Python-based simulated operating system that runs in your terminal using a curses-based UI. It provides a fun, interactive, and educational environment to explore OS concepts, file systems, process management, and more. all within a single Python script.

## What is TerminalOS?

TerminalOS is a terminal emulator and mock operating system. It simulates a multi-user, multi-window terminal environment with a virtual file system, process manager, package manager, and various Unix-like commands. It's perfect for learning, experimenting, or just having fun with a retro terminal experience.

## How it Works

- **Curses UI**: Uses the `curses` library to create a multi-window terminal interface.
- **Virtual File System**: Simulates files, directories, symlinks, and hardlinks, with support for permissions and ownership.
- **User Management**: Supports multiple users, login/logout, and sudo mode.
- **Process Management**: Simulates processes, allows listing and killing processes.
- **Package Management**: Simulates installing, listing, and viewing available packages.
- **Networking**: Simulates network commands like `ping`, `ifconfig`, and `curl`.
- **Persistence**: Save and load the state of the file system and users.

## Features

- Multi-user login system (with password support)
- Multi-window terminal (switch with F1/F3, open new with F2)
- Virtual file system with directories, files, symlinks, and hardlinks
- File permissions and ownership (`chmod`, `chown`)
- Simulated process management (`ps`, `kill`, `top`)
- Simulated package manager (`pkg install`, `pkg list`, `pkg available`)
- Simulated networking (`ping`, `ifconfig`, `curl`)
- Disk usage commands (`df`, `du`)
- Mount/unmount simulated devices
- Sudo mode for admin commands
- Command history and autocompletion (Tab)
- Help system (`help` command, scroll with Up/Down)

## Installation

1. **Clone the repository or download the files**

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run TerminalOS**

   ```bash
   python main.py
   ```

   > **Note:** TerminalOS requires a terminal that supports curses (most Unix-like systems, including macOS and Linux). On Windows, use WSL or a compatible terminal.

## Default Usernames and Passwords

- **guest**: No password (just press Enter when prompted)
- **admin**: Password is `admin123`

You can log in as either user at the login prompt.

## Fun Commands to Try

Here are some fun and useful commands to explore TerminalOS:

- `help` — Show all available commands and scroll with Up/Down
- `ls` — List files and directories with permissions
- `mkdir testdir` — Create a new directory
- `touch hello.txt` — Create a new file
- `cat hello.txt` — View file contents
- `chmod 777 hello.txt` — Change file permissions
- `chown admin hello.txt` — Change file owner
- `ps` — List running processes
- `kill 1234` — Kill a process by PID
- `pkg install cowsay` — Install a fun package
- `ping google.com` — Simulate a network ping
- `ifconfig` — Show network info
- `curl example.com` — Simulate fetching a webpage
- `mount usb1` / `umount usb1` — Mount/unmount a simulated device
- `df` — Show disk usage
- `du` — Show directory usage
- `ln -s hello.txt link.txt` — Create a symlink
- `ln hello.txt hardlink.txt` — Create a hardlink
- `sudo <command>` — Run a command as admin (if you are admin)
- `logout` — Log out of the current user

## Have Fun!

TerminalOS is designed for experimentation and learning. Try out different commands, explore the virtual OS, and enjoy the retro terminal vibes! 
