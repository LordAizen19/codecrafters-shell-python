import sys
import os
import subprocess

def check_command_in_path(command, paths_list):
    for path in paths_list:
        full_path = os.path.join(path, command)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    return None


def main():
    # TODO: Uncomment the code below to pass the first stage
    commands_list = ["echo", "type", "exit", "pwd", "cd"]
    path_env = os.environ.get("PATH", "")
    paths_list = path_env.split(os.pathsep)

    while True:
        sys.stdout.write("$ ")
        command = input()

        if command.strip() == "exit" and len(command) == 4:
            break

        elif command[0:4].strip() == "echo":
            if len(command) > 5:
                print(command[5:])
            else:
                print(f"{command}: command not found")

        elif command[0:3].strip() == "pwd" and len(command) == 3:
            print(os.getcwd())

        elif command.strip().split()[0] == "cd":
            parts = command.strip().split()
            if len(parts) == 1:
                os.chdir(os.path.expanduser("~"))
            elif len(parts) == 2:
                if parts[1][0] == "/":
                    try:
                        os.chdir(parts[1])
                    except FileNotFoundError:
                        print(f"cd: {parts[1]}: No such file or directory")
                else:
                    full_path = os.getcwd()
                    try:
                        os.chdir(full_path + parts[1])
                    except FileNotFoundError:
                        print(f"cd: {parts[1]}: No such file or directory")

        elif command[0:4].strip() == "type":
            if command[5:] in commands_list:
                print(f"{command[5:]} is a shell builtin")
                continue

            res = check_command_in_path(command[5:], paths_list)
            if res:
                print(f"{command[5:]} is {res}")
            else:
                print(f"{command[5:]}: not found")

        else:
            cmd = check_command_in_path(command.split()[0], paths_list)
            if cmd is not None:
                subprocess.run(command.strip(), shell=True)
            else:
                print(f"{command}: command not found")


if __name__ == "__main__":
    main()
