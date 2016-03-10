#pourfunc
# y = height_coeff*(1 - 2^pow * ( 1 / width_coeff * x  - 1/2)^pow)

from __future__ import division
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

#def y(x, h=1, w=1, p=6):
#    return h*(1 - 2**p * ( 1 / w * x - 1/2 )**p)
#    
#
#x = np.arange(0, 1+0.01, 0.01)
#
#fig = plt.figure()
#ax = fig.add_subplot(111)
#ax.plot(x, y(x))
#
#fig.savefig('test.png')

import asyncio
import serial.aio

arduino_port = '/dev/pts/24'
address = ('127.0.0.1', 25000)

socket_transports = []

def clean(text):
    return [x.rstrip(',') for x in text.strip().split(' ')[1:]]

def grapher():
    t = []
    v = []
    x = []

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax2 = ax.twinx()

    print('initializing grapher...');
    while True:
        data_pts = yield;
        print('data!')
        ti, vi, xi = clean(data_pts)
        t.append(float(ti))
        v.append(float(vi))
        x.append(int(xi))
        if len(t) > 40:
            ax.plot(t, x)
            ax2.plot(t, v)
            fig.savefig('test.png')

g = grapher()
g.send(None)


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

            #if 'pour_update' in full_message:
            #    g.send(full_message)

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
