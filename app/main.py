import sys

BUILTINS = {
    "exit": lambda code=0, *_: sys.exit(int(code)),
    "echo": lambda *args: print(" ".join(args)),
}

def main():
    while True:  #infinite loop keeps running forever
        sys.stdout.write("$ ")
        sys.stdout.flush()

        user_input = input().strip()

        parts = user_input.split()
        if not parts:
            continue
        cmd  = parts[0]
        args = parts[1:]

        if cmd in BUILTINS:
            BUILTINS[cmd](*args)
        else:
            print(f"{cmd}: command not found")

if __name__ == "__main__":
    main()
