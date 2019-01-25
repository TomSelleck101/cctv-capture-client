from send_message_exception import SendMessageException
from not_connected_exception import NotConnectedException

import socket
import time
import multiprocessing
import struct

class ConnectionService():

    MAX_QUEUE_SIZE = 1
    CLIENT_TYPE_REQUEST = b"0"

    def __init__(self, host, port, client_type):
        self.host = host
        self.port = port
        self.socket = None
        self.client_type = client_type
                
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
    def connect(self, init_message):
        print ("Attempting to connect...")
        if self.is_connected():
            print ("Already connected...")
            return
        elif not self.pending_connection_queue.empty():
            print ("Pending Connection...")
            return
        else:
            print ("Starting network connect thread...")
            self.network_thread = multiprocessing.Process(target=self.start_network_comms, args=(init_message,))
            self.network_thread.start()

            #Give thread time to sort out queue
            while self.pending_connection_queue.empty():
                continue

    # Start network communications
    # Mark connection status as pending via queue. Clear stop queues.
    # Get socket for connection, mark as connected via queue.
    # Start Send + Receive message queues with socket as argument
    def start_network_comms(self, init_message):
        self.clear_queue(self.stop_send_queue)
        self.clear_queue(self.stop_receive_queue)
        self.clear_queue(self.pending_connection_queue)

        self.pending_connection_queue.put("CONNECTING")

        sock = self.connect_to_server(self.host, self.port)
        
        print ("Connected to server...")

        receive_message_thread = multiprocessing.Process(target=self.receive_message, args=(sock,))
        receive_message_thread.start()

        send_message_thread = multiprocessing.Process(target=self.send_message_to_server, args=(sock,))
        send_message_thread.start()

        print ("Sending init message...")

        self.send_message_queue.put(init_message)

        server_ack = None
        count = 0
        while server_ack is None:
            if count > 20:
                self.disconnect()
                return

            print ("Waiting for ack from server...")

            server_ack = self.get_message()

            print ("Received: ")

            print (server_ack)
            time.sleep(1)

        self.is_connected_queue.put("CONNECTED")
        self.pending_connection_queue.get()
             

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
        self.clear_queue(self.receive_message_queue)
        self.clear_queue(self.send_message_queue)


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
        print ("Start send loop...")
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
            print ("Popping message...")
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
        except Exception as e:
            print (f"Connect exception {e}")
            print (f"Waiting {wait_time} seconds to retry")
            time.sleep(wait_time)
            return self.connect_to_server(host, port, wait_time * 1)

    # Clear messages from the supplied queue (should live somewhere else)
    def clear_queue(self, queue):
        while not queue.empty():
            queue.get()

