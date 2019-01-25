from orchestrator import Orchestrator
from connection_service import ConnectionService
from capture_service import CaptureService

HOST = "127.0.0.1"
PORT = 80
CAPTURE_CLIENT = b"0"
def main():
    capture_service = CaptureService()
    connection_service = ConnectionService(HOST, PORT, CAPTURE_CLIENT)
    orchestrator = Orchestrator(capture_service, connection_service)

    orchestrator.start()

if __name__ == '__main__':
    main()
    