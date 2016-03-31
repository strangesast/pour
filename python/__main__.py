import asyncio
import json
import sys
import re

from objects import Keg, SocketProtocol, handle_message
import virtual

with open('config.json') as f:
    config = json.load(f)


class FakeProtocol:
    def __init__(self):
        return 'toast'

def stdin_reader():
    data = sys.stdin.readline()
    asyncio.ensure_future(queue.put(data))


@asyncio.coroutine
def main():
    serial_devices, serial_ports = virtual.retrieve_devices_by_serial()

    for kegid, val in config['kegs'].items():
        validport = re.match('\/dev\/\w+', val.get('port') or "")
        # is port specified, is that port auto, is a serial id provided
        if val.get('port') and val['port'] == 'auto' and val.get('serial_id') in serial_devices:
            serial_id = val.get('serial_id')
            loc = serial_devices[serial_id]
            print('found device at {}'.format(repr(loc)))
            keg = Keg(val['name'], False, port=loc)

        # is port specified, is that port explicit
        elif val.get('port') and val['port'] in serial_ports:
            keg = Keg(val['name'], False, port=val['port'])

        # probably virtual
        else:
            if not val.get('virtual'):
                print('\033[93m' + 'WARNING: assuming virtual port' + '\033[0m')

            keg = Keg(val['name'], True)

        yield from keg.init_connection()

        print('now waiting on ready from device...')

        welcome_message = yield from keg.create_task(keg.welcome, 10)

    loop.add_reader(sys.stdin, stdin_reader)

    fake_protocol = FakeProtocol()
    print('>>> ', end='')
    while True:
        val = yield from queue.get()
        if val in ['quit', 'exit']:
            break

        print(handle_message(fake_protocol, val) + '\n>>> ', end='')



if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    host = '127.0.0.1'
    port=25000
    server = loop.create_server(
            SocketProtocol,
            host=host,
            port=port)
    
    loop.run_until_complete(server)
    print("Listening at '{}:{}'".format(host, port))
    
    queue = asyncio.Queue()

    loop.run_until_complete(main())

    loop.close()
