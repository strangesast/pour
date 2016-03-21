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

    all_data = yield from get_line_until_timeout(proc, 1.5, False)

    pts = find_match_in_iter(all_data, pat)

    if pts:
        print('got {} '.format(pts['pts']))
        tty_future.set_result(pts)
    else:
        print('FAILED')
        tty_future.set_exception(Exception('no pts returned'))

    try:
        yield from proc.wait()
    except asyncio.CancelledError:
        print('simulator canceled')
        pass

    return


@asyncio.coroutine
def upload_firmware():
    exit_code = yield from proc.wait()
    print('DONE')


@asyncio.coroutine
def make_and_upload_sim_code(sim_loc):
    print('building firmware...', end='')

    make_command = ['make']
    make_path = '../arduino/testing'
    make_create = create_process_with_command(make_command, make_path)
    proc = yield from make_create
    all_data = yield from get_line_until_timeout(proc, 1.5, False)
    exit_code = yield from proc.wait()

    print('DONE')

    print('uploading firmware...', end='')

    upload_command = unbuf + ['avrdude', '-p', 'm328p', '-c', 'arduino',
            '-P', sim_loc, '-U', 'flash:w:build-uno/testing.hex']

    upload_path = '../arduino/testing'
    create = create_process_with_command(upload_command, upload_path)
    proc = yield from create
    all_data = yield from get_line_until_timeout(proc, 1.5, False)

    exit_code = yield from proc.wait()

    assert exit_code == 0

    print('DONE')
    return exit_code


def start_serial_connection(keg, pts):
    print('starting serial connection with {}...'.format(repr(pts)))
    connection_made_future = asyncio.Future()
    serial_transport = yield from serial.aio.create_serial_connection(
            asyncio.get_event_loop(),
            lambda: SerialProtocol(keg, pts, connection_made_future),
            port=pts,
            baudrate=9600)

    print('waiting for connection...')
    yield from connection_made_future

    return serial_transport


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
            #result = parse_full_line(self.port, line)
            #text = 'line from {} ({}): {}'.format(repr(self.keg.name), self.port, repr(line))

            #for protocol in SocketProtocol.items:
            #    transport = protocol.transport
            #    t = result.get('type')
            #    if not (t is None or t == 'unknown'):
            #        transport.write(json.dumps(result).encode())
            #        transport.write(b'\n')

        self.current_data = spl[0].encode()

    def connection_lost(self, exc):
        print('port closed')
        SerialProtocol.items.remove(self)

    items = []

@asyncio.coroutine
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

        m1 = re.findall('reg\s(\/dev\/[\w\/]+)', message)
        if m1:
            keg = Keg.get_keg_by_pts(m1[0])
            if keg is None:
                text = 'keg with pts {} not found\n'.format(repr(m1[0]))

            else:
                keg.registered_to.add(self)
                text = 'registered to {}\n'.format(repr(keg.name))

            return self.transport.write(text.encode())

        m2 = re.findall('reg\s"([\w\s]+)"', message)
        if m2:
            keg = Keg.get_keg_by_name(m2[0])
            if keg is None:
                text = 'keg with name {} not found\n'.format(repr(m2[0]))

            else:
                keg.registered_to.add(self)
                text = 'registered to {}\n'.format(repr(keg.name))

            return self.transport.write(text.encode())

        self.transport.write(b'unrecognized or malformed command\n')
        

    def connection_lost(self, exc):
        peername = self.transport.get_extra_info('peername')
        print('Connection from {} closed'.format(peername))
        SocketProtocol.items.remove(self)
        self.transport.close()

    items = []


class Keg:
    def __init__(self, name, virtual=True, host=None, port=None):
        self.name = name
        self.host = host
        self.port = port
        self.virtual = virtual
        self.connection_ready = asyncio.Future()
        self.registered_to = set()
        Keg.items.append(self)

    @asyncio.coroutine
    def init_connection(self):
        # establish connection
        print('establishing connection for {}'.format(repr(self.name)))

        if self.virtual:
            sim_setup_complete = asyncio.Future()
            sim_task = asyncio.ensure_future(setup_sim(sim_setup_complete))

            port_defs = yield from sim_setup_complete

            sim, pts = [port_defs.get(x) for x in ['sim', 'pts']]
            self.pts = pts
            yield from make_and_upload_sim_code(sim)

            transport, protocol = yield from start_serial_connection(self, pts)

            self.serial_transport = transport

        print('connected!')

    def send_message(self, message):
        message = message.rstrip('\n') + '\n'
        self.serial_transport.write(message.encode())

    def message_received(self, message):
        if 'welcome' in message:
            # should happen only once
            print('ready...')
            self.connection_ready.set_result(True)
        else:
            print('message for {}: {}'.format(repr(self.name), repr(message)))
            for protocol in self.registered_to:
                try:
                    protocol.transport.write("message from {}: {}\n".format(repr(self.name), message).encode())
                # too vague
                except:
                    print('removing transport...')
                    self.registered_to.remove(protocol)


    @classmethod
    def get_keg_by_name(cls, name):
        return next((keg for keg in cls.items if keg.name == name), None)

    @classmethod
    def get_keg_by_pts(cls, pts):
        return next((keg for keg in cls.items if keg.pts == pts), None)

    items = []


@asyncio.coroutine
def main():
    with open('config.json') as f:
        config = json.load(f)

    for kegid, val in config['kegs'].items():
        if val.get('virtual') or kegid == 'test':
            keg = Keg(val['name'], True)
            yield from keg.init_connection()

            yield from keg.connection_ready

            keg.send_message('temps')

        else:
            pass

    while True:
        yield from asyncio.sleep(10.0)
        for keg in Keg.items:
            yield from asyncio.sleep(1.0)
            keg.send_message('temps\n')

    ## future for pts retrieval
    #fut = asyncio.Future()

    ## run this in the background until process terminates,
    ## then possibly restart it
    #simulator_proc = asyncio.ensure_future(setup_sim(fut))

    #locs = yield from fut
    #pts = locs['pts']
    #sim = locs['sim']

    #yield from make_and_upload_sim_code(sim)

    #con_fut = asyncio.Future()

    #name = 'testing port'
    #yield from asyncio.ensure_future(start_serial_connection(name, pts, con_fut))

    ## repeatedly get temps every 10s
    #temps_coro = get_temps(10)
    #all_temps_task = yield from asyncio.ensure_future(temps_coro)
    #yield from simulator_proc


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
