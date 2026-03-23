#!/usr/bin/expect -f

set env(LANG) "en_US.UTF-8"
set timeout 240

send_user "\r============Starting automated script execution============\r"

spawn make run ARCH=riscv64 BOARD=qemu-plic

# Wait for root password prompt and U-Boot prompt
expect {
#    "password for chh: " {
#         puts "\r============Handling sudo password and U-Boot commands============\r"
#         send "$password\r"
#         exp_continue
#    }
   -re "char device redirected to /dev/pts.*(label X10007000)" {
        # Enter command at prompt
        send "\x01c"
   }
   timeout {
        exit 1
   }
}

expect {
    "(qemu)" {
        send "c\r"
    }
    timeout {
        exit 1
    }
}

puts "\n============Testing hvisor startup and virtio daemon============\n"

expect {
    -re {job control turned off.*#} {
        send "\x01cbash\r"
    }
    timeout {
        exit 1
    }
}

expect {
    "root@(none):/# " {
        send "cd /home/riscv\r"
    }
    timeout {
        exit 1
    }
}

expect eof
exit 0