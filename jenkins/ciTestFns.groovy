// CI test functions used by root Jenkinsfile.
// Loaded via: load 'jenkins/ciTestFns.groovy'

def runCompile(Map ctx = [:]) {
    echo "Compile hvisor [BID=${env.BID}, ARCH=${env.ARCH}, BOARD=${env.BOARD}]"
    sh """
        export PATH=${env.CARGO_HOME}/bin:${env.PATH_TOOLCHAIN}:\$PATH
        make dtb ARCH=${env.ARCH} BOARD=${env.BOARD}
        make all ARCH=${env.ARCH} BOARD=${env.BOARD} MODE=release
    """
}

def runQemuTest(Map ctx = [:]) {
    def stepsStr = (env.CI_QEMU_TEST_STEPS ?: '').trim()
    echo "Qemu Test [ARCH=${env.ARCH}, BOARD=${env.BOARD}] steps='${stepsStr}'"

    def cmd = "\"${env.CURRENT_TEST_SCRIPT}\""
    if (stepsStr) {
        // Qemu scripts use kv-style argument: --steps a,b,c
        cmd += " --steps \"${stepsStr}\""
    }

    sh """
        export PATH=${env.CARGO_HOME}/bin:${env.QEMU_PATH}:\$PATH
        chmod +x "${env.CURRENT_TEST_SCRIPT}"
        ${cmd}
    """
}

def runBoardTest(Map ctx = [:]) {
    def scriptPath = "platform/${env.ARCH}/${env.BOARD}/scripts/board_test.sh"
    echo "Board Test [BID=${env.BID}, ARCH=${env.ARCH}, BOARD=${env.BOARD}]"
    sh """
        if [ ! -f "${scriptPath}" ]; then
            echo "SKIP: ${scriptPath} not found (placeholder; no automated board test for this platform)"
            exit 0
        fi
        chmod +x "${scriptPath}"
        cd "platform/${env.ARCH}/${env.BOARD}/scripts"
        sudo ./board_test.sh
    """
}

return this

