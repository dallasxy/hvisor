// CI test functions used by root Jenkinsfile.
// Loaded via: load 'jenkins/ciTestFns.groovy'

def runCompile(Map ctx = [:]) {
    def arch = ctx.arch?.toString()
    def board = ctx.board?.toString()
    if (!arch || !board) {
        error("runCompile requires ctx.arch and ctx.board")
    }
    echo "Compile hvisor [BID=${env.BID}, ARCH=${arch}, BOARD=${board}]"
    sh """
        export PATH=${env.CARGO_HOME}/bin:${env.TOOLCHAIN_PATHS}:\$PATH
        make dtb ARCH=${arch} BOARD=${board}
        make all ARCH=${arch} BOARD=${board} MODE=release
    """
}

def runQemuTest(Map ctx = [:]) {
    def arch = ctx.arch?.toString()
    def board = ctx.board?.toString()
    if (!arch || !board) {
        error("runQemuTest requires ctx.arch and ctx.board")
    }
    def stepsStr = (env.CI_QEMU_TEST_STEPS ?: '').trim()
    echo "Qemu Test [BID=${env.BID}, ARCH=${arch}, BOARD=${board}] steps='${stepsStr}'"

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
    def arch = ctx.arch?.toString()
    def board = ctx.board?.toString()
    if (!arch || !board) {
        error("runBoardTest requires ctx.arch and ctx.board")
    }
    def scriptPath = "platform/${arch}/${board}/scripts/board_test.sh"
    echo "Board Test [BID=${env.BID}, ARCH=${arch}, BOARD=${board}]"
    sh """
        if [ ! -f "${scriptPath}" ]; then
            echo "SKIP: ${scriptPath} not found (placeholder; no automated board test for this platform)"
            exit 0
        fi
        chmod +x "${scriptPath}"
        cd "platform/${arch}/${board}/scripts"
        sudo ./board_test.sh
    """
}

return this

