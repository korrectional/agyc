"""
Test script for validating user input passthrough and auto-confirmation behavior.
"""
import subprocess
import sys

def test_user_input_passthrough():
    child_code = '''
import sys
sys.stdout.write("Enter your query: ")
sys.stdout.flush()
line = sys.stdin.readline()
sys.stdout.write("Got query: " + repr(line.strip()) + "\\n")
sys.stdout.write("> 1. Yes, execute this query?\\n")
sys.stdout.flush()
choice = sys.stdin.readline()
sys.stdout.write("Got choice: " + repr(choice.strip()) + "\\n")
'''
    # Run agyc with piped input "my search query\n"
    # agyc should forward "my search query\n" to prompt 1
    # and then automatically send Enter for prompt 2 ("> 1. Yes, ")!
    p = subprocess.Popen(
        [sys.executable, "agyc.py", "--agyc-target", sys.executable, "-c", child_code],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    out, err = p.communicate(input="my search query\n", timeout=5)
    print("STDOUT:", out)
    print("STDERR:", err)
    print("EXIT:", p.returncode)
    assert "Got query: 'my search query'" in out
    assert "Got choice: ''" in out or "Got choice: '1'" in out
    print("PASSTHROUGH & AUTO-ENTER TEST PASSED!")

if __name__ == "__main__":
    test_user_input_passthrough()
