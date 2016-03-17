#!/usr/bin/python3
# -*- coding: utf-8 -*-


import sys
from queue import Queue
from subprocess import PIPE, Popen
from threading import Thread


def read_output(pipe, funcs):
    for line in iter(pipe.readline, b''):
        for func in funcs:
            func(line.decode('utf-8'))
    pipe.close()


def write_output(get):
    for line in iter(get, None):
        sys.stdout.write(line)


def run_cmd(command, cwd=None, passthrough=True):
    outs, errs = None, None

    proc = Popen(
        command,
        cwd=cwd,
        shell=True,
        close_fds=True,
        stdout=PIPE,
        stderr=PIPE,
        bufsize=1
        )

    if passthrough:

        outs, errs = [], []

        q = Queue()

        stdout_thread = Thread(
            target=read_output, args=(proc.stdout, [q.put, outs.append])
            )

        stderr_thread = Thread(
            target=read_output, args=(proc.stderr, [q.put, errs.append])
            )

        writer_thread = Thread(
            target=write_output, args=(q.get,)
            )

        for t in (stdout_thread, stderr_thread, writer_thread):
            t.daemon = True
            t.start()

        proc.wait()

        for t in (stdout_thread, stderr_thread):
            t.join()

        q.put(None)

        outs = ' '.join(outs)
        errs = ' '.join(errs)

    else:

        outs, errs = proc.communicate()
        outs = '' if outs == None else outs.decode('utf-8')
        errs = '' if errs == None else errs.decode('utf-8')

    rc = proc.returncode

    return (rc, (outs, errs))


command = ['obj-x86_64-linux-gnu/simduino.elf 2> /dev/null']
path = "/home/samuel/Packages/simavr/examples/board_simduino"
run_cmd(*command, cwd=path)
