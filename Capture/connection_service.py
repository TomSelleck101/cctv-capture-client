from send_message_exception import SendMessageException
from not_connected_exception import NotConnectedException

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

        self.send_message_queue = manager.Queue(self.MAX_QUEUE_SIZE)
        self.receive_message_queue = manager.Queue(self.MAX_QUEUE_SIZE)

        self.is_connected_queue = manager.Queue(self.MAX_QUEUE_SIZE)
        self.pending_connection_queue = manager.Queue(self.MAX_QUEUE_SIZE)

        self.stop_send_queue = manager.Queue(self.MAX_QUEUE_SIZE)
        self.stop_receive_queue = manager.Queue(self.MAX_QUEUE_SIZE)

        #self.socket_queue = manager.Queue(self.MAX_QUEUE_SIZE)

    def connect(self):
        #print ("Connecting to server...")

        if self.is_connected():
            #print ("Already connected...")
            return
        elif not self.pending_connection_queue.empty():
            #print ("Attemping to connect...")
            return
        else:
            self.network_thread = multiprocessing.Process(target=self.start_network_comms)
            self.network_thread.start()

            #Give thread time to sort out queue
            while self.pending_connection_queue.empty():
                continue

    def start_network_comms(self):
            self.pending_connection_queue.put("CONNECTING")
            self.clear_queue(self.stop_send_queue)
            self.clear_queue(self.stop_receive_queue)

            self.socket = self.connect_to_server(self.host, self.port)

            self.is_connected_queue.put("CONNECTED")
            self.pending_connection_queue.get()
        
            print ("Connected to server...")

            receive_message_thread = multiprocessing.Process(target=self.receive_message, args=(self.socket,))
            receive_message_thread.start()

            send_message_thread = multiprocessing.Process(target=self.send_message_to_server, args=(self.socket,))
            send_message_thread.start()

    def is_connected(self):
        return not self.is_connected_queue.empty()

    def disconnect(self):
        print ("Disconnecting...")

        self.stop_receive_queue.put("")
        self.stop_send_queue.put("")

        self.clear_queue(self.pending_connection_queue)
        self.clear_queue(self.is_connected_queue)

        print ("Connection closed")

    def send_message(self, message):
        if self.is_connected():
            if self.send_message_queue.full():
                print ("Send message queue full...")
                return
            self.send_message_queue.put(message)
        else:
            raise NotConnectedException("Not connected to server...")

    def send_message_to_server(self, socket):
        while self.stop_send_queue.empty():
            while not self.send_message_queue.empty():
                print ("Message found on queue...")
                try:
                    message = self.send_message_queue.get()
                    message_size = len(message)
                    print (f"Message: {message_size}")
                    socket.sendall(struct.pack(">L", message_size) + message)
                except Exception as e:
                    if not self.stop_send_queue.empty():
                        return
                    print (f"\nException sending message:\n\n{e}")
                    self.disconnect()

    def get_message(self):
        if not self.receive_message_queue.empty():
            return self.receive_message_queue.get()

        return None

    def receive_message(self, socket):
        data = b""
        payload_size = struct.calcsize(">L")

        print ("Listening for messages...")
        while self.stop_receive_queue.empty():               # While socket connection is open
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
                
                if self.receive_message_queue.qsize() >= self.MAX_QUEUE_SIZE or self.receive_message_queue.full():
                    continue

                self.receive_message_queue.put(message)

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

    def clear_queue(self, queue):
        while not queue.empty():
            queue.get()

	#def get_message():
	#def send_message():
	#def is_connected():

