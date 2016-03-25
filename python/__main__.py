import asyncio
import json

from objects import Keg, SocketProtocol

with open('config.json') as f:
    config = json.load(f)

@asyncio.coroutine
def main():
    temps_tasks = []
    for kegid, val in config['kegs'].items():
        if val.get('virtual') or kegid == 'test':
            keg = Keg(val['name'], True)

        else:
            keg = Keg(val['name'], False, port=val['port'])

        yield from keg.init_connection()

        print('now waiting on ready from device...')

        welcome_message = yield from keg.create_task(keg.welcome, 10)

        #yield from keg.connection_ready

        #temps_task = keg.get_temps(10)
        #temps_tasks.append(temps_task)

    #yield from asyncio.wait(temps_tasks)


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
    
    loop.run_until_complete(main())
    loop.run_forever()
    loop.close()
