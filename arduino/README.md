Folder contains code related to keg control / monitoring

To test without board, get simavr at https://github.com/buserror/simavr

In `board_simduino` run `obj-x86_64-linux-gnu/simduino.elf` to begin emulator

Run `avrdude -p m328p -c arduino -P /tmp/simavr-uart0 -U flash:w:ping.hex` to upload to board
