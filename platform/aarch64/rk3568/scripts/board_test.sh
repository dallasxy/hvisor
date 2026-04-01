#!/usr/bin/expect -f
#
# Open serial with screen. Run as root so spawn does not nest sudo (which often
# makes screen exit immediately under expect):  sudo ./board_test.sh
#

set env(LANG) "en_US.UTF-8"
set timeout 240

# trap "" SIGINT 

spawn screen /dev/ttyUSB0 1500000

# expect {
#     -re "Hit key to stop autoboot.*: *" {
#         # Send Ctrl+C
#         send "\x03"
#     }
#     timeout {
#         puts "Timeout waiting for autoboot message"
#         exit 1
#     }
# }

expect {
    -re "=> <INTERRUPT>" {
        Send "pci enum\r"
    }
    timeout {
        puts "Timeout waiting for interrupt message"
        exit 1
    }
}