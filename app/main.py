import sys
import os
import subprocess
import readline


# Command history storage
COMMAND_HISTORY = []


def parse_command_with_quotes(command_string):
    r"""Parse command string with quote handling."""
    arguments = []
    current_argument = ""
    quote_state = None
    escape_next = False
    
    for char in command_string:
        if escape_next:
            if quote_state == 'DOUBLE':
                if char in ('\\', '"'):
                    current_argument += char
                else:
                    current_argument += '\\' + char
            else:
                current_argument += char
            escape_next = False
            continue
        
        if char == '\\':
            if quote_state == 'SINGLE':
                current_argument += char
            else:
                escape_next = True
            continue
        
        if char == "'":
            if quote_state is None:
                quote_state = 'SINGLE'
            elif quote_state == 'SINGLE':
                quote_state = None
            else:
                current_argument += char
            continue
        
        if char == '"':
            if quote_state is None:
                quote_state = 'DOUBLE'
            elif quote_state == 'DOUBLE':
                quote_state = None
            else:
                current_argument += char
            continue
        
        if char in (' ', '\t'):
            if quote_state is not None:
                current_argument += char
            else:
                if current_argument:
                    arguments.append(current_argument)
                    current_argument = ""
            continue
        
        current_argument += char
    
    if escape_next and quote_state != 'DOUBLE':
        current_argument += '\\'
    
    if current_argument:
        arguments.append(current_argument)
    
    return arguments


def split_by_pipe(tokens):
    """
    Split tokens by pipe operator.
    
    Returns: List of command segments (each segment is a list of tokens)
    
    Example:
        ["cat", "file", "|", "grep", "hello"] 
        → [["cat", "file"], ["grep", "hello"]]
    """
    commands = []
    current_command = []
    
    for token in tokens:
        if token == '|':
            if current_command:
                commands.append(current_command)
                current_command = []
        else:
            current_command.append(token)
    
    if current_command:
        commands.append(current_command)
    
    return commands


def split_redirections(tokens):
    """Split tokens that contain redirection operators."""
    result = []
    
    for token in tokens:
        if '2>>' in token:
            idx = token.index('2>>')
            before = token[:idx]
            after = token[idx + 3:]
            if before:
                result.append(before)
            result.append('2>>')
            if after:
                result.append(after)
        elif '1>>' in token:
            idx = token.index('1>>')
            before = token[:idx]
            after = token[idx + 3:]
            if before:
                result.append(before)
            result.append('1>>')
            if after:
                result.append(after)
        elif '>>' in token:
            idx = token.index('>>')
            before = token[:idx]
            after = token[idx + 2:]
            if before:
                result.append(before)
            result.append('>>')
            if after:
                result.append(after)
        elif '2>' in token:
            idx = token.index('2>')
            before = token[:idx]
            after = token[idx + 2:]
            if before:
                result.append(before)
            result.append('2>')
            if after:
                result.append(after)
        elif '1>' in token:
            idx = token.index('1>')
            before = token[:idx]
            after = token[idx + 2:]
            if before:
                result.append(before)
            result.append('1>')
            if after:
                result.append(after)
        elif '>' in token:
            idx = token.index('>')
            before = token[:idx]
            after = token[idx + 1:]
            if before:
                result.append(before)
            result.append('>')
            if after:
                result.append(after)
        # Handle pipe operator
        elif '|' in token:
            idx = token.index('|')
            before = token[:idx]
            after = token[idx + 1:]
            if before:
                result.append(before)
            result.append('|')
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
        full_path = os.path.join(directory, command_name)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    return None


def get_executables_in_path(path_directories):
    """Get all executable files in PATH directories."""
    executables = set()
    
    for directory in path_directories:
        if not os.path.isdir(directory):
            continue
        
        try:
            for filename in os.listdir(directory):
                full_path = os.path.join(directory, filename)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    executables.add(filename)
        except PermissionError:
            continue
        except Exception:
            continue
    
    return executables


def execute_pipeline(pipeline_commands, path_directories):
    """
    Execute a pipeline of commands.
    
    Args:
        pipeline_commands: List of command lists
            Example: [["cat", "file"], ["grep", "hello"], ["wc", "-l"]]
    """
    if not pipeline_commands:
        return
    
    # Single command - no pipeline
    if len(pipeline_commands) == 1:
        command_tokens, stdout_file, stdout_append, stderr_file, stderr_append = parse_command_with_redirection(' '.join(pipeline_commands[0]))
        execute_single_command(command_tokens, path_directories, stdout_file, stdout_append, stderr_file, stderr_append)
        return
    
    # Multiple commands - create pipeline
    processes = []
    
    for i, cmd_tokens in enumerate(pipeline_commands):
        # Parse redirection for this command
        command_tokens, stdout_file, stdout_append, stderr_file, stderr_append = parse_command_with_redirection(' '.join(cmd_tokens))
        
        if not command_tokens:
            continue
        
        command_name = command_tokens[0]
        
        # Find executable
        executable_path = find_executable_in_path(command_name, path_directories)
        
        if not executable_path:
            print(f"{command_name}: command not found")
            # Clean up any previous processes
            for proc in processes:
                try:
                    proc.kill()
                except:
                    pass
            return
        
        # Determine stdin
        if i == 0:
            # First command: stdin from terminal
            stdin_source = None
        else:
            # Middle/last command: stdin from previous command
            stdin_source = processes[i - 1].stdout
        
        # Determine stdout
        if i == len(pipeline_commands) - 1:
            # Last command
            if stdout_file:
                mode = 'a' if stdout_append else 'w'
                stdout_dest = open(stdout_file, mode)
            else:
                stdout_dest = None  # Terminal
        else:
            # Not last command: pipe to next
            stdout_dest = subprocess.PIPE
        
        # Determine stderr
        if stderr_file:
            mode = 'a' if stderr_append else 'w'
            stderr_dest = open(stderr_file, mode)
        else:
            stderr_dest = None  # Terminal
        
        # Start the process
        try:
            proc = subprocess.Popen(
                command_tokens,
                executable=executable_path,
                stdin=stdin_source,
                stdout=stdout_dest,
                stderr=stderr_dest
            )
            processes.append(proc)
            
            # Close the previous process's stdout in parent
            # This is important for proper pipe behavior
            if i > 0 and processes[i - 1].stdout:
                processes[i - 1].stdout.close()
                
        except Exception as e:
            print(f"Error executing {command_name}: {e}")
            # Clean up
            for proc in processes:
                try:
                    proc.kill()
                except:
                    pass
            return
    
    # Wait for all processes to complete
    for proc in processes:
        proc.wait()


def execute_single_command(command_tokens, path_directories, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """Execute a single command (handles both builtins and external)."""
    if not command_tokens:
        return
    
    command_name = command_tokens[0]
    arguments = command_tokens[1:]
    
    BUILTIN_COMMANDS_SET = {"echo", "type", "exit", "pwd", "cd", "history"}
    
    if command_name == "exit":
        return "EXIT"
    elif command_name == "echo":
        handle_echo_command(arguments, stdout_file, stdout_append, stderr_file, stderr_append)
    elif command_name == "pwd":
        handle_pwd_command(arguments, stdout_file, stdout_append, stderr_file, stderr_append)
    elif command_name == "cd":
        handle_cd_command(arguments, stdout_file, stdout_append, stderr_file, stderr_append)
    elif command_name == "type":
        handle_type_command(arguments, BUILTIN_COMMANDS_SET, path_directories, stdout_file, stdout_append, stderr_file, stderr_append)
    elif command_name == "history":
        handle_history_command(arguments, stdout_file, stdout_append, stderr_file, stderr_append)
    else:
        execute_external_command(command_tokens, path_directories, stdout_file, stdout_append, stderr_file, stderr_append)


def handle_echo_command(args, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """Handle the 'echo' command."""
    output = ' '.join(args) if args else ''
    
    if stderr_file:
        try:
            mode = 'a' if stderr_append else 'w'
            open(stderr_file, mode).close()
        except:
            pass
    
    if stdout_file:
        try:
            mode = 'a' if stdout_append else 'w'
            with open(stdout_file, mode) as f:
                f.write(output + '\n')
        except Exception as e:
            print(f"bash: {stdout_file}: {e}", file=sys.stderr)
    else:
        print(output)


def handle_pwd_command(args, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """Handle the 'pwd' command."""
    output = os.getcwd()
    
    if stderr_file:
        try:
            mode = 'a' if stderr_append else 'w'
            open(stderr_file, mode).close()
        except:
            pass
    
    if stdout_file:
        try:
            mode = 'a' if stdout_append else 'w'
            with open(stdout_file, mode) as f:
                f.write(output + '\n')
        except Exception as e:
            print(f"bash: {stdout_file}: {e}", file=sys.stderr)
    else:
        print(output)


def handle_cd_command(args, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """Handle the 'cd' command."""
    if stderr_file:
        try:
            mode = 'a' if stderr_append else 'w'
            stderr_handle = open(stderr_file, mode)
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


def handle_type_command(args, builtin_commands, path_directories, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """Handle the 'type' command."""
    if stderr_file:
        try:
            mode = 'a' if stderr_append else 'w'
            stderr_handle = open(stderr_file, mode)
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
            mode = 'a' if stdout_append else 'w'
            with open(stdout_file, mode) as f:
                f.write(output + '\n')
        except Exception as e:
            print(f"bash: {stdout_file}: {e}", file=sys.stderr)
    else:
        print(output)
    
    if stderr_handle:
        stderr_handle.close()


def handle_history_command(args, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """Handle the 'history' command."""
    if stderr_file:
        try:
            mode = 'a' if stderr_append else 'w'
            open(stderr_file, mode).close()
        except:
            pass
    
    if args:
        try:
            limit = int(args[0])
            entries_to_show = COMMAND_HISTORY[-limit:] if limit > 0 else []
            start_index = len(COMMAND_HISTORY) - len(entries_to_show)
        except ValueError:
            error_msg = f"history: {args[0]}: numeric argument required"
            if stdout_file:
                try:
                    mode = 'a' if stdout_append else 'w'
                    with open(stdout_file, mode) as f:
                        f.write(error_msg + '\n')
                except:
                    print(error_msg)
            else:
                print(error_msg)
            return
    else:
        entries_to_show = COMMAND_HISTORY
        start_index = 0
    
    output_lines = []
    for i, cmd in enumerate(entries_to_show, start=start_index + 1):
        output_lines.append(f"    {i}  {cmd}")
    
    output = '\n'.join(output_lines)
    
    if stdout_file:
        try:
            mode = 'a' if stdout_append else 'w'
            with open(stdout_file, mode) as f:
                if output:
                    f.write(output + '\n')
        except Exception as e:
            print(f"bash: {stdout_file}: {e}", file=sys.stderr)
    else:
        if output:
            print(output)


def execute_external_command(command_parts, path_directories, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """Execute an external command."""
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
            print(error_msg.rstrip())
    else:
        error_msg = f"{command_name}: command not found\n"
        print(error_msg.rstrip())


BUILTIN_COMMANDS = ["echo", "exit"]
PATH_DIRECTORIES = []
EXECUTABLES_CACHE = set()


def update_executables_cache():
    """Update the cache of available executables."""
    global EXECUTABLES_CACHE
    EXECUTABLES_CACHE = get_executables_in_path(PATH_DIRECTORIES)


def completer(text, state):
    """Tab completion function for readline."""
    line = readline.get_line_buffer()
    
    if line.lstrip() == text:
        all_commands = set(BUILTIN_COMMANDS) | EXECUTABLES_CACHE
        options = sorted([cmd for cmd in all_commands if cmd.startswith(text)])
        
        if state < len(options):
            return options[state] + ' '
    
    return None


def setup_readline():
    """Configure readline for tab completion."""
    readline.set_completer(completer)
    readline.parse_and_bind('tab: complete')
    readline.set_completer_delims(' \t\n')


def main():
    """Main shell loop."""
    global PATH_DIRECTORIES
    
    path_env = os.environ.get("PATH", "")
    PATH_DIRECTORIES = path_env.split(os.pathsep)
    
    update_executables_cache()
    setup_readline()
    
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()
        
        try:
            user_input = input()
        except EOFError:
            print()
            break
        
        COMMAND_HISTORY.append(user_input)
        
        # Parse tokens
        tokens = parse_command_with_quotes(user_input.strip())
        if not tokens:
            continue
        
        # Split tokens by redirection operators
        tokens = split_redirections(tokens)
        
        # Split by pipes
        pipeline_commands = split_by_pipe(tokens)
        
        # Execute pipeline
        result = execute_pipeline(pipeline_commands, PATH_DIRECTORIES)
        
        if result == "EXIT":
            break


if __name__ == "__main__":
    main()