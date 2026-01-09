import sys

def main():
    while True:  #infinite loop keeps running forever
        sys.stdout.write("$ ")
        valid_commands = ["echo", "exit", "help", "clear", "cd", "ls"]
        command = input().strip()
        if command is not None and command not in valid_commands:
            print(f"{command}: command not found")
        elif command == "exit":
            break


if __name__ == "__main__":
    main()
