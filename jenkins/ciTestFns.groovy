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
    def stepsStr = (ctx.qemuSteps ?: '').toString().trim()
    echo "Qemu Test [BID=${env.BID}, ARCH=${arch}, BOARD=${board}] steps='${stepsStr}'"
    def testsArg = stepsStr ?: "zone0_start,zone1_start"

    sh """
        export PATH=${env.CARGO_HOME}/bin:${env.QEMU_PATH}:\$PATH
        python3 jenkins/ci_runner.py \
            --mode qemu \
            --arch "${arch}" \
            --board "${board}" \
            --test "${testsArg}" \
            --workspace "${pwd()}" \
            --log-file "${pwd()}/qemu_ci.log"
    """
}

def runBoardTest(Map ctx = [:]) {
    def arch = ctx.arch?.toString()
    def board = ctx.board?.toString()
    if (!arch || !board) {
        error("runBoardTest requires ctx.arch and ctx.board")
    }
    def testsArg = (ctx.boardTests ?: 'start_zone1').toString().trim()
    echo "Board Test [BID=${env.BID}, ARCH=${arch}, BOARD=${board}]"
    sh """
        python3 jenkins/ci_runner.py \
            --mode board \
            --arch "${arch}" \
            --board "${board}" \
            --test "${testsArg}" \
            --workspace "${pwd()}" \
            --log-file "${pwd()}/board_ci.log"
    """
}

return this

