import asyncio
import re
import asyncio.subprocess
from asyncio.subprocess import PIPE, STDOUT, create_subprocess_exec
import sys
import serial.aio

path = "/home/samuel/Packages/simavr/examples/board_simduino"

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
    all_data = yield from get_line_until_timeout(proc, 2.0, True)
    exit_code = yield from proc.wait()

    print('uploading firmware...')

    upload_command = unbuf + ['avrdude', '-p', 'm328p', '-c', 'arduino',
            '-P', sim_loc, '-U', 'flash:w:build-uno/testing.hex']

    upload_path = '../arduino/testing'
    create = create_process_with_command(upload_command, upload_path)
    proc = yield from create
    all_data = yield from get_line_until_timeout(proc, 2.0, True)

    exit_code = yield from proc.wait()

    print('DONE')
    return exit_code


def start_serial_connection(pts, connection_made_future):
    print('starting serial connection with {}...'.format(repr(pts)))

    coro = serial.aio.create_serial_connection(
            asyncio.get_event_loop(),
            lambda: SerialProtocol(pts, connection_made_future),
            port=pts,
            baudrate=9600)

    return (yield from coro)


class SerialProtocol(asyncio.Protocol):
    def __init__(self, port_name, connection_established_future):
        self.port_name = port_name
        self.connection_established_future = connection_established_future
        self.current_data = bytearray()

    def connection_made(self, transport):
        if self.connection_established_future:
            self.connection_established_future.set_result(True)
        self.transport = transport
        SerialProtocol.transports.append(transport)
        print('port opened', transport)

    def data_received(self, data):
        self.current_data += data
        parsed = self.current_data.decode()
        spl = parsed.split('\n')
        while len(spl) > 1:
            print('line from {}'.format(repr(self.port_name)))
            print(repr(spl.pop(0)))

        self.current_data = spl[0].encode()
        #self.transport.close()

    def connection_lost(self, exc):
        print('port closed')
        SerialProtocol.transports.remove(transport)

    transports = []

def get_temps(delay):
    print('sleeping for {}s'.format(delay))
    yield from asyncio.sleep(delay)
    print('writing...')
    for transport in SerialProtocol.transports:
        transport.write(b'temps\n')

    return

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

    yield from asyncio.ensure_future(start_serial_connection(pts, con_fut))

    print('waiting...')
    yield from con_fut

    yield from get_temps(5)

    yield from simulator_proc


loop = asyncio.get_event_loop()

try:
    date = loop.run_until_complete(main())
    print(date)

except KeyboardInterrupt:
    print('quit')

loop.close()
