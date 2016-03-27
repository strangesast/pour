from serial.tools import list_ports
import asyncio
import sys

from objects import Keg

try:
    pts = next(port.device for port in list_ports.comports()
        if 'Arduino' in port.manufacturer)
except StopIteration:
    pts = None

if pts is None:
    print('Arduino not found via serial')
    sys.exit()

else:
    print('Found arduino at pts {}...'.format(pts))


@asyncio.coroutine
def main():
    keg = Keg('test', vir=False, port=pts)

    yield from asyncio.sleep(1)

    print(keg)

    yield from keg.init_connection()
    welcome_message = yield from keg.create_task(keg.welcome, 10)

    print('welcome_message')
    print(welcome_message)

    temps = yield from keg.create_task(keg.temps, 20)
    print('temps!')
    print(temps)

    pour = yield from keg.create_task(keg.pour, 200)


loop = asyncio.get_event_loop()

asyncio.ensure_future(main())
loop.run_forever()

loop.close()
