import sys
import time

def main():
    print("Welcome to agy mock CLI")
    time.sleep(0.1)
    
    # Prompt 1
    sys.stdout.write("Agent wants to run: git status\n")
    sys.stdout.write("  Do you want to proceed?\n")
    sys.stdout.write("\x1b[32m> 1. Yes, \x1b[0mrun this command\n")
    sys.stdout.write("  2. No, skip\n")
    sys.stdout.flush()

    line = sys.stdin.readline()
    if line.strip() == "" or line.strip() == "1":
        sys.stdout.write("Confirmed 1! Command executed.\n\n")
        sys.stdout.flush()
    else:
        sys.stdout.write(f"Rejected with input: {line!r}\n")
        sys.stdout.flush()
        sys.exit(1)

    time.sleep(0.1)

    # Prompt 2
    sys.stdout.write("Agent wants to edit: file.txt\n")
    sys.stdout.write("> 1. Yes, allow edit\n")
    sys.stdout.write("  2. No\n")
    sys.stdout.flush()

    line = sys.stdin.readline()
    if line.strip() == "" or line.strip() == "1":
        sys.stdout.write("Confirmed 2! File edited.\nDone!\n")
        sys.stdout.flush()
    else:
        sys.stdout.write(f"Rejected 2 with input: {line!r}\n")
        sys.stdout.flush()
        sys.exit(1)

if __name__ == "__main__":
    main()
