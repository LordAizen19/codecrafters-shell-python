import sys
import os


def type_command(cmd):
    """Handle the 'type' builtin command"""

    # Step 1: Check if it's a builtin
    if cmd in BUILTINS:
        print(f"{cmd} is a shell builtin")
        return

    # Step 2: Get the PATH environment variable
    path_env = os.environ.get("PATH", "")

    # Step 3: Split PATH into directories (using os.pathsep for cross-platform compatibility)
    # On Linux/Mac: PATH uses ':' as separator
    # On Windows: PATH uses ';' as separator
    # os.pathsep automatically uses the correct one
    directories = path_env.split(os.pathsep)

    # Step 4: Search each directory
    for directory in directories:
        # Build the full path to the potential executable
        full_path = os.path.join(directory, cmd)

        # Step 5: Check if file exists AND is executable
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            print(f"{cmd} is {full_path}")
            return

    # Step 6: If we get here, command wasn't found
    print(f"{cmd}: not found")


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
            print(f"{cmd}: command not found")


if __name__ == "__main__":
    main()