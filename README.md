<p align="center">
  <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAfCAMAAACxiD++AAAAzFBMVEVHcEwQv+0A4O8Pwe4vg+06a+s6fuoF2fNmE+dGVuZULt9kEeID2u5DVuYRvuwRvuxXLeRYLeRGVuUZpOJYLOVOE7Iojekhm+phGOJNQ+RhGuJOQeQODxQRERcTFBoVFh0AAAD///8TAQAEDACTk5QepvAZOV4FBw9WV1kODgsvLzNdJehOROkNud1tbW8+P0LMzMwnFVwaI0bn5+clTZRYGc4ih9USWGVEWOw8FYwToc0+T9FKLMW1trccGjEWao0PhZhhYWSBgoQuLoo2PTGRAAAAHHRSTlMAziH4/fwB/v4d+Kenp1CUlMQy2NzWoK1SUk5OwOG+6QAAAdFJREFUKJFtk1l3mzAQheWG1a63nJ4srSRGIkBYAg7xWjd2lv//nzKSgEDS+8LDd3VnRhoI6eTM5qML1Gg+c8h3/fjpuu7FX1SEuva/csQP51pq1edtZF0NjyPeSckDJc6kjLeW5Q/4i2RBI45K5dqyLnt8J4Ogb+BcxpbdZvyPK4dtt/29yB4GaB1re2oKPAz4aqUdjDE47n0dsGOfhuRVPIHhLI33GOF0AZQyHsCzuIOEMi04Fg6ZtR1AVlWMw5OosioDxWn6XvwhczfWFeBOiDKhFVYoBaboGnWxICNXtvweOH6eAe4bBw2LJRnpFhqOM4gSmHFQSsPxL2PA3sUbcgZCAHYIb8rfM3QVSrHC7GFChI/IVXHxCnrIT07DfEnmUczUzekp1JCJmULxtM4XZBadpb5ayLJMDclolp00p+Eh/02caKsNnFGqh8TpkoQaw8bD7byO4tQ8H8MKpTI0Ch+9CT6W30Sou8eXpD3DxtMrc2WtpTFQGPCDDkBZVixZp14Br1k5v+egfd7t9aVtr2U6OI75XrfVmGHbxxrC1NA0DB83vfNa0/3++H4KtU4HxJOv/54/LVD/UHmee5Nv/ybKuV0sx3k+Xi5uHNL93x+Do2IF3gwEkwAAAABJRU5ErkJggg==" alt="CodeCrafters" width="96" />
</p>

# CodeCrafters — Python Shell

A small, educational Unix-like shell implemented in Python as part of the CodeCrafters "Build Your Own Shell" challenge. This repository focuses on command tokenization and correct handling of single-quoted input.

## Short description
A minimal, readable Python shell implementation that demonstrates character-by-character parsing for single-quote handling and basic tokenization.

## Project overview
This project implements the parsing stage of a shell: reading a command string and splitting it into tokens while correctly handling single quotes. The implemented stage preserves spaces inside single quotes, concatenates adjacent quoted segments, and uses stateful, character-by-character parsing to produce reliable tokens.

## Implemented features
- Command tokenization (splits input into argument tokens)
- Single-quote handling
- Preservation of spaces inside single quotes
- Concatenation of adjacent quoted strings
- Character-by-character parsing with simple state tracking

## How single-quote parsing works (high-level)
- The parser scans the input one character at a time.
- It tracks an inside_quotes boolean (or equivalent) to know whether the parser is currently inside a single-quoted section.
- When inside_quotes is true:
  - Spaces are treated as literal characters and appended to the current token.
  - Characters are appended until a closing single quote is found.
- When inside_quotes is false:
  - Unquoted spaces act as token separators.
  - Single-quote characters switch the parser into inside_quotes mode; a following single quote exits that mode.
- Adjacent quoted segments and unquoted segments are concatenated into the same token when not separated by unquoted spaces.

This state-based approach ensures that quoted sequences are preserved as intended while still splitting on unquoted whitespace.

## Code example
A short usage example showing the parser in action (do not modify the implementation):

```python
# Example usage (adjust import path to your repo layout)
# from parser import parse_command_with_quotes

input_str = "echo 'hello world' foo''bar baz"
tokens = parse_command_with_quotes(input_str)

# Expected tokens:
# ["echo", "hello world", "foobar", "baz"]
```

## Running the program
The tester runs the shell as:
```bash
./your_program.sh
```
(Replace with the actual script or entry point filename if different in this repository.)

## What I learned today
- Quotes group text into single arguments.
- Spaces inside single quotes are preserved verbatim.
- Adjacent quoted strings (or quoted + unquoted segments without separating spaces) concatenate into one token.
- Character-by-character parsing is required to correctly handle quoting edge cases.
- State tracking (inside_quotes boolean) is a simple and effective control mechanism.

## Challenges faced
- Handling quoted input correctly is error-prone: deciding when spaces act as separators versus literal characters is central to correctness.
- Adjacent quotes and empty quoted segments complicate token assembly.
- The solution requires careful state transitions (enter/exit quote) and correct concatenation logic.

## Next steps
Planned improvements for subsequent stages:
- Support double quotes and escapes inside double quotes.
- Implement escape character handling (backslash).
- Add execution of parsed commands, pipelines, and redirections.
- Add tests around more edge cases and interactive behaviors.

## Notes
- This README intentionally documents only the parsing stage implemented here. If you need exact filenames or the program entry point, check the repository root for the script used by the tester.
- Replace the logo path `assets/codecrafters-logo.png` with the actual logo file if you add one to the repository.
