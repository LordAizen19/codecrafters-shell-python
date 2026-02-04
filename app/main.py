import sys
import os
import subprocess


def parse_command_with_quotes(command_string):
    r"""
    Parse command string, handling:
    - Single quotes (everything literal)
    - Double quotes (everything literal for now)
    - Backslash escaping outside single quotes
    
    Backslash rules:
    - Outside quotes or in double quotes: escape next character
    - Inside single quotes: backslash is literal
    
    Examples:
        echo three\ \ \ spaces → ["echo", "three   spaces"]
        echo test\nexample → ["echo", "testnexample"]
        echo hello\\world → ["echo", "hello\world"]
        echo \'hello\' → ["echo", "'hello'"]
    """
    arguments = []
    current_argument = ""
    quote_state = None  # None, 'SINGLE', or 'DOUBLE'
    escape_next = False  # True if previous char was backslash
    
    for char in command_string:
        # STEP 1: Handle escaped characters
        if escape_next:
            # Add the character as-is (it's escaped)
            current_argument += char
            escape_next = False
            continue
        
        # STEP 2: Handle backslash (only works outside single quotes)
        if char == '\\' and quote_state != 'SINGLE':
            # Next character will be escaped
            escape_next = True
            continue  # Don't add the backslash itself
        
        # STEP 3: Handle single quotes
        if char == "'":
            if quote_state is None:
                quote_state = 'SINGLE'
            elif quote_state == 'SINGLE':
                quote_state = None
            else:
                # Inside double quotes, single quote is literal
                current_argument += char
            continue
        
        # STEP 4: Handle double quotes
        if char == '"':
            if quote_state is None:
                quote_state = 'DOUBLE'
            elif quote_state == 'DOUBLE':
                quote_state = None
            else:
                # Inside single quotes, double quote is literal
                current_argument += char
            continue
        
        # STEP 5: Handle whitespace
        if char in (' ', '\t'):
            if quote_state is not None:
                # Inside quotes: preserve whitespace
                current_argument += char
            else:
                # Outside quotes: whitespace ends the argument
                if current_argument:
                    arguments.append(current_argument)
                    current_argument = ""
            continue
        
        # STEP 6: Regular characters
        current_argument += char
    
    # Don't forget the last argument
    if current_argument:
        arguments.append(current_argument)
    
    return arguments


def find_executable_in_path(command_name, path_directories):
    """Search for an executable command in the PATH directories."""
    for directory in path_directories:
        full_path = os.path.join(directory, command_name)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    return None


def handle_exit_command(args):
    """Handle the 'exit' command."""
    return True


def handle_echo_command(args):
    """Handle the 'echo' command - prints arguments to stdout."""
    if args:
        print(' '.join(args))
    else:
        print()


def handle_pwd_command(args):
    """Handle the 'pwd' command - prints current working directory."""
    print(os.getcwd())


def handle_cd_command(args):
    """Handle the 'cd' command - changes current working directory."""
    if not args:
        target_directory = os.path.expanduser("~")
    else:
        target_directory = args[0]
        
        if target_directory.startswith("~"):
            target_directory = os.path.expanduser(target_directory)
        elif not target_directory.startswith("/"):
            target_directory = os.path.join(os.getcwd(), target_directory)
    
    try:
        os.chdir(target_directory)
    except FileNotFoundError:
        print(f"cd: {args[0]}: No such file or directory")
    except NotADirectoryError:
        print(f"cd: {args[0]}: Not a directory")
    except PermissionError:
        print(f"cd: {args[0]}: Permission denied")


def handle_type_command(args, builtin_commands, path_directories):
    """Handle the 'type' command - shows what kind of command something is."""
    if not args:
        print("type: missing argument")
        return
    
    command_name = args[0]
    
    if command_name in builtin_commands:
        print(f"{command_name} is a shell builtin")
    else:
        executable_path = find_executable_in_path(command_name, path_directories)
        if executable_path:
            print(f"{command_name} is {executable_path}")
        else:
            print(f"{command_name}: not found")


def execute_external_command(command_parts, path_directories):
    """Execute an external command (not a shell built-in)."""
    command_name = command_parts[0]
    
    executable_path = find_executable_in_path(command_name, path_directories)
    
    if executable_path:
        try:
            subprocess.run(
                command_parts,
                executable=executable_path
            )
        except Exception as e:
            print(f"Error executing {command_name}: {e}")
    else:
        print(f"{command_name}: command not found")


def parse_command(command_string):
    """Parse command with proper quote and escape handling."""
    parts = parse_command_with_quotes(command_string.strip())
    
    if not parts:
        return None, None
    
    return parts[0], parts[1:]


def main():
    """Main shell loop."""
    
    BUILTIN_COMMANDS = {"echo", "type", "exit", "pwd", "cd"}
    
    path_env = os.environ.get("PATH", "")
    path_directories = path_env.split(os.pathsep)
    
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()
        
        try:
            user_input = input()
        except EOFError:
            print()
            break
        
        command_name, arguments = parse_command(user_input)
        
        if command_name is None:
            continue
        
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
        else:
            execute_external_command([command_name] + arguments, path_directories)


if __name__ == "__main__":
    main()