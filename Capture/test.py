from connection_service import ConnectionService
from sys import stdin
import signal


def main():
    my_value = ""


    connection = ConnectionService("127.0.0.1", 11000)
    connection.connect()

    while my_value is not "q":
        my_value = stdin.readline()
        my_value = "TESTESTEST"
        connection.send_message(my_value.strip())
        connection.send_message("ABC")
        print (my_value)


if __name__ == '__main__':
    main()