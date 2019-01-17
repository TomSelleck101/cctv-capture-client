import cv2
import multiprocessing

class CaptureService():

    FRAME_QUEUE_SIZE_LIMIT = 10
    STOP_QUEUE_SIZE_LIMIT = 1
    START_QUEUE_SIZE_LIMIT = 1

    def __init__(self):
        self.frame = None
        manager = multiprocessing.Manager()

        # The queue to add frames to
        self.frame_queue = manager.Queue(self.FRAME_QUEUE_SIZE_LIMIT)

        # A queue to indicate capturing should be stopped
        self.stop_queue = manager.Queue(self.STOP_QUEUE_SIZE_LIMIT)

        # A queue to indicate that capturing should be started
        self.start_queue = manager.Queue(self.START_QUEUE_SIZE_LIMIT)

    # Start Capture
    # Empty the stop queue. If the start queue is empty - start a new capture thread
    # If start queue is not empty, service has already been started
    def start_capture(self):
        print ("Starting capture...")
        while not self.stop_queue.empty():
            self.stop_queue.get()

        if self.start_queue.empty():
            self.capture_thread = multiprocessing.Process(target=self.capture_frames)
            self.capture_thread.start()
            self.start_queue.put("")
            print ("Capturing started...")
        else:
            print ("Capture already started...")

    # Is Capturing
    # Return true if start queue has a value
    def is_capturing(self):
        return not self.start_queue.empty()

    # Get Current Frame
    # Return the current frame from the frame queue
    def get_current_frame(self):
        if not self.frame_queue.empty():
            return self.frame_queue.get()

        return None

    # Stop Capture
    # Add a message to the stop queue
    # Empty the start queue
    def stop_capture(self):
        if self.stop_queue.empty():
            self.stop_queue.put("")

        while not self.start_queue.empty():
            self.start_queue.get()

    # Capture Frames
    # Captures frames from the device at 0
    # Only add frames to queue if there's space
    def capture_frames(self):
        cap = None
        try:
            cap = cv2.VideoCapture(0)
            while True:
                #Empty Start / Stop queue signals
                if not self.stop_queue.empty():
                    while not self.stop_queue.empty():
                        self.stop_queue.get()
                    while not self.start_queue.empty():
                        self.start_queue.get()
                    break;

                ret, frame = cap.read()

                if self.frame_queue.qsize() > self.FRAME_QUEUE_SIZE_LIMIT or self.frame_queue.full():
                    continue

                self.frame_queue.put(frame)

            # When everything done, release the capture
            cap.release()
            cv2.destroyAllWindows()

        except Exception as e:
            print ("Exception capturing images, stopping...")
            self.stop_capture()
            cv2.destroyAllWindows()
            if cap is not None:
                cap.release()

