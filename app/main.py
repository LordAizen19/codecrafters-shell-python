import sys
import os
import subprocess


def type_command(cmd):
    """Handle the 'type' builtin command"""

    # Step 1: Check if it's a builtin
    if cmd in BUILTINS:
        print(f"{cmd} is a shell builtin")
        return

    # Step 2: Search for executable in PATH
    executable_path = find_executable(cmd)

    if executable_path:
        print(f"{cmd} is {executable_path}")
    else:
        print(f"{cmd}: not found")


def find_executable(cmd):
    """Search for an executable in PATH and return its full path if found"""
    path_env = os.environ.get("PATH", "")
    directories = path_env.split(os.pathsep)

    for directory in directories:
        full_path = os.path.join(directory, cmd)

        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path

    return None


def run_external_program(cmd, args):
    """Find and execute an external program"""

    # Find the executable in PATH
    executable_path = find_executable(cmd)

    if not executable_path:
        print(f"{cmd}: command not found")
        return

    # Execute the program
    # IMPORTANT: Pass the original command name as first arg, not the full path
    try:
        subprocess.run([executable_path, cmd] + args)
    except Exception as e:
        print(f"{cmd}: error executing: {e}")


BUILTINS = {
    "type": type_command,
    "exit": lambda code=0, *_: sys.exit(int(code)),
    "echo": lambda *args: print(" ".join(args)),
}


def main():
    while True:  # infinite loop keeps running forever
        sys.stdout.write("$ ")
        sys.stdout.flush()

        user_input = input().strip()

        parts = user_input.split()
        if not parts:  # Handle empty input
            continue

        cmd = parts[0]
        args = parts[1:]

        if cmd in BUILTINS:
            BUILTINS[cmd](*args)
        else:
            # Not a builtin, try to run as external program
            run_external_program(cmd, args)


if __name__ == "__main__":
    main()