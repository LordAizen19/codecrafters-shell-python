import sys
import os
import subprocess
import readline


def parse_command_with_quotes(command_string):
    r"""
    Parse a command string while handling quotes and escape sequences.
    
    This function tokenizes a command string according to shell quoting rules:
    - Single quotes: Everything inside is treated literally (no escaping)
    - Double quotes: Only backslashes before \ and " are escape sequences
    - Outside quotes: Backslash escapes the next character
    - Whitespace outside quotes separates tokens
    
    Args:
        command_string (str): The raw command string to parse
        
    Returns:
        list[str]: List of parsed tokens/arguments
        
    Examples:
        >>> parse_command_with_quotes('echo "hello world"')
        ['echo', 'hello world']
        
        >>> parse_command_with_quotes("echo 'test\\'s'")
        ['echo', "test\\'s"]
        
        >>> parse_command_with_quotes('echo "test\\\\"')
        ['echo', 'test\\']
    
    Note:
        This function does NOT handle redirection operators or pipes.
        Those are processed in a separate step.
    """
    arguments = []
    current_argument = ""
    quote_state = None  # Tracks quote context: None, 'SINGLE', or 'DOUBLE'
    escape_next = False  # True when previous character was an unprocessed backslash
    
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
                # Outside quotes: add the escaped character as-is
                current_argument += char
            escape_next = False
            continue
        
        # STEP 2: Handle backslash (potential escape character)
        if char == '\\':
            if quote_state == 'SINGLE':
                # Inside single quotes: backslash is literal (no escaping)
                current_argument += char
            else:
                # Outside quotes or inside double quotes: next char might be escaped
                escape_next = True
            continue
        
        # STEP 3: Handle single quotes (start/end single-quote mode)
        if char == "'":
            if quote_state is None:
                # Start single-quote mode
                quote_state = 'SINGLE'
            elif quote_state == 'SINGLE':
                # End single-quote mode
                quote_state = None
            else:
                # Inside double quotes: single quote is literal
                current_argument += char
            continue
        
        # STEP 4: Handle double quotes (start/end double-quote mode)
        if char == '"':
            if quote_state is None:
                # Start double-quote mode
                quote_state = 'DOUBLE'
            elif quote_state == 'DOUBLE':
                # End double-quote mode
                quote_state = None
            else:
                # Inside single quotes: double quote is literal
                current_argument += char
            continue
        
        # STEP 5: Handle whitespace (token separator when not quoted)
        if char in (' ', '\t'):
            if quote_state is not None:
                # Inside quotes: preserve whitespace as part of the token
                current_argument += char
            else:
                # Outside quotes: whitespace ends the current token
                if current_argument:
                    arguments.append(current_argument)
                    current_argument = ""
            continue
        
        # STEP 6: Regular characters (letters, digits, symbols)
        current_argument += char
    
    # Handle trailing backslash (edge case: command ends with \)
    if escape_next and quote_state != 'DOUBLE':
        current_argument += '\\'
    
    # Don't forget to add the last token if it exists
    if current_argument:
        arguments.append(current_argument)
    
    return arguments


def split_redirections(tokens):
    """
    Split tokens that contain redirection operators into separate tokens.
    
    This function handles cases where redirection operators are concatenated
    with filenames or commands (e.g., "echo>file" becomes ["echo", ">", "file"]).
    
    Redirection operators must be checked in order from longest to shortest
    to avoid incorrect matches (e.g., check ">>" before ">").
    
    Args:
        tokens (list[str]): List of tokens that may contain redirection operators
        
    Returns:
        list[str]: List of tokens with redirections split out
        
    Examples:
        >>> split_redirections(['echo>file'])
        ['echo', '>', 'file']
        
        >>> split_redirections(['cat', 'file>>output'])
        ['cat', 'file', '>>', 'output']
    
    Supported operators (in check order):
        - 2>> : Append stderr
        - 1>> : Append stdout
        - >>  : Append stdout (shorthand)
        - 2>  : Redirect stderr
        - 1>  : Redirect stdout
        - >   : Redirect stdout (shorthand)
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
            # No redirection operator in this token
            result.append(token)
    
    return result


def split_pipes(tokens):
    """
    Split a list of tokens by pipe operators into separate command lists.
    
    This function identifies pipe operators (|) and splits the token stream
    into separate commands that will be connected via pipes.
    
    Args:
        tokens (list[str]): List of tokens potentially containing pipes
        
    Returns:
        list[list[str]]: List of command token lists, one for each pipeline stage
        
    Examples:
        >>> split_pipes(['cat', 'file', '|', 'wc', '-l'])
        [['cat', 'file'], ['wc', '-l']]
        
        >>> split_pipes(['echo', 'hello', '|', 'grep', 'h', '|', 'wc'])
        [['echo', 'hello'], ['grep', 'h'], ['wc']]
    """
    commands = []
    current_command = []
    
    for token in tokens:
        if token == '|':
            # Pipe operator: save current command and start a new one
            if current_command:
                commands.append(current_command)
                current_command = []
        else:
            # Regular token: add to current command
            current_command.append(token)
    
    # Don't forget the last command after the final token
    if current_command:
        commands.append(current_command)
    
    return commands


def parse_command_with_redirection(command_string):
    """
    Parse a command string and extract command tokens and redirection information.
    
    This is the main parsing function that orchestrates quote parsing,
    redirection splitting, and pipeline detection.
    
    Args:
        command_string (str): The raw command string from user input
        
    Returns:
        tuple: A 6-element tuple containing:
            - command_tokens (list[str]): Command and its arguments (empty if pipeline)
            - stdout_file (str|None): File to redirect stdout to
            - stdout_append (bool): True for >>, False for >
            - stderr_file (str|None): File to redirect stderr to
            - stderr_append (bool): True for 2>>, False for 2>
            - pipeline_commands (list[list[str]]): List of commands if pipeline (empty otherwise)
    
    Examples:
        >>> parse_command_with_redirection('echo hello > output.txt')
        (['echo', 'hello'], 'output.txt', False, None, False, [])
        
        >>> parse_command_with_redirection('cat file | wc -l')
        ([], None, False, None, False, [['cat', 'file'], ['wc', '-l']])
    """
    # Step 1: Parse quotes and escape sequences
    tokens = parse_command_with_quotes(command_string.strip())
    
    if not tokens:
        # Empty command
        return [], None, False, None, False, []
    
    # Step 2: Split redirection operators from adjacent tokens
    tokens = split_redirections(tokens)
    
    # Step 3: Check if this is a pipeline
    if '|' in tokens:
        # Split by pipes and return pipeline commands
        pipeline_commands = split_pipes(tokens)
        # Return empty command_tokens since this is a pipeline
        return [], None, False, None, False, pipeline_commands
    
    # Step 4: Extract redirection information (non-pipeline case)
    stdout_file = None
    stdout_append = False
    stderr_file = None
    stderr_append = False
    
    i = 0
    command_tokens = []
    
    while i < len(tokens):
        token = tokens[i]
        
        # Check for stdout append redirections
        if token in ('>>', '1>>'):
            if i + 1 < len(tokens):
                stdout_file = tokens[i + 1]
                stdout_append = True
                i += 2  # Skip both operator and filename
            else:
                i += 1  # Skip lone operator
                
        # Check for stdout redirections
        elif token in ('>', '1>'):
            if i + 1 < len(tokens):
                stdout_file = tokens[i + 1]
                stdout_append = False
                i += 2
            else:
                i += 1
                
        # Check for stderr append redirection
        elif token == '2>>':
            if i + 1 < len(tokens):
                stderr_file = tokens[i + 1]
                stderr_append = True
                i += 2
            else:
                i += 1
                
        # Check for stderr redirection
        elif token == '2>':
            if i + 1 < len(tokens):
                stderr_file = tokens[i + 1]
                stderr_append = False
                i += 2
            else:
                i += 1
        else:
            # Regular token: part of the command
            command_tokens.append(token)
            i += 1
    
    # Return command with redirection info, empty pipeline
    return command_tokens, stdout_file, stdout_append, stderr_file, stderr_append, []


def find_executable_in_path(command_name, path_directories):
    """
    Search for an executable file in the PATH directories.
    
    This function mimics shell behavior for locating executable commands
    by searching through directories in the PATH environment variable.
    
    Args:
        command_name (str): Name of the command to find (e.g., 'ls', 'cat')
        path_directories (list[str]): List of directory paths to search
        
    Returns:
        str|None: Full path to the executable if found, None otherwise
        
    Examples:
        >>> find_executable_in_path('ls', ['/bin', '/usr/bin'])
        '/bin/ls'  # (if ls exists in /bin)
        
        >>> find_executable_in_path('nonexistent', ['/bin'])
        None
    
    Note:
        - Skips non-existent directories gracefully
        - Checks both that the file exists AND is executable
        - Returns the first match found
    """
    for directory in path_directories:
        # Skip non-existent directories (PATH may contain invalid entries)
        if not os.path.isdir(directory):
            continue
            
        # Construct full path to potential executable
        full_path = os.path.join(directory, command_name)
        
        # Check if it's a file AND executable
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    
    # Not found in any directory
    return None


def get_executables_in_path(path_directories):
    """
    Get a set of all executable file names available in PATH directories.
    
    This function is used to build a cache of available executables for
    tab completion functionality.
    
    Args:
        path_directories (list[str]): List of directory paths to scan
        
    Returns:
        set[str]: Set of executable file names (not full paths)
        
    Examples:
        >>> get_executables_in_path(['/bin', '/usr/bin'])
        {'ls', 'cat', 'grep', 'sed', ...}
    
    Note:
        - Handles non-existent directories gracefully
        - Catches and ignores permission errors
        - Returns file names only, not full paths
        - Uses a set to automatically deduplicate names
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
                
                # Check if it's a regular file and executable
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    executables.add(filename)
        except PermissionError:
            # Skip directories we can't read (e.g., /root)
            continue
        except Exception:
            # Skip any other errors (corrupted filesystem, etc.)
            continue
    
    return executables


def handle_exit_command(args, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """
    Handle the 'exit' built-in command.
    
    The exit command terminates the shell. In non-pipeline contexts, this
    causes the main loop to break and the program to exit.
    
    Args:
        args (list[str]): Arguments passed to exit (currently unused)
        stdout_file (str|None): Stdout redirection file (unused for exit)
        stdout_append (bool): Whether to append to stdout file
        stderr_file (str|None): Stderr redirection file
        stderr_append (bool): Whether to append to stderr file
        
    Returns:
        bool: True to indicate the shell should exit
        
    Note:
        If stderr redirection is specified, an empty file is created/truncated.
        This handles edge cases like "exit 2> file".
    """
    # Create empty stderr file if specified (edge case handling)
    if stderr_file:
        try:
            mode = 'a' if stderr_append else 'w'
            with open(stderr_file, mode):
                pass  # Just create/truncate the file
        except:
            pass  # Ignore file creation errors
    
    return True  # Signal to caller that shell should exit


def handle_echo_command(args, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """
    Handle the 'echo' built-in command.
    
    Echo prints its arguments to stdout, separated by spaces, followed by
    a newline. This implementation supports output redirection.
    
    Args:
        args (list[str]): Arguments to echo
        stdout_file (str|None): File to redirect output to
        stdout_append (bool): If True, append to file; if False, overwrite
        stderr_file (str|None): Stderr redirection file (creates empty file)
        stderr_append (bool): Whether to append to stderr file
        
    Examples:
        >>> handle_echo_command(['hello', 'world'])
        hello world
        
        >>> handle_echo_command(['test'], stdout_file='output.txt', stdout_append=False)
        # Writes "test\n" to output.txt
    """
    # Join arguments with spaces (or empty string if no args)
    output = ' '.join(args) if args else ''
    
    # Create empty stderr file if specified (edge case handling)
    if stderr_file:
        try:
            mode = 'a' if stderr_append else 'w'
            with open(stderr_file, mode):
                pass
        except:
            pass
    
    # Handle stdout redirection
    if stdout_file:
        try:
            mode = 'a' if stdout_append else 'w'
            with open(stdout_file, mode) as f:
                f.write(output + '\n')
        except Exception as e:
            # Error opening output file - report to stderr
            error_msg = f"bash: {stdout_file}: {e}\n"
            if stderr_file:
                try:
                    mode = 'a' if stderr_append else 'w'
                    with open(stderr_file, mode) as f:
                        f.write(error_msg)
                except:
                    print(error_msg.rstrip(), file=sys.stderr)
            else:
                print(error_msg.rstrip(), file=sys.stderr)
    else:
        # No redirection - print to terminal
        print(output)


def handle_pwd_command(args, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """
    Handle the 'pwd' built-in command.
    
    PWD (Print Working Directory) displays the current working directory's
    absolute path.
    
    Args:
        args (list[str]): Arguments passed to pwd (typically ignored)
        stdout_file (str|None): File to redirect output to
        stdout_append (bool): If True, append to file; if False, overwrite
        stderr_file (str|None): Stderr redirection file
        stderr_append (bool): Whether to append to stderr file
        
    Examples:
        >>> handle_pwd_command([])
        /home/user/current/directory
    """
    # Get current working directory
    output = os.getcwd()
    
    # Create empty stderr file if specified
    if stderr_file:
        try:
            mode = 'a' if stderr_append else 'w'
            with open(stderr_file, mode):
                pass
        except:
            pass
    
    # Handle stdout redirection
    if stdout_file:
        try:
            mode = 'a' if stdout_append else 'w'
            with open(stdout_file, mode) as f:
                f.write(output + '\n')
        except Exception as e:
            error_msg = f"bash: {stdout_file}: {e}\n"
            if stderr_file:
                try:
                    mode = 'a' if stderr_append else 'w'
                    with open(stderr_file, mode) as f:
                        f.write(error_msg)
                except:
                    print(error_msg.rstrip(), file=sys.stderr)
            else:
                print(error_msg.rstrip(), file=sys.stderr)
    else:
        # No redirection - print to terminal
        print(output)


def handle_cd_command(args, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """
    Handle the 'cd' built-in command.
    
    CD (Change Directory) changes the shell's current working directory.
    This must be a built-in because it affects the shell process itself;
    an external command would only change its own directory.
    
    Args:
        args (list[str]): Directory arguments (first arg is target directory)
        stdout_file (str|None): Stdout redirection (unused for cd)
        stdout_append (bool): Whether to append to stdout file
        stderr_file (str|None): File to redirect error messages to
        stderr_append (bool): Whether to append to stderr file
        
    Behavior:
        - No args: Change to home directory (~)
        - Relative path: Relative to current directory
        - Absolute path: Use as-is
        - Tilde paths: Expand ~ to home directory
        
    Examples:
        >>> handle_cd_command([])  # Go to home directory
        >>> handle_cd_command(['/tmp'])  # Go to /tmp
        >>> handle_cd_command(['..'])  # Go up one directory
        >>> handle_cd_command(['~/Documents'])  # Go to home/Documents
    """
    stderr_handle = None
    
    # Open stderr file if redirection specified
    if stderr_file:
        try:
            mode = 'a' if stderr_append else 'w'
            stderr_handle = open(stderr_file, mode)
        except:
            stderr_handle = None
    
    # Determine target directory
    if not args:
        # No arguments: go to home directory
        target_directory = os.path.expanduser("~")
    else:
        target_directory = args[0]
        
        if target_directory.startswith("~"):
            # Expand tilde to home directory
            target_directory = os.path.expanduser(target_directory)
        elif not target_directory.startswith("/"):
            # Relative path: join with current directory
            target_directory = os.path.join(os.getcwd(), target_directory)
    
    # Attempt to change directory
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
    
    # Clean up stderr file handle
    if stderr_handle:
        stderr_handle.close()


def handle_type_command(args, builtin_commands, path_directories, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """
    Handle the 'type' built-in command.
    
    Type displays information about how a command name would be interpreted:
    - Built-in command: "X is a shell builtin"
    - External command: "X is /path/to/X"
    - Not found: "X: not found"
    
    Args:
        args (list[str]): Command names to check
        builtin_commands (set[str]): Set of built-in command names
        path_directories (list[str]): PATH directories to search
        stdout_file (str|None): File to redirect output to
        stdout_append (bool): Whether to append to stdout file
        stderr_file (str|None): File to redirect errors to
        stderr_append (bool): Whether to append to stderr file
        
    Examples:
        >>> handle_type_command(['echo'], {'echo', 'cd'}, ['/bin'])
        echo is a shell builtin
        
        >>> handle_type_command(['ls'], {'echo'}, ['/bin'])
        ls is /bin/ls
    """
    stderr_handle = None
    
    # Open stderr file if redirection specified
    if stderr_file:
        try:
            mode = 'a' if stderr_append else 'w'
            stderr_handle = open(stderr_file, mode)
        except:
            stderr_handle = None
    
    # Check if command name was provided
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
    
    # Determine command type and generate output
    if command_name in builtin_commands:
        output = f"{command_name} is a shell builtin"
    else:
        executable_path = find_executable_in_path(command_name, path_directories)
        if executable_path:
            output = f"{command_name} is {executable_path}"
        else:
            output = f"{command_name}: not found"
    
    # Handle stdout redirection
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
        # No redirection - print to terminal
        print(output)
    
    # Clean up stderr file handle
    if stderr_handle:
        stderr_handle.close()


def execute_external_command(command_parts, path_directories, stdout_file=None, stdout_append=False, stderr_file=None, stderr_append=False):
    """
    Execute an external (non-built-in) command.
    
    This function locates an executable in PATH and runs it using subprocess.
    It handles stdout and stderr redirection.
    
    Args:
        command_parts (list[str]): Command and its arguments
        path_directories (list[str]): PATH directories to search
        stdout_file (str|None): File to redirect stdout to
        stdout_append (bool): If True, append; if False, overwrite
        stderr_file (str|None): File to redirect stderr to
        stderr_append (bool): If True, append; if False, overwrite
        
    Examples:
        >>> execute_external_command(['ls', '-l'], ['/bin'])
        # Executes /bin/ls -l
        
        >>> execute_external_command(['cat', 'file'], ['/bin'], stdout_file='out.txt')
        # Executes /bin/cat file > out.txt
    
    Note:
        Uses subprocess.run() with the 'executable' parameter to ensure
        the correct binary is executed even if argv[0] differs.
    """
    command_name = command_parts[0]
    
    # Locate the executable in PATH
    executable_path = find_executable_in_path(command_name, path_directories)
    
    if executable_path:
        try:
            stdout_handle = None
            stderr_handle = None
            
            # Open stdout redirection file if specified
            if stdout_file:
                mode = 'a' if stdout_append else 'w'
                stdout_handle = open(stdout_file, mode)
            
            # Open stderr redirection file if specified
            if stderr_file:
                mode = 'a' if stderr_append else 'w'
                stderr_handle = open(stderr_file, mode)
            
            # Execute the command with subprocess
            # executable: actual binary path
            # command_parts: argv passed to the program
            subprocess.run(
                command_parts,
                executable=executable_path,
                stdout=stdout_handle,
                stderr=stderr_handle
            )
            
            # Clean up file handles
            if stdout_handle:
                stdout_handle.close()
            if stderr_handle:
                stderr_handle.close()
                
        except Exception as e:
            # Error executing the command
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
        # Command not found in PATH
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


def execute_builtin_in_pipeline(command_parts, builtin_commands_set, path_directories, stdin_fd=None, stdout_fd=None):
    """
    Execute a built-in command within a pipeline context.
    
    Built-in commands must run in the shell process (not forked), but when
    they're part of a pipeline, their I/O needs to be redirected to/from pipes.
    This function temporarily redirects the shell's stdin/stdout to pipe
    file descriptors, executes the built-in, then restores the original I/O.
    
    Args:
        command_parts (list[str]): Command and its arguments
        builtin_commands_set (set[str]): Set of built-in command names
        path_directories (list[str]): PATH directories (for 'type' command)
        stdin_fd (int|None): File descriptor to use as stdin (None = keep current)
        stdout_fd (int|None): File descriptor to use as stdout (None = keep current)
        
    Process:
        1. Save current stdin (fd 0) and stdout (fd 1)
        2. Redirect stdin/stdout to provided pipe file descriptors
        3. Execute the built-in command (it writes to redirected stdout)
        4. Restore original stdin/stdout
        
    Examples:
        >>> # In pipeline: echo hello | grep h
        >>> # When executing 'echo hello' (builtin):
        >>> execute_builtin_in_pipeline(['echo', 'hello'], {'echo'}, [], 
        ...                            stdin_fd=None, stdout_fd=pipe_write_fd)
        # echo writes "hello" to the pipe instead of terminal
    
    Note:
        The try/finally ensures stdin/stdout are always restored, even if
        the built-in command raises an exception.
    """
    if not command_parts:
        return
    
    command_name = command_parts[0]
    arguments = command_parts[1:]
    
    # Save original stdin/stdout by duplicating them to new file descriptors
    # This is crucial because we need to restore them after the builtin executes
    orig_stdin = os.dup(0)   # Duplicate stdin (fd 0)
    orig_stdout = os.dup(1)  # Duplicate stdout (fd 1)
    
    try:
        # Redirect stdin to read from pipe (if specified)
        if stdin_fd is not None:
            os.dup2(stdin_fd, 0)  # Make fd 0 point to the pipe
        
        # Redirect stdout to write to pipe (if specified)
        if stdout_fd is not None:
            os.dup2(stdout_fd, 1)  # Make fd 1 point to the pipe
        
        # Execute the built-in command
        # It will now read from/write to the pipes instead of terminal
        if command_name == "echo":
            handle_echo_command(arguments)
        elif command_name == "pwd":
            handle_pwd_command(arguments)
        elif command_name == "cd":
            handle_cd_command(arguments)
        elif command_name == "type":
            handle_type_command(arguments, builtin_commands_set, path_directories)
        elif command_name == "exit":
            # Exit in a pipeline shouldn't exit the shell
            pass
    finally:
        # Always restore original stdin/stdout
        # This is critical - without this, the shell's I/O would be broken
        os.dup2(orig_stdin, 0)   # Restore stdin
        os.dup2(orig_stdout, 1)  # Restore stdout
        
        # Close the duplicate file descriptors (we don't need them anymore)
        os.close(orig_stdin)
        os.close(orig_stdout)


def execute_pipeline(pipeline_commands, path_directories, builtin_commands_set):
    """
    Execute a pipeline of commands (mix of built-ins and external commands).
    
    A pipeline connects the stdout of each command to the stdin of the next
    command using Unix pipes. This function handles both built-in commands
    (executed in the shell process) and external commands (executed in
    child processes).
    
    Args:
        pipeline_commands (list[list[str]]): List of command token lists
        path_directories (list[str]): PATH directories to search
        builtin_commands_set (set[str]): Set of built-in command names
        
    Pipeline Execution Process:
        1. Create N-1 pipes for N commands
        2. For each command:
           - If built-in: Execute in parent with redirected I/O
           - If external: Fork child, redirect I/O, execv
        3. Close all pipe file descriptors in parent
        4. Wait for all child processes to complete
        
    Examples:
        >>> # cat file.txt | grep pattern | wc -l
        >>> execute_pipeline([['cat', 'file.txt'], ['grep', 'pattern'], ['wc', '-l']], 
        ...                  ['/bin'], {'echo', 'type'})
        
        >>> # echo hello | wc -c (built-in piped to external)
        >>> execute_pipeline([['echo', 'hello'], ['wc', '-c']], 
        ...                  ['/usr/bin'], {'echo'})
    
    Pipe Structure:
        For 3 commands A | B | C, we create 2 pipes:
        
        A (stdout) -> pipe0 -> B (stdin)
        B (stdout) -> pipe1 -> C (stdin)
        
        pipe0 = (read_fd0, write_fd0)
        pipe1 = (read_fd1, write_fd1)
    
    Important:
        - Pipe FDs must be closed in parent after children fork
        - Built-in commands must close their pipe FDs immediately after use
        - Failure to close pipes causes deadlocks (child waits for EOF)
    """
    # Handle edge case: empty pipeline
    if not pipeline_commands:
        return
    
    # Handle edge case: single command (not actually a pipeline)
    if len(pipeline_commands) == 1:
        command_parts = pipeline_commands[0]
        if command_parts:
            command_name = command_parts[0]
            if command_name in builtin_commands_set:
                # Execute built-in without any I/O redirection
                execute_builtin_in_pipeline(command_parts, builtin_commands_set, path_directories)
            else:
                # Execute external command normally
                execute_external_command(command_parts, path_directories)
        return
    
    # Create pipes for the pipeline
    # For N commands, we need N-1 pipes
    num_pipes = len(pipeline_commands) - 1
    pipes = []
    
    for _ in range(num_pipes):
        read_fd, write_fd = os.pipe()
        pipes.append((read_fd, write_fd))
    
    # Track child processes (for external commands)
    processes = []
    
    # Execute each command in the pipeline
    for i, command_parts in enumerate(pipeline_commands):
        if not command_parts:
            continue
        
        command_name = command_parts[0]
        
        # Determine if this is a built-in or external command
        is_builtin = command_name in builtin_commands_set
        
        if is_builtin:
            # ========== BUILT-IN COMMAND PATH ==========
            # Execute in the parent process with redirected I/O
            
            # Determine which pipe FDs to use for stdin/stdout
            stdin_fd = None
            stdout_fd = None
            
            if i > 0:
                # Not the first command: read from previous pipe
                stdin_fd = pipes[i - 1][0]  # Read end of previous pipe
            
            if i < len(pipeline_commands) - 1:
                # Not the last command: write to next pipe
                stdout_fd = pipes[i][1]  # Write end of current pipe
            
            # Execute the built-in with redirected I/O
            execute_builtin_in_pipeline(command_parts, builtin_commands_set, 
                                       path_directories, stdin_fd, stdout_fd)
            
            # CRITICAL: Close the pipe FDs we just used
            # If we don't close the write end, the next command will wait forever
            if stdin_fd is not None:
                os.close(stdin_fd)
            if stdout_fd is not None:
                os.close(stdout_fd)
        else:
            # ========== EXTERNAL COMMAND PATH ==========
            # Fork a child process and execv
            
            # Find the executable
            executable_path = find_executable_in_path(command_name, path_directories)
            
            if not executable_path:
                # Command not found - abort pipeline
                print(f"{command_name}: command not found")
                
                # Clean up remaining pipes
                for j in range(i, len(pipes)):
                    read_fd, write_fd = pipes[j]
                    try:
                        os.close(read_fd)
                    except:
                        pass
                    try:
                        os.close(write_fd)
                    except:
                        pass
                
                # Wait for any already-started child processes
                for proc in processes:
                    proc.wait()
                return
            
            # Fork a new process
            pid = os.fork()
            
            if pid == 0:
                # ===== CHILD PROCESS =====
                
                # Set up stdin redirection
                if i > 0:
                    # Not the first command: read from previous pipe
                    prev_read_fd, prev_write_fd = pipes[i - 1]
                    os.dup2(prev_read_fd, 0)  # stdin = previous pipe's read end
                
                # Set up stdout redirection
                if i < len(pipeline_commands) - 1:
                    # Not the last command: write to next pipe
                    next_read_fd, next_write_fd = pipes[i]
                    os.dup2(next_write_fd, 1)  # stdout = current pipe's write end
                
                # Close ALL pipe file descriptors in child
                # Child only needs the redirected stdin/stdout, not the raw pipes
                for read_fd, write_fd in pipes:
                    os.close(read_fd)
                    os.close(write_fd)
                
                # Execute the external command
                # This replaces the child process with the new program
                try:
                    os.execv(executable_path, command_parts)
                except Exception as e:
                    print(f"Error executing {command_name}: {e}", file=sys.stderr)
                    os._exit(1)  # Exit child process on error
            else:
                # ===== PARENT PROCESS =====
                # Track the child process so we can wait for it later
                processes.append(type('Process', (), {
                    'pid': pid, 
                    'wait': lambda self: os.waitpid(self.pid, 0)
                })())
    
    # Close all remaining pipe file descriptors in parent
    # This is CRITICAL - if the parent keeps pipes open, children will hang
    for read_fd, write_fd in pipes:
        try:
            os.close(read_fd)
        except:
            pass  # May already be closed by built-in execution
        try:
            os.close(write_fd)
        except:
            pass
    
    # Wait for all child processes to complete
    for proc in processes:
        proc.wait()


# ========== TAB COMPLETION SYSTEM ==========

# Global state for tab completion
BUILTIN_COMMANDS = ["echo", "exit", "pwd", "cd", "type"]
PATH_DIRECTORIES = []
EXECUTABLES_CACHE = set()

# Track tab completion state across calls
last_completion_text = None
last_completion_options = []
tab_press_count = 0


def update_executables_cache():
    """
    Update the global cache of available executables.
    
    This function scans all PATH directories and builds a set of executable
    names for tab completion. Called once at shell startup.
    
    Side Effects:
        Updates the global EXECUTABLES_CACHE variable
    """
    global EXECUTABLES_CACHE
    EXECUTABLES_CACHE = get_executables_in_path(PATH_DIRECTORIES)


def longest_common_prefix(strings):
    """
    Find the longest common prefix of a list of strings.
    
    This is used for tab completion to determine how much of a partial
    command can be auto-completed when multiple matches exist.
    
    Args:
        strings (list[str]): List of strings to find common prefix
        
    Returns:
        str: The longest common prefix, or empty string if none
        
    Examples:
        >>> longest_common_prefix(['abc', 'abd', 'abe'])
        'ab'
        
        >>> longest_common_prefix(['hello', 'world'])
        ''
        
        >>> longest_common_prefix(['test'])
        'test'
    
    Algorithm:
        Sorts the list and compares only the first and last strings.
        Since they're lexicographically furthest apart, any prefix they
        share must be common to all strings in between.
    """
    if not strings:
        return ""
    
    if len(strings) == 1:
        return strings[0]
    
    # Sort to make comparison easier
    # Only need to compare first and last after sorting
    strings = sorted(strings)
    first = strings[0]
    last = strings[-1]
    
    # Find common prefix between first and last
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
    
    This function is called by the readline library when the user presses TAB.
    It handles completion of command names (both built-ins and executables).
    
    Completion Behavior:
        - Single match: Complete immediately with trailing space
        - Multiple matches, first TAB: Complete to longest common prefix or ring bell
        - Multiple matches, second TAB: Show all options
        - Multiple matches, third+ TAB: Ring bell
    
    Args:
        text (str): The text to complete (partial command name)
        state (int): Iteration state (0 for first call, 1+ for subsequent)
        
    Returns:
        str|None: Completion string, or None if no more completions
        
    State Tracking:
        Uses global variables to track completion state across TAB presses:
        - last_completion_text: Previous completion text
        - last_completion_options: Available options for current text
        - tab_press_count: How many times TAB was pressed for same text
    
    Examples:
        >>> # User types "ech" and presses TAB
        >>> completer("ech", 0)
        'echo '  # Single match, complete with space
        
        >>> # User types "e" and presses TAB twice
        >>> completer("e", 0)  # First TAB
        None  # Multiple matches, ring bell
        >>> completer("e", 0)  # Second TAB (same text, new call)
        None  # Shows list: "echo  exit"
    """
    global last_completion_text, last_completion_options, tab_press_count
    
    # Get the current line buffer from readline
    line = readline.get_line_buffer()
    
    # Only complete if we're at the beginning of the line (completing the command)
    # This prevents completion in the middle of arguments
    if line.lstrip() == text:
        # When state is 0, this is a new completion request
        if state == 0:
            # Combine built-in commands and PATH executables
            all_commands = set(BUILTIN_COMMANDS) | EXECUTABLES_CACHE
            
            # Find all commands that start with the given text
            options = sorted([cmd for cmd in all_commands if cmd.startswith(text)])
            
            # Check if this is a new completion or continuation of previous
            if text != last_completion_text:
                # New completion - reset state
                last_completion_text = text
                last_completion_options = options
                tab_press_count = 1
            else:
                # Same text - user pressed TAB again
                tab_press_count += 1
            
            # Handle different cases based on number of matches
            if len(options) == 0:
                # No matches - ring bell (ASCII BEL character)
                sys.stdout.write('\a')
                sys.stdout.flush()
                return None
            
            elif len(options) == 1:
                # Single match - complete it with a trailing space
                result = options[0] + ' '
                # Reset state since we completed successfully
                last_completion_text = None
                tab_press_count = 0
                return result
            
            else:
                # Multiple matches - use longest common prefix strategy
                lcp = longest_common_prefix(options)
                
                # Check if we can complete further than current text
                if len(lcp) > len(text):
                    # We can make progress by completing to LCP
                    if tab_press_count == 1:
                        # First TAB - complete to LCP (no trailing space)
                        return lcp
                    elif tab_press_count == 2:
                        # Second TAB - show all options
                        print()  # New line
                        print('  '.join(options))  # Options separated by 2 spaces
                        # Redisplay the prompt and current LCP
                        sys.stdout.write("$ " + lcp)
                        sys.stdout.flush()
                        return None
                    else:
                        # Third+ TAB - ring bell
                        sys.stdout.write('\a')
                        sys.stdout.flush()
                        return None
                else:
                    # LCP is same as current text - can't complete further
                    if tab_press_count == 1:
                        # First TAB - ring bell (no progress possible)
                        sys.stdout.write('\a')
                        sys.stdout.flush()
                        return None
                    elif tab_press_count == 2:
                        # Second TAB - show all options
                        print()
                        print('  '.join(options))
                        # Redisplay the prompt and current text
                        sys.stdout.write("$ " + text)
                        sys.stdout.flush()
                        return None
                    else:
                        # Third+ TAB - ring bell
                        sys.stdout.write('\a')
                        sys.stdout.flush()
                        return None
        else:
            # state > 0 means readline is asking for additional completions
            # We handle everything manually, so no additional completions
            return None
    else:
        # Not at the beginning - reset state
        last_completion_text = None
        last_completion_options = []
        tab_press_count = 0
        return None
    
    return None


def setup_readline():
    """
    Configure the readline library for tab completion.
    
    This function sets up the readline module to enable TAB completion
    for command names. It configures:
    - The completer function to call
    - The TAB key binding
    - The delimiter characters that separate completable tokens
    
    Called once at shell startup.
    """
    # Set our completer function
    readline.set_completer(completer)
    
    # Bind TAB key to completion
    readline.parse_and_bind('tab: complete')
    
    # Set completion delimiters (space, tab, newline)
    # This tells readline what characters separate tokens
    # We only want to complete the first word (command), not filenames
    readline.set_completer_delims(' \t\n')


def main():
    """
    Main shell loop (REPL - Read-Eval-Print Loop).
    
    This is the entry point and main control flow of the shell.
    
    Initialization:
        1. Parse PATH environment variable
        2. Build cache of available executables
        3. Set up readline for tab completion
    
    Main Loop:
        1. Display prompt ("$ ")
        2. Read user input
        3. Parse command (quotes, redirections, pipes)
        4. Execute command (built-in or external, single or pipeline)
        5. Repeat until 'exit' or EOF
    
    Command Execution Flow:
        - Pipeline: Call execute_pipeline()
        - Built-in: Call appropriate handle_*_command()
        - External: Call execute_external_command()
    """
    global PATH_DIRECTORIES, last_completion_text, tab_press_count
    
    # Initialize PATH directories from environment
    path_env = os.environ.get("PATH", "")
    PATH_DIRECTORIES = path_env.split(os.pathsep)
    
    # Build cache of available executables for tab completion
    update_executables_cache()
    
    # Set up readline for tab completion
    setup_readline()
    
    # Set of built-in command names
    BUILTIN_COMMANDS_SET = {"echo", "type", "exit", "pwd", "cd"}
    
    # Main REPL loop
    while True:
        # Reset tab completion state at each new prompt
        # This prevents TAB state from persisting across commands
        last_completion_text = None
        tab_press_count = 0
        
        # Display prompt
        sys.stdout.write("$ ")
        sys.stdout.flush()
        
        # Read user input
        try:
            user_input = input()
        except EOFError:
            # User pressed Ctrl+D - exit gracefully
            print()  # Print newline for clean exit
            break
        
        # Parse the command (handles quotes, redirections, pipes)
        command_tokens, stdout_file, stdout_append, stderr_file, stderr_append, pipeline_commands = parse_command_with_redirection(user_input)
        
        # Check if this is a pipeline
        if pipeline_commands:
            # Execute pipeline (may contain mix of built-ins and external commands)
            execute_pipeline(pipeline_commands, PATH_DIRECTORIES, BUILTIN_COMMANDS_SET)
            continue
        
        # Skip empty commands
        if not command_tokens:
            continue
        
        # Extract command name and arguments
        command_name = command_tokens[0]
        arguments = command_tokens[1:]
        
        # Execute built-in commands
        if command_name == "exit":
            should_exit = handle_exit_command(arguments, stdout_file, stdout_append, stderr_file, stderr_append)
            if should_exit:
                break  # Exit the main loop
        elif command_name == "echo":
            handle_echo_command(arguments, stdout_file, stdout_append, stderr_file, stderr_append)
        elif command_name == "pwd":
            handle_pwd_command(arguments, stdout_file, stdout_append, stderr_file, stderr_append)
        elif command_name == "cd":
            handle_cd_command(arguments, stdout_file, stdout_append, stderr_file, stderr_append)
        elif command_name == "type":
            handle_type_command(arguments, BUILTIN_COMMANDS_SET, PATH_DIRECTORIES, stdout_file, stdout_append, stderr_file, stderr_append)
        else:
            # Not a built-in - execute as external command
            execute_external_command(command_tokens, PATH_DIRECTORIES, stdout_file, stdout_append, stderr_file, stderr_append)


# Entry point - run main loop when script is executed
if __name__ == "__main__":
    main()