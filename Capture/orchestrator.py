from connection_service import ConnectionService
from capture_service import CaptureService
from not_connected_exception import NotConnectedException

import multiprocessing
import cv2
import time
import base64

class Orchestrator():
    init_message = f"client_type:0&hub_name:test_hub&camera_id:1".encode()

    def __init__(self, capture_service, connection_service):
        self.manager = multiprocessing.Manager()

        self.connection_service = connection_service
        self.capture_service = capture_service

        self.SEND_FOOTAGE = False   
        self.DETECT_MOTION = False

        self.RUN = True

    # End services
    def finish(self):
        self.RUN = False
        self.connection_service.disconnect()
        self.capture_service.stop_capture()
             
    # Start services, connect to server / start capturing from camera
    # Grab frames from capture service and display
    # Retrieve any messages from connection service
    # Deal with message e.g stop / start sending frames
    # If send footage is true, encode frame as string and send
    def start(self):
        print ("Starting Orchestration...")

        self.connection_service.connect(self.init_message)
        self.capture_service.start_capture()
        while self.RUN:

            try:
                message = None

                #Get camera frames
                frame = self.capture_service.get_current_frame()

                self.display_frame(frame)

                if self.connection_service.is_connected():
                    message = self.connection_service.get_message()
                    if message is not None:
                        self.handle_message(message.decode())

                #Send footage if requested
                if self.SEND_FOOTAGE and frame is not None and self.connection_service.is_connected(): #or (self.DETECT_MOTION and motion_detected):
                    try:
                        reval, buffer = cv2.imencode('.jpg', frame)
                        jpg_as_text = base64.b64encode(buffer)
                        self.connection_service.send_message(jpg_as_text)

                    except NotConnectedException as e:
                        self.connection_service.connect(self.init_message)

                elif not self.connection_service.is_connected():
                    self.connection_service.connect(self.init_message)

            except Exception as e:
                print ("Unhandled error in main orchestration loop...")
                print (e)

    def handle_message(self, message):
        if message == "SEND_FOOTAGE":
            self.SEND_FOOTAGE = True

        elif message == "STOP_SEND_FOOTAGE":
            self.SEND_FOOTAGE = False

        elif message == "DETECT_MOTION":
            self.DETECT_MOTION = True

        elif message == "STOP_DETECT_MOTION":
            self.DETECT_MOTION = False

    def display_frame(self, frame):
        if frame is not None:
            # Display the resulting frame
            cv2.imshow('orchestrator', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                raise SystemExit("Exiting...")