from __future__ import division
import asyncio
from asyncio import subprocess
import serial.aio

arduino_port = '/dev/pts/24'
address = ('127.0.0.1', 25000)

command = ['sh', 'start_simavr.sh']

@asyncio.coroutine
def monitor_command():
    process = yield from asyncio.create_subprocess_exec(*command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, = yield from process.communicate()

    print(stdout)

socket_transports = []

class SocketOutput(asyncio.Protocol):
    print("Listening at {}".format(address))
    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('New connection from {}'.format(peername))
        socket_transports.append(transport)
        self.transport = transport

    def data_received(self, data):
        message = data.decode()
        print('message received: {}'.format(repr(message)))

        if message[:5] == 'close':
            self.transport.write(b'closing...\n')
            self.transport.close()
            return

        elif message[:4] == 'quit':
            self.transport.write(b'stopping...\n')
            loop.stop()
            return

        for sertransport in serial_transports:
            print('writing to serial...')
            sertransport.write(message.encode())

        self.transport.write(b'wrote: ' + data)

    def connection_lost(self, exc):
        peername = self.transport.get_extra_info('peername')
        print('Connection from {} closed'.format(peername))
        socket_transports.remove(self.transport)
        self.transport.close()


serial_transports = []

class SerialOutput(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        self.current_read = ""
        serial_transports.append(self.transport)
        print('port opened at ', arduino_port)

    def data_received(self, data):
        self.current_read += data.decode()
        if '\n' in self.current_read:
            s = self.current_read.split('\n')
            full_message = s.pop(0)
            self.current_read = "\n".join(s)

            for socktransport in socket_transports:
                print('writing to socket...')
                socktransport.write(('message from serial: "' + repr(full_message) + '"\n').encode())

    def connection_lost(self, exc):
        print('port closed')
        serial_transports.remove(self.transport)
        self.transport.close()

loop = asyncio.get_event_loop()

args = [SocketOutput] + list(address)
socket_coro = loop.create_server(*args)
serial_coro = serial.aio.create_serial_connection(loop, SerialOutput, arduino_port, baudrate=9600)

socket_server = loop.run_until_complete(socket_coro)
serial_server = loop.run_until_complete(serial_coro)

try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

print("closing server...")
socket_server.close()
loop.run_until_complete(socket_server.wait_closed())
loop.close()
