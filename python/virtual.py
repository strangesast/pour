from asyncio.subprocess import PIPE, STDOUT, create_subprocess_exec
import asyncio
import re


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
def _make_and_upload_sim_code(sim_loc):
    print('building firmware...', end='')

    make_command = ['make']
    make_path = '../arduino/testing'
    make_create = create_process_with_command(make_command, make_path)
    proc = yield from make_create
    all_data = yield from get_line_until_timeout(proc, 1.5, False)
    exit_code = yield from proc.wait()

    print('DONE')

    print('uploading firmware...', end='')

    unbuf = ['stdbuf', '-oL', '-eL']
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


def create_simulator(simulator_ready_future, command, path="./"):
    print('creating sim process...', end=' ')

    create = create_subprocess_exec(*command, cwd=path, stdout=PIPE, stderr=STDOUT)
    proc = yield from create
    all_data = yield from get_line_until_timeout(proc, 1.5, False)

    mat = re.findall('((?P<sim>\/tmp\/[-\w\d]+?)\s)|(?P<pts>\/dev\/pts\/\d+)', "".join(all_data))
    _, sim, pts = [next(x for x in y if x) for y in zip(*mat)]

    yield from _make_and_upload_sim_code(sim)

    if pts:
        simulator_ready_future.set_result(pts)
        yield from proc.wait()

    else:
        return simulator_ready_future.set_exception(Exception('no pts returned'))
