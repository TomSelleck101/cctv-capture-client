from send_message_exception import SendMessageException
import socket
import time
import multiprocessing
import struct

class ConnectionService():

    MAX_QUEUE_SIZE = 1

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
                
        manager = multiprocessing.Manager()

        self.message_queue = manager.Queue(self.MAX_QUEUE_SIZE)
        self.pending_connection_queue = manager.Queue(self.MAX_QUEUE_SIZE)
        self.socket_queue = manager.Queue(self.MAX_QUEUE_SIZE)

    def connect(self):
        print ("Connecting to server...")

        if self.is_connected():
            print ("Already connected...")

        elif not self.pending_connection_queue.empty():
            print ("Attemping to connect...")

        else:
            self.network_thread = multiprocessing.Process(target=self.start_network_comms)
            self.network_thread.start()

    def start_network_comms(self):
            self.pending_connection_queue.put("CONNECTING...")
            self.socket = self.connect_to_server(self.host, self.port)
            self.pending_connection_queue.get()
             
            print ("Connected to server...")
            print ("Putting socket on queue...")
            self.socket_queue.put(self.socket)
            self.receive_messages(self.socket)

    def is_connected(self):
        return not self.socket_queue.empty()

    def disconnect(self):
        while not self.pending_connection_queue.empty():
            self.pending_connection_queue.get()

        while not self.socket_queue.empty():
            s = self.socket_queue.get()
            s.shutdown(socket.SHUT_RDWR)
            s.close()

        print ("Connection closed")


    def send_message(self, message):
        if not self.socket_queue.empty() and message is not None:
            sock = self.socket_queue.get()
            if isinstance(sock, socket.socket):
                try:
                    message_size = len(message)
                    print (f"Message: {message_size} - {message}")
                    print (f"{message.encode()}")
                    print(struct.pack(">L", message_size))
                    sock.sendall(struct.pack(">L", message_size) + message.encode())
                except Exception as e:
                    print (f"\nException sending message:\n\n{e}")
                    self.disconnect()
                    raise SendMessageException("Exception sending message")
            self.socket_queue.put(sock)

    def get_message(self):
        if not self.message_queue.empty():
            return self.message_queue.get()

        return None

    def receive_messages(self, socket):
        data = b""
        payload_size = struct.calcsize(">L")

        print ("Listening for messages...")
        while True:                                     # While socket connection is open
            #Get message size
            try:
                while len(data) < payload_size:
                    data += socket.recv(4096)

                packed_msg_size = data[:payload_size]   # Message size is equal to start of byte array until payload size (initially 4 bytes)
                data = data[payload_size:]              # Data is equal to from end of payload bytes until end of byte array
                msg_size = struct.unpack(">L", packed_msg_size)[0]

                print ("Received message size:")
                print (msg_size)


                #Get message
                while len(data) < msg_size:             # While the total length of retrieved data is less than size of message
                    data += socket.recv(4096)           # Append more data from socket

                message = data[:msg_size]               # Message is equal to start of array until size of message
                data = data[msg_size:]                  # Data is equal to data array starting at message length


                print (message)
                
                if self.message_queue.qsize() >= self.MAX_QUEUE_SIZE or self.message_queue.full():
                    continue

                self.message_queue.put(message)

            except Exception as e:
                print (f"\nException while receiving messages: {e}\n\n")
                break

        print ("\nNo longer listening for messages...\n\n")
        

    def connect_to_server(self, host, port, wait_time=1):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            client_socket.connect((host, port))

            return client_socket
        except Exception:
            print (f"Couldn't connect to remote address, waiting {wait_time} seconds to retry")
            time.sleep(wait_time)
            return self.connect_to_server(host, port, wait_time * 1)

	#def get_message():
	#def send_message():
	#def is_connected():

