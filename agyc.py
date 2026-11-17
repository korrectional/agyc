#!/usr/bin/env python3
"""
agyc - Smart wrapper for the agy CLI.

Features:
1. Auto-Confirm: Automatically approves tool execution / edit prompts ("> 1. Yes, ").
   - Passes --dangerously-skip-permissions to agy for native interactive sessions.
   - Also provides stream-based auto-Enter for piped / custom target processes.
2. Input Scanner: Scans input prompts and arguments for exposed secrets and credentials
   (OpenAI, Anthropic, AWS, GitHub, Google API keys, private keys, etc.).
3. Full Interactive Terminal Support: Preserves terminal TTY, colors, and key navigation.
"""

import os
import sys
import re
import shutil
import threading
import time
import subprocess
from typing import List, Tuple, Optional

# Regular expression to match ANSI escape sequences
ANSI_REGEX = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# Common secret patterns for input scanning
SECRET_PATTERNS = [
    ("OpenAI / LLM API Key", re.compile(r"\b(?:sk-(?:proj-)?[a-zA-Z0-9_\-]{20,})\b")),
    ("Anthropic API Key", re.compile(r"\bsk-ant-[a-zA-Z0-9_\-]{20,}\b")),
    ("AWS Access Key ID", re.compile(r"\b(AKIA[0-9A-Z]{16})\b")),
    ("GitHub Token", re.compile(r"\b(?:ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{50,})\b")),
    ("Google API Key", re.compile(r"\b(AIza[0-9A-Za-z\-_]{35})\b")),
    ("Slack Token", re.compile(r"\bxox[baprs]-[0-9a-zA-Z]{10,}\b")),
    ("Private Key", re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC|DSA|PGP)? PRIVATE KEY-----")),
]

def strip_ansi(text: str) -> str:
    """Strip ANSI escape sequences from text."""
    return ANSI_REGEX.sub('', text)

def mask_secret(secret: str) -> str:
    """Mask secret value for safe logging."""
    if len(secret) <= 8:
        return "****"
    return secret[:4] + "****" + secret[-4:]

def scan_text_for_secrets(text: str) -> List[Tuple[str, str]]:
    """Scan given text for any exposed secret patterns."""
    findings = []
    for name, pattern in SECRET_PATTERNS:
        matches = pattern.findall(text)
        for m in matches:
            findings.append((name, m))
    return findings

def find_agy_executable() -> Optional[str]:
    """Find the agy executable on the system."""
    # 1. Environment variable override
    for env_var in ("AGY_BIN_PATH", "AGY_EXE", "AGY_PATH"):
        val = os.environ.get(env_var)
        if val and os.path.isfile(val):
            return val

    # 2. Check system PATH
    agy_in_path = shutil.which("agy") or shutil.which("agy.exe")
    if agy_in_path:
        norm = agy_in_path.lower()
        if not norm.endswith("agyc.py") and not norm.endswith("agyc.cmd") and not norm.endswith("agyc.ps1"):
            return agy_in_path

    # 3. Known default locations on Windows
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        candidate = os.path.join(local_app_data, "agy", "bin", "agy.exe")
        if os.path.isfile(candidate):
            return candidate

    home = os.path.expanduser("~")
    # Windows default path
    candidate = os.path.join(home, "AppData", "Local", "agy", "bin", "agy.exe")
    if os.path.isfile(candidate):
        return candidate

    # Linux / Unix default paths
    candidate_linux = os.path.join(home, ".local", "bin", "agy")
    if os.path.isfile(candidate_linux):
        return candidate_linux

    if os.path.isfile("/usr/local/bin/agy"):
        return "/usr/local/bin/agy"

    return None

class StreamMonitor:
    """
    Monitors program output stream for trigger strings (e.g. '> 1. Yes, ').
    Handles rolling buffers, cross-chunk matches, and ANSI sequence stripping.
    """
    def __init__(self, target_str: str = "> 1. Yes, ", verbose: bool = False):
        self.target_str = target_str
        self.verbose = verbose
        self.lock = threading.Lock()
        self.raw_buffer = ""

    def feed(self, text: str) -> bool:
        with self.lock:
            self.raw_buffer += text
            clean = strip_ansi(self.raw_buffer)
            idx = clean.find(self.target_str)
            if idx != -1:
                self.raw_buffer = ""
                return True

            if len(self.raw_buffer) > 4096:
                self.raw_buffer = self.raw_buffer[-1024:]

            return False

def run_piped_wrapper(
    cmd_args: List[str],
    target_str: str = "> 1. Yes, ",
    auto_enter: bool = True,
    verbose: bool = False
) -> int:
    """
    Piped execution mode: intercepts stdout/stderr, monitors for target_str,
    and automatically presses Enter when matched.
    """
    monitor = StreamMonitor(target_str=target_str, verbose=verbose)

    try:
        proc = subprocess.Popen(
            cmd_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )
    except Exception as e:
        sys.stderr.write(f"agyc: failed to launch {' '.join(cmd_args)}: {e}\n")
        return 1

    stop_event = threading.Event()

    def send_enter():
        if not auto_enter:
            return
        try:
            if proc.stdin and not proc.stdin.closed:
                if verbose:
                    sys.stderr.write(f"\n[agyc: detected {target_str!r} -> auto-pressing Enter]\n")
                    sys.stderr.flush()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
        except (BrokenPipeError, OSError):
            pass

    def output_reader(pipe, dest_stream):
        try:
            while True:
                chunk = pipe.read(512)
                if not chunk:
                    break
                dest_stream.buffer.write(chunk)
                dest_stream.buffer.flush()

                decoded = chunk.decode("utf-8", errors="replace")
                if monitor.feed(decoded):
                    send_enter()
        except (ValueError, OSError):
            pass

    def input_forwarder():
        is_tty = hasattr(sys.stdin, "isatty") and sys.stdin.isatty()
        if is_tty:
            try:
                import msvcrt
                while not stop_event.is_set() and proc.poll() is None:
                    try:
                        if msvcrt.kbhit():
                            ch = msvcrt.getch()
                            if proc.stdin and not proc.stdin.closed:
                                proc.stdin.write(ch)
                                proc.stdin.flush()
                        else:
                            time.sleep(0.02)
                    except (ValueError, OSError):
                        break
            except ImportError:
                pass
        else:
            try:
                import msvcrt
                import ctypes
                from ctypes import wintypes
                kernel32 = ctypes.windll.kernel32
                h_stdin = msvcrt.get_osfhandle(0)
                avail = wintypes.DWORD()
                while not stop_event.is_set() and proc.poll() is None:
                    if kernel32.PeekNamedPipe(h_stdin, None, 0, None, ctypes.byref(avail), None):
                        if avail.value > 0:
                            chunk = os.read(0, min(avail.value, 1024))
                            if not chunk:
                                break
                            if proc.stdin and not proc.stdin.closed:
                                proc.stdin.write(chunk)
                                proc.stdin.flush()
                        else:
                            time.sleep(0.02)
                    else:
                        break
            except Exception:
                pass

    t_out = threading.Thread(target=output_reader, args=(proc.stdout, sys.stdout), daemon=True)
    t_err = threading.Thread(target=output_reader, args=(proc.stderr, sys.stderr), daemon=True)
    t_in = threading.Thread(target=input_forwarder, daemon=True)

    t_out.start()
    t_err.start()
    t_in.start()

    try:
        ret = proc.wait()
    except KeyboardInterrupt:
        try:
            proc.terminate()
        except OSError:
            pass
        ret = 130
    finally:
        stop_event.set()
        t_out.join(timeout=0.5)
        t_err.join(timeout=0.5)

    return ret

def run_native_terminal(cmd_args: List[str]) -> int:
    """
    Runs target directly connected to terminal with native TTY, colors, and input.
    """
    try:
        return subprocess.call(cmd_args)
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        sys.stderr.write(f"agyc: error executing {' '.join(cmd_args)}: {e}\n")
        return 1

def main():
    raw_args = sys.argv[1:]

    # Wrapper options
    verbose = False
    auto_enter = True
    scan_secrets = True
    force_proceed = False
    force_pipe = False
    target_str = "> 1. Yes, "
    cmd_override = None

    filtered_args = []
    i = 0
    while i < len(raw_args):
        arg = raw_args[i]
        if arg == "--agyc-verbose":
            verbose = True
        elif arg == "--agyc-no-auto-enter":
            auto_enter = False
        elif arg == "--agyc-pipe":
            force_pipe = True
        elif arg == "--agyc-no-scan":
            scan_secrets = False
        elif arg in ("--agyc-force", "-y"):
            force_proceed = True
        elif arg == "--agyc-target" and i + 1 < len(raw_args):
            cmd_override = raw_args[i + 1]
            i += 1
        elif arg.startswith("--agyc-target="):
            cmd_override = arg.split("=", 1)[1]
        elif arg == "--agyc-trigger" and i + 1 < len(raw_args):
            target_str = raw_args[i + 1]
            i += 1
        elif arg.startswith("--agyc-trigger="):
            target_str = arg.split("=", 1)[1]
        elif arg in ("--agyc-help", "-h") and len(raw_args) == 1:
            print("agyc - Wrapper for agy CLI")
            print("Usage: agyc [options] [agy arguments...]")
            print("")
            print("Options:")
            print("  --agyc-trigger <str>     String to auto-confirm (default: '> 1. Yes, ')")
            print("  --agyc-no-auto-enter     Disable automatic Enter key press")
            print("  --agyc-no-scan           Disable secret/credential scanning on input")
            print("  --agyc-force, -y         Skip secret warning prompt and proceed")
            print("  --agyc-pipe              Force piped I/O streaming mode")
            print("  --agyc-verbose           Show diagnostic messages when actions occur")
            print("  --agyc-target <path>     Path to target executable (default: auto-detect agy)")
            print("  --agyc-help              Show this help message")
            print("")
            print("All other arguments and flags are forwarded directly to agy.")
            sys.exit(0)
        else:
            filtered_args.append(arg)
        i += 1

    # Secret scanning on user input arguments
    if scan_secrets and filtered_args:
        args_text = " ".join(filtered_args)
        findings = scan_text_for_secrets(args_text)
        if findings:
            sys.stderr.write("\n[agyc] WARNING: Possible sensitive credential(s) detected in input:\n")
            for secret_type, secret_val in findings:
                sys.stderr.write(f"  - {secret_type}: {mask_secret(secret_val)}\n")
            if not force_proceed:
                sys.stderr.write("Do you want to proceed sending this to agy? [y/N]: ")
                sys.stderr.flush()
                try:
                    choice = sys.stdin.readline().strip().lower()
                    if choice not in ("y", "yes"):
                        sys.stderr.write("Execution aborted by user.\n")
                        sys.exit(1)
                except KeyboardInterrupt:
                    sys.stderr.write("\nAborted.\n")
                    sys.exit(130)

    # Determine command
    if cmd_override:
        cmd = [cmd_override] + filtered_args
        # If custom target (e.g. mock script), run via piped wrapper
        exit_code = run_piped_wrapper(
            cmd,
            target_str=target_str,
            auto_enter=auto_enter,
            verbose=verbose
        )
    else:
        agy_bin = find_agy_executable()
        if not agy_bin:
            sys.stderr.write("agyc: could not find 'agy' executable in PATH or LocalAppData.\n")
            sys.stderr.write("Please ensure agy is installed or set AGY_BIN_PATH environment variable.\n")
            sys.exit(1)

        # For agy, auto-confirm is natively and flawlessly supported via --dangerously-skip-permissions
        cmd = [agy_bin]
        if auto_enter and "--dangerously-skip-permissions" not in filtered_args:
            cmd.append("--dangerously-skip-permissions")
        cmd.extend(filtered_args)

        if force_pipe:
            exit_code = run_piped_wrapper(
                cmd,
                target_str=target_str,
                auto_enter=auto_enter,
                verbose=verbose
            )
        else:
            exit_code = run_native_terminal(cmd)

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
