import socketserver
import struct
import time

class MyTCPHandler(socketserver.BaseRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        # self.request is the TCP socket connected to the client
        while True:
            self.data = self.request.recv(4096).strip()
            print ("{} wrote:".format(self.client_address[0]))
            print (self.data)
            # just send back the same data, but upper-cased

            d = "".encode()

            d += self.data.upper()
            size = len(d)

            self.request.sendall(struct.pack(">L", size) + d)



if __name__ == "__main__":
    HOST, PORT = "localhost", 11000

    # Create the server, binding to localhost on port 9999
    server = socketserver.TCPServer((HOST, PORT), MyTCPHandler)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()