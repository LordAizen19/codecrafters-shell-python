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
        ["cat", "file", "2>err"] → ["cat", "file", "2>", "err"]
    """
    result = []
    
    for token in tokens:
        # Check for 2> first
        if '2>' in token:
            idx = token.index('2>')
            before = token[:idx]
            after = token[idx + 2:]
            
            if before:
                result.append(before)
            result.append('2>')
            if after:
                result.append(after)
        
        # Check for 1>
        elif '1>' in token:
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
        (command_tokens, stdout_file, stderr_file) where:
        - command_tokens: list of command and arguments
        - stdout_file: filename to redirect stdout to, or None
        - stderr_file: filename to redirect stderr to, or None
    """
    # First, parse quotes normally
    tokens = parse_command_with_quotes(command_string.strip())
    
    if not tokens:
        return [], None, None
    
    # Split any tokens containing redirection operators
    tokens = split_redirections(tokens)
    
    # Track redirection targets
    stdout_file = None
    stderr_file = None
    
    # Find and remove redirection operators and their targets
    i = 0
    command_tokens = []
    
    while i < len(tokens):
        token = tokens[i]
        
        if token in ('>', '1>'):
            # Redirect stdout
            if i + 1 < len(tokens):
                stdout_file = tokens[i + 1]
                i += 2  # Skip both operator and filename
            else:
                i += 1
        
        elif token == '2>':
            # Redirect stderr
            if i + 1 < len(tokens):
                stderr_file = tokens[i + 1]
                i += 2  # Skip both operator and filename
            else:
                i += 1
        
        else:
            # Regular token - part of the command
            command_tokens.append(token)
            i += 1
    
    return command_tokens, stdout_file, stderr_file


def find_executable_in_path(command_name, path_directories):
    """Search for an executable command in the PATH directories."""
    for directory in path_directories:
        full_path = os.path.join(directory, command_name)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    return None


def handle_exit_command(args, stdout_file=None, stderr_file=None):
    """Handle the 'exit' command."""
    # Create stderr file if specified (even if empty)
    if stderr_file:
        try:
            open(stderr_file, 'w').close()
        except:
            pass
    
    return True


def handle_echo_command(args, stdout_file=None, stderr_file=None):
    """Handle the 'echo' command - prints arguments to stdout or file."""
    output = ' '.join(args) if args else ''
    
    # Create stderr file if specified (even if empty)
    if stderr_file:
        try:
            open(stderr_file, 'w').close()
        except:
            pass
    
    if stdout_file:
        # Redirect stdout to file
        try:
            with open(stdout_file, 'w') as f:
                f.write(output + '\n')
        except Exception as e:
            # Error opening file - write to stderr
            if stderr_file:
                try:
                    with open(stderr_file, 'w') as f:
                        f.write(f"bash: {stdout_file}: {e}\n")
                except:
                    print(f"bash: {stdout_file}: {e}", file=sys.stderr)
            else:
                print(f"bash: {stdout_file}: {e}", file=sys.stderr)
    else:
        # Print to stdout (terminal)
        print(output)


def handle_pwd_command(args, stdout_file=None, stderr_file=None):
    """Handle the 'pwd' command - prints current working directory."""
    output = os.getcwd()
    
    # Create stderr file if specified (even if empty)
    if stderr_file:
        try:
            open(stderr_file, 'w').close()
        except:
            pass
    
    if stdout_file:
        try:
            with open(stdout_file, 'w') as f:
                f.write(output + '\n')
        except Exception as e:
            if stderr_file:
                try:
                    with open(stderr_file, 'w') as f:
                        f.write(f"bash: {stdout_file}: {e}\n")
                except:
                    print(f"bash: {stdout_file}: {e}", file=sys.stderr)
            else:
                print(f"bash: {stdout_file}: {e}", file=sys.stderr)
    else:
        print(output)


def handle_cd_command(args, stdout_file=None, stderr_file=None):
    """Handle the 'cd' command - changes current working directory."""
    # Create stderr file if specified (even if empty initially)
    if stderr_file:
        try:
            # Pre-create the file
            stderr_handle = open(stderr_file, 'w')
        except:
            stderr_handle = None
    else:
        stderr_handle = None
    
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
        error_msg = f"cd: {args[0]}: No such file or directory\n"
        if stderr_handle:
            stderr_handle.write(error_msg)
        else:
            print(error_msg.rstrip())
    except NotADirectoryError:
        error_msg = f"cd: {args[0]}: Not a directory\n"
        if stderr_handle:
            stderr_handle.write(error_msg)
        else:
            print(error_msg.rstrip())
    except PermissionError:
        error_msg = f"cd: {args[0]}: Permission denied\n"
        if stderr_handle:
            stderr_handle.write(error_msg)
        else:
            print(error_msg.rstrip())
    
    if stderr_handle:
        stderr_handle.close()


def handle_type_command(args, builtin_commands, path_directories, stdout_file=None, stderr_file=None):
    """Handle the 'type' command - shows what kind of command something is."""
    # Create stderr file if specified (even if empty initially)
    if stderr_file:
        try:
            stderr_handle = open(stderr_file, 'w')
        except:
            stderr_handle = None
    else:
        stderr_handle = None
    
    if not args:
        error_msg = "type: missing argument\n"
        if stderr_handle:
            stderr_handle.write(error_msg)
        else:
            print(error_msg.rstrip())
        
        if stderr_handle:
            stderr_handle.close()
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
    
    if stdout_file:
        try:
            with open(stdout_file, 'w') as f:
                f.write(output + '\n')
        except Exception as e:
            error_msg = f"bash: {stdout_file}: {e}\n"
            if stderr_handle:
                stderr_handle.write(error_msg)
            else:
                print(error_msg.rstrip(), file=sys.stderr)
    else:
        print(output)
    
    if stderr_handle:
        stderr_handle.close()


def execute_external_command(command_parts, path_directories, stdout_file=None, stderr_file=None):
    """Execute an external command (not a shell built-in)."""
    command_name = command_parts[0]
    
    executable_path = find_executable_in_path(command_name, path_directories)
    
    if executable_path:
        try:
            # Prepare file handles for redirection
            stdout_handle = None
            stderr_handle = None
            
            if stdout_file:
                stdout_handle = open(stdout_file, 'w')
            
            if stderr_file:
                stderr_handle = open(stderr_file, 'w')
            
            # Execute with appropriate redirections
            subprocess.run(
                command_parts,
                executable=executable_path,
                stdout=stdout_handle,  # None means terminal
                stderr=stderr_handle   # None means terminal
            )
            
            # Close file handles
            if stdout_handle:
                stdout_handle.close()
            if stderr_handle:
                stderr_handle.close()
                
        except Exception as e:
            error_msg = f"Error executing {command_name}: {e}\n"
            if stderr_file:
                try:
                    with open(stderr_file, 'w') as f:
                        f.write(error_msg)
                except:
                    print(error_msg.rstrip())
            else:
                print(error_msg.rstrip())
    else:
        error_msg = f"{command_name}: command not found\n"
        if stderr_file:
            try:
                with open(stderr_file, 'w') as f:
                    f.write(error_msg)
            except:
                print(error_msg.rstrip())
        else:
            print(error_msg.rstrip())


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
        command_tokens, stdout_file, stderr_file = parse_command_with_redirection(user_input)
        
        if not command_tokens:
            continue
        
        command_name = command_tokens[0]
        arguments = command_tokens[1:]
        
        # Execute built-in commands
        if command_name == "exit":
            should_exit = handle_exit_command(arguments, stdout_file, stderr_file)
            if should_exit:
                break
        elif command_name == "echo":
            handle_echo_command(arguments, stdout_file, stderr_file)
        elif command_name == "pwd":
            handle_pwd_command(arguments, stdout_file, stderr_file)
        elif command_name == "cd":
            handle_cd_command(arguments, stdout_file, stderr_file)
        elif command_name == "type":
            handle_type_command(arguments, BUILTIN_COMMANDS, path_directories, stdout_file, stderr_file)
        else:
            # Execute external commands
            execute_external_command(command_tokens, path_directories, stdout_file, stderr_file)


if __name__ == "__main__":
    main()