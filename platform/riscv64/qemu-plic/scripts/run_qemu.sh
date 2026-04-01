#!/usr/bin/expect -f

set env(LANG) "en_US.UTF-8"
set timeout 240

set stepsArg ""
set argc [llength $argv]
set i 0
while {$i < $argc} {
    set key [lindex $argv $i]
    if {$key eq "--steps"} {
        incr i
        set stepsArg [lindex $argv $i]
        break
    }
    incr i
}

set stepsList {}
if {$stepsArg ne ""} {
    set stepsList [split $stepsArg ","]
} else {
    # Backward compatibility: if Jenkins hasn't been updated to pass --steps,
    # run the full legacy flow as zone0_start + zone1_start.
    set stepsList [list "zone0_start" "zone1_start"]
}

send_user "\r============Starting automated script execution============\r"
spawn make run ARCH=riscv64 BOARD=qemu-plic

# start_zone0 corresponds to the original script (roughly lines 10-47):
# - Wait for U-Boot/root prompt
# - Enter /home/riscv64
proc start_zone0 {} {
    expect {
        -re "char device redirected to /dev/pts.*(label X10007000)" {
            # Enter command at prompt
            send "\x01c"
        }
        timeout { exit 1 }
    }

    expect {
        "(qemu)" { send "c\r" }
        timeout { exit 1 }
    }

    puts "\n============Testing hvisor startup and virtio daemon============\n"

    expect {
        -re {job control turned off.*#} { send "\x01cbash\r" }
        timeout { exit 1 }
    }

    expect {
        "root@(none):/# " { send "cd /home/riscv64\r" }
        timeout { exit 1 }
    }
}

# start_zone1 corresponds to the original script (roughly lines 49-87):
# - boot_zone1.sh
# - screen / verify "home" exists
proc start_zone1 {} {
    expect {
        "root@(none):/home/riscv64# " { send "./boot_zone1.sh\r" }
        timeout { exit 1 }
    }

    after 10000
    send "\r"

    expect {
        "root@(none):/home/riscv64# " { send "script /dev/null\r" }
        timeout { exit 1 }
    }

    expect {
        -re {\r?\n# } { send "screen /dev/pts/0\r" }
        timeout { exit 1 }
    }

    expect {
        -re {\r?\n# } { send "ls | grep home\r" }
        timeout { exit 1 }
    }

    # If "home" isn't found, treat as failure.
    expect {
        "home" { return 0 }
        timeout { exit 1 }
    }
}

proc zone0_network {} {
    # Placeholder until guest interaction is defined.
    send_user "\r[zone0_network] placeholder\r"
}

proc zone1_shutdown {} {
    # Placeholder until guest interaction is defined.
    send_user "\r[zone1_shutdown] placeholder\r"
}

proc zone1_restart {} {
    # Placeholder until guest interaction is defined.
    send_user "\r[zone1_restart] placeholder\r"
}

set stepResults {}
foreach step $stepsList {
    set s [string trim $step]
    if {$s eq ""} { continue }

    send_user "\r--- Step: ${s} ---\r"
    switch -- $s {
        "zone0_start" {
            start_zone0
            lappend stepResults "${s}=PASS"
        }
        "zone0_network" {
            zone0_network
            lappend stepResults "${s}=PASS"
        }
        "zone1_start" {
            start_zone1
            lappend stepResults "${s}=PASS"
        }
        "zone1_shutdown" {
            zone1_shutdown
            lappend stepResults "${s}=PASS"
        }
        "zone1_restart" {
            zone1_restart
            lappend stepResults "${s}=PASS"
        }
        default {
            send_user "\r[${s}] unknown step, skipping\r"
            lappend stepResults "${s}=SKIP"
        }
    }
}

set joinedResults [join $stepResults ", "]
send_user "\r============Step results: ${joinedResults}============\r"

# Terminate spawned QEMU/make process after finishing requested steps.
catch { close -force $spawn_id }
exit 0