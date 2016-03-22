import os
import asyncio
import json
import re
import asyncio.subprocess
from asyncio.subprocess import PIPE, STDOUT, create_subprocess_exec
import sys
import serial.aio


with open('config.json') as f:
    config = json.load(f)

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
        for keg in Keg.items:
            if not keg.pouring:
                keg.serial_transport.write(b'temps\n')
                #for protocol in keg.registered_to:
                #    transport = protocol.transport
                #    transport.write(b'temps\n')

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

        m3 = re.findall('keg "([\w\s]+)" pour (\d+)', message)
        if m3:
            kegname, amount = m3[0]
            keg = Keg.get_keg_by_name(kegname)
            if keg is None:
                text = 'keg with name {} not found\n'.format(repr(kegname))
            else:
                keg.pouring = True
                keg.serial_transport.write('pour\n'.format(amount).encode())
                text = "pouring {} to {}...\n".format(amount, repr(kegname))

            return self.transport.write(text.encode())

        m4 = re.findall('keg "([\w\s]+)" pour cancel', message)
        if m4:
            kegname = m4[0]
            keg = Keg.get_keg_by_name(kegname)
            if keg is None:
                text = 'keg with name {} not found\n'.format(repr(kegname))
            elif keg.pouring:
                text = 'cancelling...\n'
                keg.serial_transport.write(b'cancel\n')
            else:
                text = 'keg is not pouring...\n'

            return self.transport.write(text.encode())
        

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
        self.pts = port
        self.virtual = virtual
        self.connection_ready = asyncio.Future()
        self.registered_to = set()
        self.pouring = False
        Keg.items.append(self)

    @asyncio.coroutine
    def init_connection(self):
        # establish connection
        print('establishing connection for {}'.format(repr(self.name)))

        if self.virtual:
            connected_fut = asyncio.Future()

            command = config['simulator_settings']['command']
            path = config['simulator_settings']['path']

            self.simulator_process_task = asyncio.ensure_future(Keg.create_simulator(
                connected_fut,
                command,
                path.replace('~', os.environ['HOME'])))

            pts = yield from connected_fut
            self.pts = pts

        assert self.pts, "No pts has been defined..."

        connection_made_future = asyncio.Future()

        transport, protocol = yield from serial.aio.create_serial_connection(
                asyncio.get_event_loop(),
                lambda: SerialProtocol(self, pts, connection_made_future),
                port=pts,
                baudrate=9600)
    
        self.serial_transport = transport

        print('waiting for connection...')
        yield from connection_made_future

        print('connection to "{}" made at "{}"!'.format(self.name, transport.serial.port))

    def send_message(self, message):
        message = message.rstrip('\n') + '\n'
        self.serial_transport.write(message.encode())

    def message_received(self, message):
        if 'welcome' in message:
            # should happen only once
            print('ready...')
            self.connection_ready.set_result(True)

        elif 'pour_update' in message:
            if 'finished' in message:
                self.pouring = False

        print('message for {}: {}'.format(repr(self.name), repr(message)))
        for protocol in self.registered_to:
            try:
                protocol.transport.write("message from {}: {}\n".format(repr(self.name), message).encode())
            # too vague
            except:
                print('removing transport...')
                self.registered_to.remove(protocol)

    @staticmethod
    def create_simulator(simulator_ready_future, command, path="./"):
        print('creating sim process...', end=' ')

        create = create_subprocess_exec(*command, cwd=path, stdout=PIPE, stderr=STDOUT)
        proc = yield from create
        all_data = yield from get_line_until_timeout(proc, 1.5, False)

        mat = re.findall('((?P<sim>\/tmp\/[-\w\d]+?)\s)|(?P<pts>\/dev\/pts\/\d+)', "".join(all_data))
        _, sim, pts = [next(x for x in y if x) for y in zip(*mat)]

        yield from make_and_upload_sim_code(sim)

        if pts:
            simulator_ready_future.set_result(pts)
            yield from proc.wait()

        else:
            return simulator_ready_future.set_exception(Exception('no pts returned'))


    @classmethod
    def get_keg_by_name(cls, name):
        return next((keg for keg in cls.items if keg.name == name), None)

    @classmethod
    def get_keg_by_pts(cls, pts):
        return next((keg for keg in cls.items if keg.pts == pts), None)

    items = []


@asyncio.coroutine
def main():
    for kegid, val in config['kegs'].items():
        if val.get('virtual') or kegid == 'test':
            keg = Keg(val['name'], True)
        else:
            keg = Keg(val['name'], False)

        yield from keg.init_connection()

        print('now waiting on ready from device...')

        yield from keg.connection_ready

        keg.send_message('temps')

    temps_coro = asyncio.ensure_future(get_temps(10))

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
