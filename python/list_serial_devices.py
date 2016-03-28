import re
from serial.tools import list_ports

import virtual

serials = virtual.retrieve_devices_by_serial()
print(serials)

print('641313833313510132E0' in serials)
