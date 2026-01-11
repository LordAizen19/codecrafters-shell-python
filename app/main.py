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
    """Search for an executable in PATH directories"""
    # Get the PATH environment variable
    path_env = os.environ.get("PATH", "")

    # Split PATH into directories
    directories = path_env.split(os.pathsep)

    # Search each directory
    for directory in directories:
        full_path = os.path.join(directory, cmd)

        # Check if file exists AND is executable
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path

    return None  # Not found


def run_external_command(cmd, args):
    """Find and execute an external program"""

    # Step 1: Find the executable in PATH
    executable_path = find_executable(cmd)

    if not executable_path:
        print(f"{cmd}: command not found")
        return

    # Step 2: Run the program with arguments
    # subprocess.run executes the external program
    # [executable_path] + args creates the full command with arguments
    try:
        subprocess.run([executable_path] + args)
    except Exception as e:
        print(f"Error running {cmd}: {e}")


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

        # Check if it's a builtin command
        if cmd in BUILTINS:
            BUILTINS[cmd](*args)
        else:
            # It's an external command, try to run it
            run_external_command(cmd, args)


if __name__ == "__main__":
    main()