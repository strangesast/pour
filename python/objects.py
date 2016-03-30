from asyncio.subprocess import PIPE, STDOUT, create_subprocess_exec
import asyncio.subprocess
import serial.aio
import asyncio
import json
import sys
import re
import os

import virtual

with open('config.json') as f:
    config = json.load(f)


class SerialProtocol(asyncio.Protocol):
    def __init__(self, keg, port, connection_established_future):
        self.port = port
        self.keg = keg
        self.connection_established_future = connection_established_future
        self.current_data = bytearray()

    def connection_made(self, transport):
        if self.connection_established_future:
            self.connection_established_future.set_result(True)
        self.transport = transport
        SerialProtocol.items.append(self)
        print('serial port opened: {} ({})'.format(repr(self.keg.name), self.port))

    def data_received(self, data):
        self.current_data += data
        parsed = self.current_data.decode()
        spl = parsed.split('\n')
        while len(spl) > 1:
            line = spl.pop(0)
            self.keg.message_received(line)

        self.current_data = spl[0].encode()

    def connection_lost(self, exc):
        print('port closed')
        SerialProtocol.items.remove(self)

    items = []

def handle_message(message):
    m1 = re.findall('reg\s(\/dev\/[\w\/]+)', message)
    if m1:
        keg = Keg.get_keg_by_pts(m1[0])
        if keg is None:
            text = 'keg with pts {} not found\n'.format(repr(m1[0]))

        else:
            self.registered_to.add(keg.name)
            text = 'registered to {}\n'.format(repr(keg.name))

        return self.transport.write(text.encode())

    m2 = re.findall('reg\s"([\w\s]+)"', message)
    if m2:
        keg = Keg.get_keg_by_name(m2[0])
        if keg is None:
            text = 'keg with name {} not found\n'.format(repr(m2[0]))

        else:
            self.registered_to.add(self)
            text = 'registered to {}\n'.format(repr(keg.name))

        return self.transport.write(text.encode())

    m3 = re.findall('keg "([\w\s]+)" pour (\d+)', message)
    if m3:
        kegname, amount = m3[0]
        keg = Keg.get_keg_by_name(kegname)
        if keg is None:
            text = 'keg with name {} not found\n'.format(repr(kegname))
        else:
            text = "pouring {} to {}...\n".format(amount, repr(kegname))
            keg.create_task(keg.pour, 100, int(amount))

        return self.transport.write(text.encode())

    m4 = re.findall('keg "([\w\s]+)" pour cancel', message)
    if m4:
        kegname = m4[0]
        keg = Keg.get_keg_by_name(kegname)
        if keg is None:
            text = 'keg with name {} not found\n'.format(repr(kegname))

        elif keg.current_task is not None:
            text = 'cancelling...\n'
            keg.serial_transport.write(b'cancel\n')
        else:
            text = 'keg is not pouring...\n'

        return self.transport.write(text.encode())

    return "err: invalid command"


class SocketProtocol(asyncio.Protocol):
    def __init__(self):
        self.registered_to = set()
        print('init!')

    def connection_made(self, transport):
        self.transport = transport
        peername = transport.get_extra_info('peername')
        print('New connection from {}'.format(peername))
        SocketProtocol.items.append(self)

    def data_received(self, data):
        message = data.decode()
        return handle_message(message)

    def connection_lost(self, exc):
        peername = self.transport.get_extra_info('peername')
        print('Connection from {} closed'.format(peername))
        SocketProtocol.items.remove(self)
        self.transport.close()

    items = []


class KegTask:
    def __init__(self, completed_future, waiting_on):
        self.completed_future = completed_future
        self.waiting_on = waiting_on

    def update(self, message):
        result = self.waiting_on(message)
        if result:
            self.completed_future.set_result(result)


class Keg:
    def __init__(self, name, vir=True, host=None, port=None):
        self.name = name
        self.host = host
        self.pts = port
        self.virtual = vir
        self.current_task = None
        self.pouring = None
        Keg.items.append(self)

    @asyncio.coroutine
    def init_connection(self):
        # establish connection
        print('establishing connection for {}'.format(repr(self.name)))

        if self.virtual:
            connected_fut = asyncio.Future()

            command = config['simulator_settings']['command']
            path = config['simulator_settings']['path']

            self.simulator_process_task = asyncio.ensure_future(virtual.create_simulator(
                connected_fut,
                command,
                path.replace('~', os.environ['HOME'])))

            pts = yield from connected_fut
            self.pts = pts

        assert self.pts, "No pts has been defined..."

        connection_made_future = asyncio.Future()

        transport, protocol = yield from serial.aio.create_serial_connection(
                asyncio.get_event_loop(),
                lambda: SerialProtocol(self, self.pts, connection_made_future),
                port=self.pts,
                baudrate=9600)
    
        self.serial_transport = transport

        print('waiting for connection...')
        yield from connection_made_future

        print('connection to "{}" made at "{}"!'.format(self.name, transport.serial.port))

    def send_message(self, message):
        message = message.rstrip('\n') + '\n'
        self.serial_transport.write(message.encode())

    def message_received(self, message):
        if self.current_task is not None:
            print('message from {}: {}'.format(repr(self.name), repr(message)))
            self.current_task.update(message)
        else:
            # this should not happen
            print('unsolicited message: {}'.format(repr(message)))

    def temps(self, fut):
        print('requesting temps...')
        self.send_message('temps')
        waiting_on = re.compile('update-temps:\s(-?\d+\.\d+),\s(-?\d+\.\d+),\s(-?\d+\.\d+)').findall
        task = KegTask(fut, waiting_on)
        return task

    def welcome(self, fut):
        print("waiting for welcome...")
        waiting_on = re.compile('welcome!').findall
        task = KegTask(fut, waiting_on)
        return task

    def pour(self, fut, amount):
        print("waiting for pour to complete...")

        # send amount
        self.send_message('pour')

        waiting_on = re.compile('finished').findall
        task = KegTask(fut, waiting_on)
        return task

    # start 'task' - which is a function with Future as first arg - and add to current_task
    def create_task(self, task, timeout, *args):
        fut = asyncio.Future()
        try:
            if self.current_task is not None:
                raise Exception('a different task is already initiated')

            self.current_task = task(fut, *args)
            val = yield from asyncio.wait_for(fut, timeout)

        except Exception as e:
            val = e

        finally:
            self.current_task = None
            return val

    @asyncio.coroutine
    def _get_temps(self, delay):
        pass

    @asyncio.coroutine
    def get_temps(self, delay):
        self.serial_transport.write(b'temps\n')
        return asyncio.ensure_future(self._get_temps(delay))

    @classmethod
    def get_keg_by_name(cls, name):
        return next((keg for keg in cls.items if keg.name == name), None)

    @classmethod
    def get_keg_by_pts(cls, pts):
        return next((keg for keg in cls.items if keg.pts == pts), None)

    items = []
