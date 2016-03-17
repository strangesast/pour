#!/usr/bin/env python3.5
import asyncio
import locale
import sys
from asyncio.subprocess import PIPE
from contextlib import closing

async def readline_and_kill(*args):
    # start child process
    process = await asyncio.create_subprocess_exec(*args, stdout=PIPE, cwd=path)

    # read line (sequence of bytes ending with b'\n') asynchronously
    async for line in process.stdout:
        print('line!')
        print("got line:", line.decode(locale.getpreferredencoding(False)))

    process.kill()
    return await process.wait() # wait for the child process to exit


loop = asyncio.get_event_loop()


path = "/home/samuel/Packages/simavr/examples/board_simduino"
command = ['obj-x86_64-linux-gnu/simduino.elf']

#command = ['tree']

with closing(loop):
    sys.exit(loop.run_until_complete(readline_and_kill(*command)))
