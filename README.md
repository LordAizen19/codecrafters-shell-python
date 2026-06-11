<p align="center">
  <img src="https://app.codecrafters.io/assets/7408d202b2bb110054fc.svg" alt="CodeCrafters" width="120" />
</p>

# Build Your Own Shell — Python

A fully-functional Unix-like shell implementation in Python, built as part of the CodeCrafters "Build Your Own Shell" challenge.

## What This Project Does

This is an interactive shell that mimics core Unix shell behavior. It parses and executes commands, handles I/O redirection, supports pipelines, maintains command history, and provides tab completion—all implemented from scratch in Python without relying on shell libraries.

## Features

- **Interactive REPL** with Unix-style prompt (`$ `)
- **Built-in Commands**: `echo`, `exit`, `pwd`, `cd`, `type`, `history`
- **External Command Execution** via `PATH` lookup
- **Quote & Escape Handling**: 
  - Single quotes (`'...'`) for literal strings
  - Double quotes (`"..."`) for interpreted strings
  - Backslash escape sequences
- **I/O Redirection**:
  - Stdout: `>`, `1>`, `>>`, `1>>`
  - Stderr: `2>`, `2>>`
  - Combined redirect support
- **Pipeline Support**: Chain commands with `|` (e.g., `cat file.txt | grep foo | wc -l`)
- **Command History**: Access and list previously run commands
- **Tab Completion**: Auto-complete built-ins and executables from `PATH`

## Technologies Used

- **Language**: Python 3
- **Core Libraries**:
  - `readline` — tab completion and history
  - `os` — file system and process management
  - `subprocess` — external command execution
  - `sys` — exit and I/O handling
- **Key Concepts**:
  - State machine parsing for quote/escape handling
  - File descriptor management for pipes
  - Process forking and redirection with `subprocess.Popen()`

## How to Run It

### Prerequisites
- Python 3.6+
- Unix-like environment (Linux, macOS, WSL)

### Running the Shell

```bash
./your_program.sh
```

Or directly with Python:

```bash
python3 app/main.py
```

### Example Commands

```bash
$ echo "Hello, World!"
Hello, World!

$ pwd
/home/user/projects/shell

$ echo "test" > output.txt

$ cat file.txt | grep pattern | wc -l
42

$ history
1  echo "Hello, World!"
2  pwd
3  echo "test" > output.txt

$ cd /tmp
$ type ls
ls is /bin/ls
```

## What I Learned

### 1. **Parsing Complexity**
   - Quote and escape handling requires careful state machine design
   - Operators can be inline with tokens (e.g., `echo>file`) and must be split correctly
   - Multi-stage parsing is cleaner than trying to handle everything at once

### 2. **Process Management**
   - File descriptor handling is critical—unclosed pipes cause deadlocks
   - `subprocess.Popen()` gives fine-grained control over stdin/stdout/stderr
   - Proper cleanup of child processes prevents zombie processes

### 3. **Pipeline Architecture**
   - Pipelines chain processes by connecting stdout of one to stdin of the next
   - Built-ins running inside pipelines need special handling to avoid forking the shell
   - Buffering and I/O blocking can cause deadlocks without careful coordination

### 4. **Shell Behavior Edge Cases**
   - Exit codes must propagate correctly through pipelines
   - Redirections have precedence and order matters
   - Built-in commands like `cd` must modify the shell's own state, not a subprocess

### 5. **User Experience**
   - `readline` library provides familiar shell history and tab completion
   - Longest common prefix matching for completions feels natural
   - Clear separation between builtin and external commands improves maintainability

## Next Steps

- Complete the `listing history` stage behavior
- Add support for argument-level and filename completion
- Implement command operators (`;`, `&&`, `||`)
- Add environment variable expansion (`$VAR` syntax)
- Improve error messages for malformed syntax
