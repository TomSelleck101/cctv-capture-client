import cv2
import multiprocessing

class CaptureService():

    FRAME_QUEUE_SIZE_LIMIT = 10
    STOP_QUEUE_SIZE_LIMIT = 1
    START_QUEUE_SIZE_LIMIT = 1

    def __init__(self):
        self.frame = None
        manager = multiprocessing.Manager()

        self.frame_queue = manager.Queue(self.FRAME_QUEUE_SIZE_LIMIT)
        self.stop_queue = manager.Queue(self.STOP_QUEUE_SIZE_LIMIT)
        self.start_queue = manager.Queue(self.START_QUEUE_SIZE_LIMIT)


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

    def is_capturing(self):
        return not self.start_queue.empty()

    def get_current_frame(self):
        if not self.frame_queue.empty():
            return self.frame_queue.get()

        return None

    def stop_capture(self):
        if self.stop_queue.empty():
            self.stop_queue.put("")

        while not self.start_queue.empty():
            self.start_queue.get()

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

