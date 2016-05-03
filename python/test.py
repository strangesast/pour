import serial
import asyncio

class SerialProtocol(asyncio.Protocol):
    def __init__(self):
        self.current_data = bytearray()

    def connection_made(self, transport):
        self.transport = transport

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
def main():

    transport, protocol = yield from serial.aio.create_serial_connection(
            asyncio.get_event_loop(),
            lambda: SerialProtocol(self),
            port=self.pts,
            baudrate=9600)
 

    while True:
        print("1")
        yield from asyncio.sleep(1)

loop = asyncio.get_event_loop()

try:
    loop.run_until_complete(main())
except KeyboardInterrupt:
    pass
