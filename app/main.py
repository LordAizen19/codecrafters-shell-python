import sys
import os
import subprocess


def parse_command_with_quotes(command_string):
    """
    Parse command string, handling single quotes.

    Single quotes preserve all characters literally, including spaces.
    Adjacent quoted strings are concatenated.
    """
    arguments = []
    current_argument = ""
    inside_quotes = False

    for char in command_string:
        if char == "'":
            inside_quotes = not inside_quotes
        elif char in (' ', '\t'):
            if inside_quotes:
                current_argument += char
            else:
                if current_argument:
                    arguments.append(current_argument)
                    current_argument = ""
        else:
            current_argument += char

    if current_argument:
        arguments.append(current_argument)

    return arguments


def find_executable_in_path(command_name, path_directories):
    """
    Search for an executable command in the PATH directories.

    Args:
        command_name: Name of the command to find (e.g., 'ls', 'cat')
        path_directories: List of directories to search

    Returns:
        Full path to the executable if found, None otherwise
    """
    for directory in path_directories:
        full_path = os.path.join(directory, command_name)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    return None


def handle_exit_command(args):
    """Handle the 'exit' command."""
    return True  # Signal to exit the shell


def handle_echo_command(args):
    """Handle the 'echo' command - prints arguments to stdout."""
    if args:
        print(' '.join(args))
    else:
        print()  # Print empty line if no arguments


def handle_pwd_command(args):
    """Handle the 'pwd' command - prints current working directory."""
    print(os.getcwd())


def handle_cd_command(args):
    """
    Handle the 'cd' command - changes current working directory.

    Args:
        args: List of arguments (should contain 0 or 1 path)
    """
    # No argument: go to home directory
    if not args:
        target_directory = os.path.expanduser("~")
    else:
        target_directory = args[0]

        # Handle special case: ~ expansion
        if target_directory.startswith("~"):
            target_directory = os.path.expanduser(target_directory)
        # Handle relative paths (not starting with /)
        elif not target_directory.startswith("/"):
            target_directory = os.path.join(os.getcwd(), target_directory)

    # Attempt to change directory
    try:
        os.chdir(target_directory)
    except FileNotFoundError:
        print(f"cd: {args[0]}: No such file or directory")
    except NotADirectoryError:
        print(f"cd: {args[0]}: Not a directory")
    except PermissionError:
        print(f"cd: {args[0]}: Permission denied")


def handle_type_command(args, builtin_commands, path_directories):
    """
    Handle the 'type' command - shows what kind of command something is.

    Args:
        args: List of arguments (should contain command name)
        builtin_commands: Set of built-in command names
        path_directories: List of PATH directories to search
    """
    if not args:
        print("type: missing argument")
        return

    command_name = args[0]

    # Check if it's a built-in command
    if command_name in builtin_commands:
        print(f"{command_name} is a shell builtin")
    else:
        # Check if it exists in PATH
        executable_path = find_executable_in_path(command_name, path_directories)
        if executable_path:
            print(f"{command_name} is {executable_path}")
        else:
            print(f"{command_name}: not found")


def execute_external_command(command_parts, path_directories):
    """
    Execute an external command (not a shell built-in).

    Args:
        command_parts: List of command and its arguments
        path_directories: List of PATH directories to search
    """
    command_name = command_parts[0]

    # Find the executable
    executable_path = find_executable_in_path(command_name, path_directories)

    if executable_path:
        try:
            # Execute the command using list form to preserve arguments
            # This ensures filenames with spaces are passed correctly
            subprocess.run([executable_path] + command_parts[1:])
        except Exception as e:
            print(f"Error executing {command_name}: {e}")
    else:
        print(f"{command_name}: command not found")


def parse_command(command_string):
    """Parse command with proper quote handling."""
    parts = parse_command_with_quotes(command_string.strip())

    if not parts:
        return None, None

    return parts[0], parts[1:]


def main():
    """Main shell loop."""

    # Define built-in commands (using a set for O(1) lookup)
    BUILTIN_COMMANDS = {"echo", "type", "exit", "pwd", "cd"}

    # Get PATH environment variable and split into directories
    path_env = os.environ.get("PATH", "")
    path_directories = path_env.split(os.pathsep)

    # Main REPL (Read-Eval-Print Loop)
    while True:
        # Display prompt
        sys.stdout.write("$ ")
        sys.stdout.flush()  # Ensure prompt is displayed immediately

        # Read user input
        try:
            user_input = input()
        except EOFError:
            # Handle Ctrl+D gracefully
            print()
            break

        # Parse the command
        command_name, arguments = parse_command(user_input)

        # Skip empty commands
        if command_name is None:
            continue

        # Execute built-in commands
        if command_name == "exit":
            should_exit = handle_exit_command(arguments)
            if should_exit:
                break

        elif command_name == "echo":
            handle_echo_command(arguments)

        elif command_name == "pwd":
            handle_pwd_command(arguments)

        elif command_name == "cd":
            handle_cd_command(arguments)

        elif command_name == "type":
            handle_type_command(arguments, BUILTIN_COMMANDS, path_directories)

        # Execute external commands
        else:
            execute_external_command([command_name] + arguments, path_directories)


if __name__ == "__main__":
    main()