#!/usr/bin/env python3


import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

PINK = "\033[1;35m"
CYAN = "\033[1;36m"
WHITE = "\033[1;37m"
RESET = "\033[0m"

IMAGE = next(
    (
        path for path in (
            Path(__file__).resolve().parent / "assets" / "miyuki_clean.png",
            Path("/usr/share/miyufetch/assets/miyuki_clean.png"),
        )
        if path.is_file()
    ),
    Path("/usr/share/miyufetch/assets/miyuki_clean.png"),
)

def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None


def run_command(*args):
    try:
        result = subprocess.run(
            args, capture_output=True, text=True,
            timeout=3, check=False
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def get_os():
    for line in (read_text("/etc/os-release") or "").splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip().strip('"')
    return platform.system()


def get_cpu():
    for line in (read_text("/proc/cpuinfo") or "").splitlines():
        if line.lower().startswith(("model name", "hardware")):
            return line.split(":", 1)[1].strip()
    return platform.processor() or "Unknown"


def get_gpu():
    output = run_command("lspci", "-nn")
    if output:
        names = []
        for line in output.splitlines():
            if not re.search(
                r"VGA compatible controller|3D controller|Display controller",
                line, re.I
            ):
                continue

            if ": " not in line:
                continue

            name = line.split(": ", 1)[1]
            name = re.sub(r"\s*\[[0-9a-fA-F]{4}:[0-9a-fA-F]{4}\]", "", name)
            name = re.sub(r"\s*\(rev [^)]+\)", "", name)
            name = re.sub(
                r"^(Intel Corporation|Advanced Micro Devices, Inc\.|"
                r"AMD/ATI|NVIDIA Corporation)\s*",
                "", name, flags=re.I
            ).strip()

            if name and name not in names:
                names.append(name)

        if names:
            return " / ".join(names)

    # Fallback if lspci is unavailable.
    vendor_names = {
        "0x8086": "Intel GPU",
        "0x10de": "NVIDIA GPU",
        "0x1002": "AMD GPU",
    }
    names = []

    for vendor_file in Path("/sys/class/drm").glob("card[0-9]*/device/vendor"):
        vendor = read_text(vendor_file)
        name = vendor_names.get(vendor, vendor)
        if name and name not in names:
            names.append(name)

    return " / ".join(names) if names else "Unknown"


def get_memory():
    values = {}

    for line in (read_text("/proc/meminfo") or "").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        try:
            values[key] = int(value.strip().split()[0])
        except (ValueError, IndexError):
            pass

    if "MemTotal" in values and "MemAvailable" in values:
        total = values["MemTotal"]
        used = total - values["MemAvailable"]
        return f"{used / 1024:.0f} MiB / {total / 1024:.0f} MiB"

    return "Unknown"


def get_battery():
    batteries = []

    for bat in Path("/sys/class/power_supply").glob("BAT*"):
        capacity = read_text(bat / "capacity")
        status = read_text(bat / "status")

        if capacity:
            entry = f"{capacity}%"
            if status:
                entry += f" ({status.lower()})"
            batteries.append(entry)

    return ", ".join(batteries) if batteries else "Not detected"


def get_display():
    # X11, including many XFCE sessions.
    output = run_command("xrandr", "--current")
    if output:
        for line in output.splitlines():
            if " connected" in line:
                match = re.search(r"\b(\d{3,5}x\d{3,5})\+\d+\+\d+", line)
                if match:
                    return match.group(1)

    # Wayland compositor tools, when available.
    output = run_command("kscreen-doctor", "-o")
    if output:
        match = re.search(r"\b(\d{3,5}x\d{3,5})@", output)
        if match:
            return match.group(1)

    output = run_command("wlr-randr")
    if output:
        for line in output.splitlines():
            match = re.search(r"\b(\d{3,5}x\d{3,5})\b", line)
            if match:
                return match.group(1)

    return "Unknown"


def get_disk():
    try:
        usage = shutil.disk_usage("/")
        used = (usage.total - usage.free) / (1024 ** 3)
        total = usage.total / (1024 ** 3)
        return f"{used:.1f} GiB / {total:.1f} GiB used (/)"
    except OSError:
        return "Unknown"


def get_desktop():
    return (
        os.environ.get("XDG_CURRENT_DESKTOP")
        or os.environ.get("DESKTOP_SESSION")
        or "Unknown"
    )


def get_window_manager():
    # Look for common window manager/compositor processes.
    known = {
        "kwin_wayland": "KWin (Wayland)",
        "kwin_x11": "KWin (X11)",
        "xfwm4": "Xfwm4",
        "Hyprland": "Hyprland",
        "sway": "Sway",
        "openbox": "Openbox",
        "i3": "i3",
        "bspwm": "bspwm",
        "mutter": "Mutter",
        "marco": "Marco",
        "picom": "Picom (compositor)",
    }

    found = set()

    try:
        for process in Path("/proc").iterdir():
            if not process.name.isdigit():
                continue

            name = read_text(process / "comm")
            if name in known:
                found.add(known[name])
    except OSError:
        pass

    # Prefer the main window manager over standalone compositors.
    priority = [
        "KWin (Wayland)", "KWin (X11)", "Hyprland", "Sway",
        "Xfwm4", "Openbox", "i3", "bspwm", "Mutter", "Marco",
    ]

    for name in priority:
        if name in found:
            return name

    return "Unknown"


def get_theme():
    # KDE Plasma theme / color scheme.
    for key in ("ColorScheme",):
        value = run_command(
            "kreadconfig6", "--file", "kdeglobals",
            "--group", "General", "--key", key
        )
        if value:
            return value

    # XFCE GTK theme.
    value = run_command(
        "xfconf-query", "-c", "xsettings",
        "-p", "/Net/ThemeName"
    )
    if value:
        return value

    # GNOME / GTK theme.
    value = run_command(
        "gsettings", "get",
        "org.gnome.desktop.interface", "gtk-theme"
    )
    if value:
        return value.strip("'\"")

    return "Unknown"


def get_icon_theme():
    value = run_command(
        "xfconf-query", "-c", "xsettings",
        "-p", "/Net/IconThemeName"
    )
    if value:
        return value

    value = run_command(
        "kreadconfig6", "--file", "kdeglobals",
        "--group", "Icons", "--key", "Theme"
    )
    if value:
        return value

    value = run_command(
        "gsettings", "get",
        "org.gnome.desktop.interface", "icon-theme"
    )
    if value:
        return value.strip("'\"")

    return "Unknown"


def get_uptime():
    try:
        seconds = int(float(read_text("/proc/uptime").split()[0]))
        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes = seconds // 60

        if days:
            return f"{days}d {hours}h {minutes}m"
        return f"{hours}h {minutes}m"
    except (AttributeError, ValueError, IndexError):
        return "Unknown"


def get_info():
    shell = Path(os.environ.get("SHELL", "")).name or "Unknown"

    if os.environ.get("KITTY_WINDOW_ID"):
        terminal = "Kitty"
    else:
        terminal = (
            os.environ.get("TERM_PROGRAM")
            or os.environ.get("COLORTERM")
            or os.environ.get("TERM")
            or "Unknown"
        )

    return [
        ("OS", get_os()),
        ("Device", platform.node()),
        ("Kernel", platform.release()),
        ("Architecture", platform.machine()),
        ("CPU", get_cpu()),
        ("GPU", get_gpu()),
        ("Memory", get_memory()),
        ("Disk", get_disk()),
        ("Battery", get_battery()),
        ("Display", get_display()),
        ("Desktop", get_desktop()),
        ("Window Manager", get_window_manager()),
        ("Theme", get_theme()),
        ("Icon Theme", get_icon_theme()),
        ("Session", os.environ.get("XDG_SESSION_TYPE", "Unknown")),
        ("Shell", shell),
        ("Terminal", terminal),
        ("Python", platform.python_version()),
        ("Uptime", get_uptime()),
    ]


def show_image(image_cols, image_rows):
    if not IMAGE.is_file():
        return False

    # Kitty: actual PNG with transparency.
    if os.environ.get("KITTY_WINDOW_ID"):
        result = subprocess.run(
            [
                "kitty", "+kitten", "icat",
                "--place", f"{image_cols}x{image_rows}@1x1",
                str(IMAGE),
            ],
            stdout=None,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            return True

    # Black Box and other terminals: Chafa fallback.
    if shutil.which("chafa"):
        result = subprocess.run(
            [
                "chafa", "--format", "symbols",
                "--size", f"{image_cols}x{image_rows}",
                str(IMAGE),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print(result.stdout, end="")
            return True

    return False


def main():
    has_image = IMAGE.is_file()
    if not has_image:
        print("Miyuki image not found; displaying system info only.")

    info = get_info()
    terminal = shutil.get_terminal_size((100, 30))

    # Adapt image and text positions to the terminal width.
    image_cols = max(12, min(30, (terminal.columns - 30) // 2))
    image_rows = 20
    text_col = image_cols + 3 if has_image else 1
    value_width = max(8, terminal.columns - text_col - 13)

    print("\033[2J\033[H", end="", flush=True)

    if has_image:
        show_image(image_cols, image_rows)

    # Move back to the top and write system info beside the image.
    print("\033[H", end="")
    print(f"\033[1;{text_col}H{PINK}MIYUFETCH{RESET}")

    for index, (label, value) in enumerate(info):
        row = index + 2
        print(
            f"\033[{row};{text_col}H"
            f"{PINK}{label:<13}{RESET} "
            f"{WHITE}{str(value)[:value_width]}{RESET}"
        )

    print(f"\033[{len(info) + 3};{text_col}H", end="")

    # Terminal color palette.
    print(f"\033[{len(info) + 4};{text_col}H", end="")
    for color in range(8):
        print(f"\033[{color + 30}m  ", end="")
    print(RESET)


if __name__ == "__main__":
    main()
