import sys
import os
import subprocess
import readline


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
    
    Must check longer operators first to avoid incorrect matches:
    - Check 2>> before 2>
    - Check 1>> before 1>
    - Check >> before >
    """
    result = []
    
    for token in tokens:
        # Check for 2>> first (before 2>)
        if '2>>' in token:
            idx = token.index('2>>')
            before = token[:idx]
            after = token[idx + 3:]
            if before:
                result.append(before)
            result.append('2>>')
            if after:
                result.append(after)
        # Check for 1>> (before 1>)
        elif '1>>' in token:
            idx = token.index('1>>')
            before = token[:idx]
            after = token[idx + 3:]
            if before:
                result.append(before)
            result.append('1>>')
            if after:
                result.append(after)
        # Check for >> (before >)
        elif '>>' in token:
            idx = token.index('>>')
            before = token[:idx]
            after = token[idx + 2:]
            if before:
                result.append(before)
            result.append('>>')
            if after:
                result.append(after)
        # Check for 2>
        elif '2>' in token:
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
    """Parse command and extract redirection information."""
    tokens = parse_command_with_quotes(command_string.strip())
    
    if not tokens:
        return [], None, False, None, False
    
    tokens = split_redirections(tokens)
    
    stdout_file = None
    stdout_append = False
    stderr_file = None
    stderr_append = False
    
    i = 0
    command_tokens = []
    
    while i < len(tokens):
        token = tokens[i]
        
        if token in ('>>', '1>>'):
            if i + 1 < len(tokens):
                stdout_file = tokens[i + 1]
                stdout_append = True
                i += 2
            else:
                i += 1
        elif token in ('>', '1>'):
            if i + 1 < len(tokens):
                stdout_file = tokens[i + 1]
                stdout_append = False
                i += 2
            else:
                i += 1
        elif token == '2>>':
            if i + 1 < len(tokens):
                stderr_file = tokens[i + 1]
                stderr_append = True
                i += 2
            else:
                i += 1
        elif token == '2>':
            if i + 1 < len(tokens):
                stderr_file = tokens[i + 1]
                stderr_append = False
                i += 2
            else:
                i += 1
        else:
            command_tokens.append(token)
            i += 1
    
    return command_tokens, stdout_file, stdout_append, stderr_file, stderr_append


def find_executable_in_path(command_name, path_directories):
    """Search for an executable command in the PATH directories."""
    for directory in path_directories:
        # Skip non-existent directories
        if not os.path.isdir(directory):
            continue
            
        full_path = os.path.join(directory, command_name)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    return None


def get_executables_in_path(path_directories):
    """
    Get all executable files in PATH directories.
    
    Returns:
        Set of executable names (not full paths)
    """
    executables = set()
    
    for directory in path_directories:
        # Skip if directory doesn't exist
        if not os.path.isdir(directory):
            continue
        
        try:
            # List all files in the directory
            for filename in os.listdir(directory):
                full_path = os.path.join(directory, filename)
                
                # Check if it's a file and executable
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    executables.add(filename)
        except PermissionError:
            # Skip directories we can't read
            continue
        except Exception:
            # Skip any other errors
            continue
    
    return executables


def handle_exit_command(args, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """Handle the 'exit' command."""
    # Create empty stderr file if specified
    if stderr_file:
        try:
            mode = 'a' if stderr_append else 'w'
            with open(stderr_file, mode):
                pass
        except:
            pass
    return True


def handle_echo_command(args, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """Handle the 'echo' command - prints arguments to stdout or file."""
    output = ' '.join(args) if args else ''
    
    # Create empty stderr file if specified
    if stderr_file:
        try:
            mode = 'a' if stderr_append else 'w'
            with open(stderr_file, mode):
                pass
        except:
            pass
    
    if stdout_file:
        try:
            mode = 'a' if stdout_append else 'w'
            with open(stdout_file, mode) as f:
                f.write(output + '\n')
        except Exception as e:
            if stderr_file:
                try:
                    mode = 'a' if stderr_append else 'w'
                    with open(stderr_file, mode) as f:
                        f.write(f"bash: {stdout_file}: {e}\n")
                except:
                    print(f"bash: {stdout_file}: {e}", file=sys.stderr)
            else:
                print(f"bash: {stdout_file}: {e}", file=sys.stderr)
    else:
        print(output)


def handle_pwd_command(args, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """Handle the 'pwd' command - prints current working directory."""
    output = os.getcwd()
    
    # Create empty stderr file if specified
    if stderr_file:
        try:
            mode = 'a' if stderr_append else 'w'
            with open(stderr_file, mode):
                pass
        except:
            pass
    
    if stdout_file:
        try:
            mode = 'a' if stdout_append else 'w'
            with open(stdout_file, mode) as f:
                f.write(output + '\n')
        except Exception as e:
            if stderr_file:
                try:
                    mode = 'a' if stderr_append else 'w'
                    with open(stderr_file, mode) as f:
                        f.write(f"bash: {stdout_file}: {e}\n")
                except:
                    print(f"bash: {stdout_file}: {e}", file=sys.stderr)
            else:
                print(f"bash: {stdout_file}: {e}", file=sys.stderr)
    else:
        print(output)


def handle_cd_command(args, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """Handle the 'cd' command - changes current working directory."""
    stderr_handle = None
    
    if stderr_file:
        try:
            mode = 'a' if stderr_append else 'w'
            stderr_handle = open(stderr_file, mode)
        except:
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


def handle_type_command(args, builtin_commands, path_directories, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """Handle the 'type' command - shows what kind of command something is."""
    stderr_handle = None
    
    if stderr_file:
        try:
            mode = 'a' if stderr_append else 'w'
            stderr_handle = open(stderr_file, mode)
        except:
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
            mode = 'a' if stdout_append else 'w'
            with open(stdout_file, mode) as f:
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


def execute_external_command(command_parts, path_directories, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """Execute an external command (not a shell built-in)."""
    command_name = command_parts[0]
    
    executable_path = find_executable_in_path(command_name, path_directories)
    
    if executable_path:
        try:
            stdout_handle = None
            stderr_handle = None
            
            if stdout_file:
                mode = 'a' if stdout_append else 'w'
                stdout_handle = open(stdout_file, mode)
            
            if stderr_file:
                mode = 'a' if stderr_append else 'w'
                stderr_handle = open(stderr_file, mode)
            
            subprocess.run(
                command_parts,
                executable=executable_path,
                stdout=stdout_handle,
                stderr=stderr_handle
            )
            
            if stdout_handle:
                stdout_handle.close()
            if stderr_handle:
                stderr_handle.close()
                
        except Exception as e:
            error_msg = f"Error executing {command_name}: {e}\n"
            if stderr_file:
                try:
                    mode = 'a' if stderr_append else 'w'
                    with open(stderr_file, mode) as f:
                        f.write(error_msg)
                except:
                    print(error_msg.rstrip())
            else:
                print(error_msg.rstrip())
    else:
        error_msg = f"{command_name}: command not found\n"
        if stderr_file:
            try:
                mode = 'a' if stderr_append else 'w'
                with open(stderr_file, mode) as f:
                    f.write(error_msg)
            except:
                print(error_msg.rstrip())
        else:
            print(error_msg.rstrip())


# Tab completion setup
BUILTIN_COMMANDS = ["echo", "exit", "pwd", "cd", "type"]
PATH_DIRECTORIES = []
EXECUTABLES_CACHE = set()

# Track tab completion state
last_completion_text = None
last_completion_options = []
tab_press_count = 0


def update_executables_cache():
    """Update the cache of available executables."""
    global EXECUTABLES_CACHE
    EXECUTABLES_CACHE = get_executables_in_path(PATH_DIRECTORIES)


def longest_common_prefix(strings):
    """
    Find the longest common prefix of a list of strings.
    
    Args:
        strings: List of strings to find common prefix
        
    Returns:
        The longest common prefix string, or empty string if none
    
    Examples:
        ['xyz_foo', 'xyz_foo_bar', 'xyz_foo_bar_baz'] -> 'xyz_foo'
        ['abc', 'abd', 'abe'] -> 'ab'
        ['hello', 'world'] -> ''
    """
    if not strings:
        return ""
    
    if len(strings) == 1:
        return strings[0]
    
    # Sort to make comparison easier (shortest and longest lexicographically)
    strings = sorted(strings)
    first = strings[0]
    last = strings[-1]
    
    # Find common prefix between first and last
    # If they share a prefix, all strings in between will too
    common = []
    for i in range(min(len(first), len(last))):
        if first[i] == last[i]:
            common.append(first[i])
        else:
            break
    
    return ''.join(common)


def completer(text, state):
    """
    Tab completion function for readline.
    
    Completes both builtin commands and executables in PATH.
    Handles:
    - Single match: complete with trailing space
    - Multiple matches: complete to longest common prefix
    - No additional completion: ring bell
    - Second tab with multiple matches: show all options
    
    Args:
        text: The text to complete
        state: The iteration state (0 for first call, 1 for second, etc.)
    
    Returns:
        The completion string, or None if no more completions
    """
    global last_completion_text, last_completion_options, tab_press_count
    
    # Get the current line buffer
    line = readline.get_line_buffer()
    
    # Only complete if we're at the beginning of the line (completing the command)
    if line.lstrip() == text:
        # When state is 0, this is a new completion request
        if state == 0:
            # Combine builtins and executables
            all_commands = set(BUILTIN_COMMANDS) | EXECUTABLES_CACHE
            
            # Find all commands that start with the given text
            options = sorted([cmd for cmd in all_commands if cmd.startswith(text)])
            
            # Check if this is a new completion or continuation of previous
            if text != last_completion_text:
                # New completion
                last_completion_text = text
                last_completion_options = options
                tab_press_count = 1
            else:
                # Same text - increment tab press count
                tab_press_count += 1
            
            # Handle different cases based on number of matches
            if len(options) == 0:
                # No matches - ring bell
                sys.stdout.write('\a')
                sys.stdout.flush()
                return None
            
            elif len(options) == 1:
                # Single match - complete it with a trailing space
                result = options[0] + ' '
                # Reset state since we completed
                last_completion_text = None
                tab_press_count = 0
                return result
            
            else:
                # Multiple matches - find longest common prefix
                lcp = longest_common_prefix(options)
                
                # Check if we can complete further than current text
                if len(lcp) > len(text):
                    # We can complete to the LCP
                    if tab_press_count == 1:
                        # First tab - complete to LCP (no trailing space)
                        return lcp
                    elif tab_press_count == 2:
                        # Second tab - show all options
                        print()
                        print('  '.join(options))
                        # Redisplay the prompt and current LCP
                        sys.stdout.write("$ " + lcp)
                        sys.stdout.flush()
                        return None
                    else:
                        # Third+ tab - ring bell
                        sys.stdout.write('\a')
                        sys.stdout.flush()
                        return None
                else:
                    # LCP is same as current text - can't complete further
                    if tab_press_count == 1:
                        # First tab - ring bell (no progress possible)
                        sys.stdout.write('\a')
                        sys.stdout.flush()
                        return None
                    elif tab_press_count == 2:
                        # Second tab - show all options
                        print()
                        print('  '.join(options))
                        # Redisplay the prompt and current text
                        sys.stdout.write("$ " + text)
                        sys.stdout.flush()
                        return None
                    else:
                        # Third+ tab - ring bell
                        sys.stdout.write('\a')
                        sys.stdout.flush()
                        return None
        else:
            # state > 0 means readline is asking for additional completions
            # We don't provide multiple completion options - we handle it manually
            return None
    else:
        # Not at the beginning - reset state
        last_completion_text = None
        last_completion_options = []
        tab_press_count = 0
        return None
    
    return None


def setup_readline():
    """Configure readline for tab completion."""
    # Set the completer function
    readline.set_completer(completer)
    
    # Set the completion key to TAB
    readline.parse_and_bind('tab: complete')
    
    # Disable filename completion (we only want command completion)
    readline.set_completer_delims(' \t\n')


def main():
    """Main shell loop."""
    global PATH_DIRECTORIES, last_completion_text, tab_press_count
    
    # Get PATH directories
    path_env = os.environ.get("PATH", "")
    PATH_DIRECTORIES = path_env.split(os.pathsep)
    
    # Build executables cache
    update_executables_cache()
    
    # Setup tab completion
    setup_readline()
    
    BUILTIN_COMMANDS_SET = {"echo", "type", "exit", "pwd", "cd"}
    
    while True:
        # Reset tab completion state at each new prompt
        last_completion_text = None
        tab_press_count = 0
        
        sys.stdout.write("$ ")
        sys.stdout.flush()
        
        try:
            user_input = input()
        except EOFError:
            print()
            break
        
        command_tokens, stdout_file, stdout_append, stderr_file, stderr_append = parse_command_with_redirection(user_input)
        
        if not command_tokens:
            continue
        
        command_name = command_tokens[0]
        arguments = command_tokens[1:]
        
        if command_name == "exit":
            should_exit = handle_exit_command(arguments, stdout_file, stdout_append, stderr_file, stderr_append)
            if should_exit:
                break
        elif command_name == "echo":
            handle_echo_command(arguments, stdout_file, stdout_append, stderr_file, stderr_append)
        elif command_name == "pwd":
            handle_pwd_command(arguments, stdout_file, stdout_append, stderr_file, stderr_append)
        elif command_name == "cd":
            handle_cd_command(arguments, stdout_file, stdout_append, stderr_file, stderr_append)
        elif command_name == "type":
            handle_type_command(arguments, BUILTIN_COMMANDS_SET, PATH_DIRECTORIES, stdout_file, stdout_append, stderr_file, stderr_append)
        else:
            execute_external_command(command_tokens, PATH_DIRECTORIES, stdout_file, stdout_append, stderr_file, stderr_append)


if __name__ == "__main__":
    main()