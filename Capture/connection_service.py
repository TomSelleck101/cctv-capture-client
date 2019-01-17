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

        # The queue to put messages to send on
        self.send_message_queue = manager.Queue(self.MAX_QUEUE_SIZE)

        # The queue received messages go onto
        self.receive_message_queue = manager.Queue(self.MAX_QUEUE_SIZE)

        # A queue which indicates if the service is connected or not
        self.is_connected_queue = manager.Queue(self.MAX_QUEUE_SIZE)

        # A queue which indicateds if the service is trying to connect
        self.pending_connection_queue = manager.Queue(self.MAX_QUEUE_SIZE)

        # A queue to stop sending activity
        self.stop_send_queue = manager.Queue(self.MAX_QUEUE_SIZE)

        # A queue to stop receiving activity
        self.stop_receive_queue = manager.Queue(self.MAX_QUEUE_SIZE)

    # Connect to the server
    # 1) If already connected - return
    # 2) If pending connection - return
    # 3) Start the network thread - don't return until the connection status is pending            
    def connect(self):
        if self.is_connected():
            return
        elif not self.pending_connection_queue.empty():
            return
        else:
            self.network_thread = multiprocessing.Process(target=self.start_network_comms)
            self.network_thread.start()

            #Give thread time to sort out queue
            while self.pending_connection_queue.empty():
                continue

    # Start network communications
    # Mark connection status as pending via queue. Clear stop queues.
    # Get socket for connection, mark as connected via queue.
    # Start Send + Receive message queues with socket as argument
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

    # Return true if connected queue has a value
    def is_connected(self):
        return not self.is_connected_queue.empty()

    # Put message on stop queues to end send / receive threads
    # Clear connected state queues
    def disconnect(self):
        print ("Disconnecting...")

        self.stop_receive_queue.put("")
        self.stop_send_queue.put("")

        self.clear_queue(self.pending_connection_queue)
        self.clear_queue(self.is_connected_queue)

        print ("Connection closed")

    # Send a message
    # If connected and send queue isn't full - add message to send queue
    # Raise exception if not connected
    def send_message(self, message):
        if self.is_connected():
            if self.send_message_queue.full():
                print ("Send message queue full...")
                return
            self.send_message_queue.put(message)
        else:
            raise NotConnectedException("Not connected to server...")

    # Send message to server
    # If send queue isn't empty, send the message length + message (expects binary data) to server
    # If exception while sending and the stop queue isn't empty - disconnect
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

    # Get a message
    # If the receive queue isn't empty - return a message
    def get_message(self):
        if not self.receive_message_queue.empty():
            return self.receive_message_queue.get()

        return None

    # Receive messages from socket
    # Read data from socket according to the pre-pended message length
    def receive_message(self, socket):
        data = b""
        payload_size = struct.calcsize(">L")

        print ("Listening for messages...")
        while self.stop_receive_queue.empty():
            #Get message size
            try:
                while len(data) < payload_size:
                    data += socket.recv(4096)

                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack(">L", packed_msg_size)[0]

                print ("Received message size:")
                print (msg_size)

                #Get message
                while len(data) < msg_size:
                    data += socket.recv(4096) 

                message = data[:msg_size]       
                data = data[msg_size:]   

                print (message)
                
                if self.receive_message_queue.qsize() >= self.MAX_QUEUE_SIZE or self.receive_message_queue.full():
                    continue

                self.receive_message_queue.put(message)

            except Exception as e:
                print (f"\nException while receiving messages: {e}\n\n")
                break

        print ("\nDisconnecting...\n\n")
        self.disconnect()

    # Connect to the server
    def connect_to_server(self, host, port, wait_time=1):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((host, port))
            return client_socket
        except Exception:
            print (f"Couldn't connect to remote address, waiting {wait_time} seconds to retry")
            time.sleep(wait_time)
            return self.connect_to_server(host, port, wait_time * 1)

    # Clear messages from the supplied queue (should live somewhere else)
    def clear_queue(self, queue):
        while not queue.empty():
            queue.get()

