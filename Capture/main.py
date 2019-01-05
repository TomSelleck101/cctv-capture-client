from connection_service import ConnectionService
from capture_service import CaptureService
from orchestrator import Orchestrator

import signal
import sys
import time
import cv2

HOST, PORT = "127.0.0.1", 11000

connection_service = None
capture_service = None
orchestrator = None

def main():

    connection_service = ConnectionService(HOST, PORT)
    capture_service = CaptureService()

    orchestrator = Orchestrator(capture_service, connection_service)
    orchestrator.start()

    print ("Completed all tasks")


def exit_gracefully(signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    signal.signal(signal.SIGINT, original_sigint)
    try:
        orchestrator.finish()
    except KeyboardInterrupt:
        print("Ok ok, quitting")
        if orchestrator is not None:
            try:
                orchestrator.finish()
            except Exception as e:
                return

    # restore the exit gracefully handler here    
    signal.signal(signal.SIGINT, exit_gracefully)

if __name__ == '__main__':
    # store the original SIGINT handler
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)

    main()