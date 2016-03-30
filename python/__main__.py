import select
import asyncio
import json
import sys

from objects import Keg, SocketProtocol, handle_message
import virtual

with open('config.json') as f:
    config = json.load(f)

def stdin_reader():
    data = sys.stdin.readline()
    asyncio.ensure_future(queue.put(data))


@asyncio.coroutine
def main():
    serial_devices = virtual.retrieve_devices_by_serial()

    for kegid, val in config['kegs'].items():
        if val.get('virtual') or kegid == 'test':
            keg = Keg(val['name'], True)

        # is port specified, is that port auto, is a serial id provided
        elif val.get('port') and val['port'] == 'auto' and val.get('serial_id') in serial_devices:
            serial_id = val.get('serial_id')
            loc = serial_devices[serial_id]
            print('found device at {}'.format(repr(loc)))
            keg = Keg(val['name'], False, port=loc)

        # is port specified, is that port explicit
        elif val.get('port'):
            keg = Keg(val['name'], False, port=val['port'])

        # probably virtual
        else:
            keg = Keg(val['name'], False, port=val['port'])

        yield from keg.init_connection()

        print('now waiting on ready from device...')

        welcome_message = yield from keg.create_task(keg.welcome, 10)

    loop.add_reader(sys.stdin, stdin_reader)

    print(SocketProtocol.items)
    while True:
        val = yield from queue.get()
        if val in ['quit', 'exit']:
            break

        print(SocketProtocol.items)
        #print(handle_message(val))



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
