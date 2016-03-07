# connect to arduino
# open socket connections
import socket
import asyncio
import serial
import serial.aio

loop = asyncio.get_event_loop()

arduino_port = '/dev/ttyACM0'

clients = []

async def echo_server(address):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(address)
    sock.listen(5)
    sock.setblocking(False)
    while True:
        client, addr = await loop.sock_accept(sock)
        print('Connected from', addr)
        loop.create_task(echo_handler(client))

async def echo_handler(client):
    clients.append(client)
    with client:
        while True:
            data = await loop.sock_recv(client, 10000)
            if not data:
                break
            for each in clients:
                await loop.sock_sendall(each, b'Got:'+ data)

            for each in transports:
                each.write(data)

    clients.remove(client)
    print('Connection closed')

transports = []

class Output(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        transports.append(transport)
        self.current_data = ""
        print('port opened on', transport)
        transport.serial.rts = False
        transport.write(b'Hellooooo\n')

    def data_received(self, data):
        string = data.decode('utf-8')
        self.current_data += string
        #print('data received', repr(data))
        if '\n' in string:
            splt = self.current_data.split('\n')
            full_string = splt.pop(0)
            self.current_data = "".join(splt)
            for each in clients:
                each.send((full_string + '\n').encode())
            print(full_string)

    def connection_lost(self, exc):
        transports.remove(self.transport)
        print('port closed')

    def write_message(self, message):
        self.transport.write(message)

def got_result(future):
    print("future loaded")
    print(future.result())

loop.create_task(echo_server(('', 25000)))

# future?
co = serial.aio.create_serial_connection(loop, Output, arduino_port, baudrate=9600)

loop.run_until_complete(co)
loop.run_forever()
loop.close()


# 
# while waiting for socket data
#   ask for temperatures
#   print
#
# on connection
#   welcome!
#   wait for data
#   
#   on recieve
#     temp request
#       send temp req to arduino
#
#     pour request
#       respond with status updates
#
#     pour cancel
#       is pour in progress?
#         yes? cancel

"""
import asyncio
import serial
import time

dev = "/dev/ttyACM0"
serial_func = serial.Serial(port=dev, baudrate=9600, timeout=2)

def write_output():
    print(serial_func.readline())

f = write_output()

loop.add_reader(serial_func.fileno(), f)
loop.run_forever()
"""
