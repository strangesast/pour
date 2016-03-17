import asyncio
import re
import asyncio.subprocess
from asyncio.subprocess import PIPE, STDOUT
import sys

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

path = "/home/samuel/Packages/simavr/examples/board_simduino"

unbuf = ['stdbuf', '-oL', '-eL']
sim_command = unbuf + ['./obj-x86_64-linux-gnu/simduino.elf']

pat = re.compile('\/dev\/pts\/\d+')

def find_match_in_iter(itr, reg):
    for each in itr:
        m = reg.findall(each)
        if len(m) > 0:
            return m[0]

def create_process_with_command(command, cwd=None):
    return asyncio.create_subprocess_exec(*command, cwd=cwd,
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
                bcolors.OKGREEN,
                line.strip(),
                bcolors.ENDC))
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

    if pts is not None:
        print('got {}'.format(repr(pts)))
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
def make_and_upload_sim_code(pts_loc):
    make_command = ['make']
    make_path = '../arduino/testing'
    print('building firmware...')
    make_create = create_process_with_command(make_command, make_path)
    proc = yield from make_create
    all_data = yield from get_line_until_timeout(proc, 2.0, True)

    exit_code = yield from proc.wait()

    upload_command = unbuf + ['avrdude', '-p', 'm328p', '-c', 'arduino', '-P', '/tmp/simavr-uart0', '-U', 'flash:w:build-uno/testing.hex']
    upload_path = '../arduino/testing'

    print('uploading firmware...')
    create = create_process_with_command(upload_command, upload_path)
    proc = yield from create
    all_data = yield from get_line_until_timeout(proc, 2.0, True)

    exit_code = yield from proc.wait()

    print('DONE')
    return exit_code
   

@asyncio.coroutine
def main():
    # future for pts retrieval
    fut = asyncio.Future()

    # run this in the background until process terminates,
    # then possibly restart it
    simulator_proc = asyncio.ensure_future(setup_sim(fut))

    pts = yield from fut

    yield from make_and_upload_sim_code(pts)

    yield from simulator_proc


loop = asyncio.get_event_loop()

try:
    date = loop.run_until_complete(main())
    print(date)

except KeyboardInterrupt:
    print('quit')

loop.close()
