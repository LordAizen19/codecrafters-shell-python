<p align="center">
  <img src="https://app.codecrafters.io/assets/7408d202b2bb110054fc.svg" alt="CodeCrafters" width="120" />
</p>

# Build Your Own Shell — Python

A Unix-like shell implementation in Python, built as part of the CodeCrafters "Build Your Own Shell" challenge.

## Current Stage

The latest completed stage adds support for `history` as a shell builtin.

The next stage is `listing history`.

## Overview

This project implements an interactive shell with parsing, built-ins, external command execution, redirections, pipelines, command history, and tab completion. The shell follows Unix-like behavior for common commands and supports mixed built-in and external commands in pipelines.

## Implemented Features

- Interactive REPL prompt (`$ `)
- Built-in commands: `echo`, `exit`, `pwd`, `cd`, `type`, `history`
- External command lookup through `PATH`
- Quote-aware command tokenization:
  - single quotes (`'...'`)
  - double quotes (`"..."`)
  - escape handling with backslashes
- Output redirection support:
  - stdout: `>`, `1>`, `>>`, `1>>`
  - stderr: `2>`, `2>>`
- Pipeline support with `|`
- Mixed pipelines with built-ins and external commands
- Command history tracking with `history`
- Command tab completion (built-ins + executables from `PATH`)

## How Parsing Works

The parser processes input in stages:

1. Tokenize with quote and escape awareness (`parse_command_with_quotes`)
2. Split inline redirection operators from tokens (`split_redirections`)
3. Detect and split pipelines (`split_pipes`)
4. Extract redirection targets for non-pipeline commands (`parse_command_with_redirection`)

Quote parsing uses a state machine with `quote_state` (`None`, `SINGLE`, `DOUBLE`) and `escape_next` to correctly preserve literals and spaces inside quotes.

## Code Example

```python
def parse_command_with_redirection(command_string):
    tokens = parse_command_with_quotes(command_string.strip())
    if not tokens:
        return [], None, False, None, False, []

    tokens = split_redirections(tokens)

    if '|' in tokens:
        pipeline_commands = split_pipes(tokens)
        return [], None, False, None, False, pipeline_commands

    # parse stdout/stderr redirections from tokens
    # and return command tokens + redirection metadata
```

## Supported Commands

- `echo [args...]`
- `pwd`
- `cd [path]`
- `type <command>`
- `history`
- `exit`

If the command is not a built-in, the shell searches executable files in `PATH` and runs the first match.

## Redirection and Pipeline Examples

```bash
echo "hello world" > out.txt
echo "append" >> out.txt
ls /not-found 2> err.txt
cat file.txt | grep foo | wc -l
echo "hi" | wc -c
```

## Tab Completion

Tab completion is implemented with `readline` and supports:

- Built-in command names
- Executables discovered from `PATH`
- Longest common prefix completion for multiple matches
- Double-tab listing of all matching options

## Running the Program

The shell can be started using:

```bash
./your_program.sh
```

## Challenges Faced

Implementing shell behavior required handling multiple edge cases cleanly:

- Correct quote/escape parsing without breaking token boundaries
- Splitting redirection operators when attached to tokens (for example `echo>file`)
- Running built-ins inside pipelines while preserving shell process state
- Avoiding pipeline deadlocks by closing the correct pipe file descriptors
- Coordinating redirection behavior for stdout and stderr

The implementation solves this with clear parser stages and careful file descriptor management for pipeline execution.

## Next Steps

- Complete the `listing history` stage behavior
- Add argument-level completion and filename/path completion
- Improve error messages for malformed redirection syntax
- Add support for more shell features (for example `;`, `&&`, environment variable expansion)
