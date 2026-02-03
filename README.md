<p align="center">
  <img src="file:///home/ichigoat/Desktop/Python-Projects/Images/logo.png" alt="CodeCrafters" width="120" />
</p>

# Build Your Own Shell — Python

A Unix-like shell implementation in Python, built as part of the CodeCrafters "Build Your Own Shell" challenge.

## Overview

This project implements a basic shell with command parsing and quote handling. The current completed stage focuses on double-quote parsing, building on previous work with single quotes. The parser correctly handles both single and double quotes, preserving spaces within quotes and concatenating adjacent quoted strings.

## Implemented Features

- Command tokenization
- Single-quote handling
- Double-quote handling
- Preserving spaces inside quotes
- Concatenation of adjacent quoted strings
- Character-by-character parsing with state tracking

## How Quote Parsing Works

The parser uses a state machine approach to handle both single and double quotes:

- A `quote_state` variable tracks the current parsing context: `None`, `'SINGLE'`, or `'DOUBLE'`
- When encountering a quote character:
  - If outside any quotes, enter the corresponding quote state
  - If inside the matching quote type, exit that state
  - If inside a different quote type, treat the character as literal
- Whitespace behavior depends on the quote state:
  - Inside quotes: whitespace is preserved as part of the token
  - Outside quotes: whitespace separates tokens
- Adjacent quoted and unquoted segments without separating whitespace are concatenated into a single token

This state-based parsing ensures correct handling of nested quote scenarios like `echo "shell's test"` or `echo 'say "hello"'`.

## Code Example

```python
def parse_command_with_quotes(command_string):
    """
    Parse command string, handling both single and double quotes.
    
    Examples:
        echo "hello world" → ["echo", "hello world"]
        echo 'hello' "world" → ["echo", "hello", "world"]
        echo "shell's test" → ["echo", "shell's test"]
        echo "hello""world" → ["echo", "helloworld"]
    """
    arguments = []
    current_argument = ""
    quote_state = None  # Can be: None, 'SINGLE', or 'DOUBLE'
    
    for char in command_string:
        if char == "'":
            if quote_state is None:
                quote_state = 'SINGLE'
            elif quote_state == 'SINGLE':
                quote_state = None
            else:
                current_argument += char
        
        elif char == '"':
            if quote_state is None:
                quote_state = 'DOUBLE'
            elif quote_state == 'DOUBLE':
                quote_state = None
            else:
                current_argument += char
        
        elif char in (' ', '\t'):
            if quote_state is not None:
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
```

## Running the Program

The shell can be started using:

```bash
./your_program.sh
```

## What I Learned Today

Quote states can be tracked with a variable (None, 'SINGLE', 'DOUBLE')

Quotes inside other quotes are literal characters

State machines are powerful for parsing

You can handle multiple similar but different cases elegantly

**Key differences from single quotes:**

- Single quotes: Only one quote type to track
- Double quotes: Need to distinguish between two quote types
- Solution: Use quote_state instead of boolean

## Challenges Faced

Handling quoted input correctly required careful consideration of several edge cases:

- Determining when spaces should act as separators versus literal characters
- Managing transitions between different quote states
- Preserving characters that would normally be special when inside the opposite quote type
- Concatenating adjacent quoted and unquoted segments correctly

The state machine approach solved these problems by explicitly tracking the current parsing context and adjusting behavior based on that state.

## Next Steps

Backslash inside quotes
