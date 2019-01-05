from connection_service import ConnectionService
from capture_service import CaptureService
from not_connected_exception import NotConnectedException

import multiprocessing
import cv2
import time

class Orchestrator():

    def __init__(self, capture_service, connection_service):
        self.manager = multiprocessing.Manager()

        self.connection_service = connection_service
        self.capture_service = capture_service

        self.SEND_FOOTAGE = True   
        self.DETECT_MOTION = False

        self.RUN = True

    def finish(self):
        self.RUN = False
        self.connection_service.disconnect()
        self.capture_service.stop_capture()
                       
    def start(self):
        print ("Starting Orchestration...")

        self.connection_service.connect()
        self.capture_service.start_capture()
        while self.RUN:
            message = None

            self.display_frame()

            message = self.connection_service.get_message()

            self.handle_message(message)

            #Send footage if requested
            if self.SEND_FOOTAGE: #or (self.DETECT_MOTION and motion_detected):
                try:
                    self.connection_service.send_message("SEND_FRAME_DATA_HERE")

                except NotConnectedException as e:
                    self.connection_service.connect()

    def handle_message(self, message):
        if message is "START_CAPTURE":
            self.capture_service.start_capture()

        elif message is "STOP_CAPTURE":
            self.capture_service.stop_capture()

        elif message is "SEND_FOOTAGE":
            self.SEND_FOOTAGE = True

        elif message is "STOP_SEND_FOOTAGE":
            self.SEND_FOOTAGE = False

        elif message is "DETECT_MOTION":
            self.DETECT_MOTION = True

        elif message is "STOP_DETECT_MOTION":
            self.DETECT_MOTION = False

    def display_frame(self):
        #Get camera frames
        frame = self.capture_service.get_current_frame()
        if frame is not None:
            # Display the resulting frame
            cv2.imshow('orchestrator', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                raise SystemExit("Exiting...")