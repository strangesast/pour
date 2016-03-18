import os
import asyncio
import json
import re
import asyncio.subprocess
from asyncio.subprocess import PIPE, STDOUT, create_subprocess_exec
import sys
import serial.aio

path = os.path.join(os.environ['HOME'], "Packages/simavr/examples/board_simduino")

unbuf = ['stdbuf', '-oL', '-eL']
sim_command = unbuf + ['./obj-x86_64-linux-gnu/simduino.elf']

pat = re.compile('\/dev\/pts\/\d+')
pat = re.compile('((?P<sim>\/tmp\/.+?)\s)|(?P<pts>\/dev\/pts\/\d+)')

def find_match_in_iter(itr, reg):
    result = {}
    for each in itr:
        m = [m.groupdict() for m in reg.finditer(each)]
        for match in m:
            for key, val in match.items():
                if val is not None:
                    result[key] = val

    return result

def create_process_with_command(command, cwd=None):
    return create_subprocess_exec(*command, cwd=cwd,
            stdout=PIPE, stderr=STDOUT)


@asyncio.coroutine
def get_line_until_timeout(process, timeout=1.0, prnt=False):
    lines = []
    while True:
        linegen = process.stdout.readline()
        task = asyncio.wait_for(linegen, timeout)
        try:
            line = (yield from task).decode()
            if not line: break
            if prnt: print("{}{}{}".format(
                '\033[92m',
                line.strip(),
                '\033[0m'))
            lines.append(line)
        except asyncio.TimeoutError:
            break
    return lines


@asyncio.coroutine
def setup_sim(tty_future):
    print('creating sim process...', end=' ')
    create = create_process_with_command(sim_command, cwd=path)

    proc = yield from create

    all_data = yield from get_line_until_timeout(proc)

    pts = find_match_in_iter(all_data, pat)

    if pts:
        print('got {} '.format(pts['pts']))
        tty_future.set_result(pts)
    else:
        print('FAILED')
        tty_future.set_exception(Exception('no pts returned'))

    yield from proc.wait()

    return


@asyncio.coroutine
def upload_firmware():
    exit_code = yield from proc.wait()
    print('DONE')


@asyncio.coroutine
def make_and_upload_sim_code(sim_loc):
    print('building firmware...')

    make_command = ['make']
    make_path = '../arduino/testing'
    make_create = create_process_with_command(make_command, make_path)
    proc = yield from make_create
    all_data = yield from get_line_until_timeout(proc)#, 2.0, True)
    exit_code = yield from proc.wait()

    print('uploading firmware...')

    upload_command = unbuf + ['avrdude', '-p', 'm328p', '-c', 'arduino',
            '-P', sim_loc, '-U', 'flash:w:build-uno/testing.hex']

    upload_path = '../arduino/testing'
    create = create_process_with_command(upload_command, upload_path)
    proc = yield from create
    all_data = yield from get_line_until_timeout(proc)#, 2.0, True)

    exit_code = yield from proc.wait()

    print('DONE')
    return exit_code


def start_serial_connection(name, pts, connection_made_future):
    print('starting serial connection with {}...'.format(repr(pts)))

    yield from serial.aio.create_serial_connection(
            asyncio.get_event_loop(),
            lambda: SerialProtocol(name, pts, connection_made_future),
            port=pts,
            baudrate=9600)

    print('waiting for connection...')
    return (yield from connection_made_future)


def parse_full_line(port_from, line):
    result = {'from' : port_from}
    if 'update-temps' in line:
        match = re.findall('update-temps:\s([\d\.,\s]+)', line.strip())
        if len(match):
            temps = list(map(float, match[0].split(', ')))
            result.update({'type': 'temp-update', 'value' : temps })
        else:
            raise ValueError('improperly formated temp line')

    elif 'welcome' in line:
        # serial initialized
        result.update({'type' : 'serial-init'})

    else:
        result.update({'type': 'unknown', 'value' : line })

    return result


class SerialProtocol(asyncio.Protocol):
    def __init__(self, name, port, connection_established_future):
        self.port = port
        self.name = name
        self.connection_established_future = connection_established_future
        self.current_data = bytearray()

    def connection_made(self, transport):
        if self.connection_established_future:
            self.connection_established_future.set_result(True)
        self.transport = transport
        SerialProtocol.items.append(self)
        print('serial port opened: {} ({})'.format(repr(self.name), self.port))

    def data_received(self, data):
        self.current_data += data
        parsed = self.current_data.decode()
        spl = parsed.split('\n')
        while len(spl) > 1:
            line = spl.pop(0)
            result = parse_full_line(self.port, line)
            #text = 'line from {} ({}): {}'.format(repr(self.name), self.port, repr(line))

            for protocol in SocketProtocol.items:
                transport = protocol.transport
                t = result.get('type')
                if not (t is None or t == 'unknown'):
                    transport.write(json.dumps(result).encode())
                    transport.write(b'\n')

        self.current_data = spl[0].encode()

    def connection_lost(self, exc):
        print('port closed')
        SerialProtocol.items.remove(self)

    items = []

def get_temps(delay):
    while True:
        print('sleeping for {}s'.format(delay))
        yield from asyncio.sleep(delay)
        print('writing...')
        for protocol in SerialProtocol.items:
            transport = protocol.transport
            transport.write(b'temps\n')

    return

class SocketProtocol(asyncio.Protocol):
    def __init__(self):
        print('init!')

    def connection_made(self, transport):
        self.transport = transport
        peername = transport.get_extra_info('peername')
        print('New connection from {}'.format(peername))
        SocketProtocol.items.append(self)

    def data_received(self, data):
        message = data.decode()
        print('message received: {}'.format(repr(message)))

        #if message[:5] == 'close':
        #    self.transport.write(b'closing...\n')
        #    self.transport.close()
        #    return

        #elif message[:4] == 'quit':
        #    self.transport.write(b'stopping...\n')
        #    loop.stop()
        #    return

        #for sertransport in serial_transports:
        #    print('writing to serial...')
        #    sertransport.write(message.encode())

        #self.transport.write(b'wrote: ' + data)

    def connection_lost(self, exc):
        peername = self.transport.get_extra_info('peername')
        print('Connection from {} closed'.format(peername))
        SocketProtocol.items.remove(self)
        self.transport.close()

    items = []


@asyncio.coroutine
def main():
    # future for pts retrieval
    fut = asyncio.Future()

    # run this in the background until process terminates,
    # then possibly restart it
    simulator_proc = asyncio.ensure_future(setup_sim(fut))

    locs = yield from fut
    pts = locs['pts']
    sim = locs['sim']

    yield from make_and_upload_sim_code(sim)

    con_fut = asyncio.Future()

    name = 'testing port'
    yield from asyncio.ensure_future(start_serial_connection(name, pts, con_fut))

    # repeatedly get temps every 10s
    yield from asyncio.ensure_future(get_temps(10))

    yield from simulator_proc


loop = asyncio.get_event_loop()

try:
    host = '127.0.0.1'
    port=25000
    server = loop.create_server(
            SocketProtocol,
            host=host,
            port=port)

    loop.run_until_complete(server)
    print("Listening at '{}:{}'".format(host, port))

    loop.run_until_complete(main())

    loop.run_forever()

except KeyboardInterrupt:
    print('quit')

loop.close()
