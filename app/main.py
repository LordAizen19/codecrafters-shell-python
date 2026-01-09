import sys

def main():
    while True:  #infinite loop keeps running forever
        # TODO: Uncomment the code below to pass the first stage
        sys.stdout.write("$ ")
        sys.stdout.flush()
        # pass

        # taking user input
        command = input().strip()
        print(f"{command}: command not found")


if __name__ == "__main__":
    main()
