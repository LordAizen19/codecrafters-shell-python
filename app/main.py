import sys
import os
import subprocess


def parse_command_with_quotes(command_string):
    r"""
    Parse command string, handling:
    - Single quotes (everything literal)
    - Double quotes (backslash escapes \ and " only)
    - Backslash escaping outside quotes
    
    This does NOT handle redirection operators - that's done separately.
    """
    arguments = []
    current_argument = ""
    quote_state = None  # None, 'SINGLE', or 'DOUBLE'
    escape_next = False  # True if previous char was backslash
    
    for char in command_string:
        # STEP 1: Handle escaped characters
        if escape_next:
            if quote_state == 'DOUBLE':
                # Inside double quotes: only \ and " can be escaped
                if char in ('\\', '"'):
                    current_argument += char
                else:
                    # Not a valid escape sequence - keep the backslash
                    current_argument += '\\' + char
            else:
                # Outside quotes: add character as-is
                current_argument += char
            escape_next = False
            continue
        
        # STEP 2: Handle backslash
        if char == '\\':
            if quote_state == 'SINGLE':
                # Inside single quotes: backslash is literal
                current_argument += char
            else:
                # Outside quotes or inside double quotes: next char might be escaped
                escape_next = True
            continue
        
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
    
    # Handle trailing backslash
    if escape_next and quote_state != 'DOUBLE':
        current_argument += '\\'
    
    if current_argument:
        arguments.append(current_argument)
    
    return arguments


def split_redirections(tokens):
    """
    Split tokens that contain redirection operators.
    
    Example:
        ["echo", "hello>file"] → ["echo", "hello", ">", "file"]
        ["ls", "1>out"] → ["ls", "1>", "out"]
    """
    result = []
    
    for token in tokens:
        # Check for 1> first (longer match)
        if '1>' in token:
            idx = token.index('1>')
            before = token[:idx]
            after = token[idx + 2:]
            
            if before:
                result.append(before)
            result.append('1>')
            if after:
                result.append(after)
        
        # Check for >
        elif '>' in token:
            idx = token.index('>')
            before = token[:idx]
            after = token[idx + 1:]
            
            if before:
                result.append(before)
            result.append('>')
            if after:
                result.append(after)
        
        else:
            result.append(token)
    
    return result


def parse_command_with_redirection(command_string):
    """
    Parse command and extract redirection information.
    
    Returns:
        (command_tokens, output_file) where:
        - command_tokens: list of command and arguments
        - output_file: filename to redirect to, or None
    """
    # First, parse quotes normally
    tokens = parse_command_with_quotes(command_string.strip())
    
    if not tokens:
        return [], None
    
    # Split any tokens containing redirection operators
    tokens = split_redirections(tokens)
    
    # Look for redirection operators
    output_file = None
    
    # Check for > or 1> (they work the same way)
    for i, token in enumerate(tokens):
        if token in ('>', '1>'):
            # Everything before is the command
            command_tokens = tokens[:i]
            
            # Next token is the output file
            if i + 1 < len(tokens):
                output_file = tokens[i + 1]
            
            # For this stage, ignore anything after the filename
            break
    else:
        # No redirection found
        command_tokens = tokens
    
    return command_tokens, output_file


def find_executable_in_path(command_name, path_directories):
    """Search for an executable command in the PATH directories."""
    for directory in path_directories:
        full_path = os.path.join(directory, command_name)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    return None


def handle_exit_command(args, output_file=None):
    """Handle the 'exit' command."""
    return True


def handle_echo_command(args, output_file=None):
    """Handle the 'echo' command - prints arguments to stdout or file."""
    output = ' '.join(args) if args else ''
    
    if output_file:
        # Redirect to file
        try:
            with open(output_file, 'w') as f:
                f.write(output + '\n')
        except Exception as e:
            print(f"bash: {output_file}: {e}", file=sys.stderr)
    else:
        # Print to stdout
        print(output)


def handle_pwd_command(args, output_file=None):
    """Handle the 'pwd' command - prints current working directory."""
    output = os.getcwd()
    
    if output_file:
        try:
            with open(output_file, 'w') as f:
                f.write(output + '\n')
        except Exception as e:
            print(f"bash: {output_file}: {e}", file=sys.stderr)
    else:
        print(output)


def handle_cd_command(args, output_file=None):
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


def handle_type_command(args, builtin_commands, path_directories, output_file=None):
    """Handle the 'type' command - shows what kind of command something is."""
    if not args:
        print("type: missing argument")
        return
    
    command_name = args[0]
    
    if command_name in builtin_commands:
        output = f"{command_name} is a shell builtin"
    else:
        executable_path = find_executable_in_path(command_name, path_directories)
        if executable_path:
            output = f"{command_name} is {executable_path}"
        else:
            output = f"{command_name}: not found"
    
    if output_file:
        try:
            with open(output_file, 'w') as f:
                f.write(output + '\n')
        except Exception as e:
            print(f"bash: {output_file}: {e}", file=sys.stderr)
    else:
        print(output)


def execute_external_command(command_parts, path_directories, output_file=None):
    """Execute an external command (not a shell built-in)."""
    command_name = command_parts[0]
    
    executable_path = find_executable_in_path(command_name, path_directories)
    
    if executable_path:
        try:
            if output_file:
                # Redirect stdout to file
                with open(output_file, 'w') as f:
                    subprocess.run(
                        command_parts,
                        executable=executable_path,
                        stdout=f  # Redirect stdout only
                        # stderr still goes to terminal
                    )
            else:
                # Normal execution
                subprocess.run(
                    command_parts,
                    executable=executable_path
                )
        except Exception as e:
            print(f"Error executing {command_name}: {e}")
    else:
        print(f"{command_name}: command not found")


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
        
        # Parse command and check for redirection
        command_tokens, output_file = parse_command_with_redirection(user_input)
        
        if not command_tokens:
            continue
        
        command_name = command_tokens[0]
        arguments = command_tokens[1:]
        
        # Execute built-in commands
        if command_name == "exit":
            should_exit = handle_exit_command(arguments, output_file)
            if should_exit:
                break
        elif command_name == "echo":
            handle_echo_command(arguments, output_file)
        elif command_name == "pwd":
            handle_pwd_command(arguments, output_file)
        elif command_name == "cd":
            handle_cd_command(arguments, output_file)
        elif command_name == "type":
            handle_type_command(arguments, BUILTIN_COMMANDS, path_directories, output_file)
        else:
            # Execute external commands
            execute_external_command(command_tokens, path_directories, output_file)


if __name__ == "__main__":
    main()