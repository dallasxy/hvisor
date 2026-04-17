// Parallel matrix branches share Run-scoped env.* — do not store per-BID flags in env.
// Use ${WORKSPACE}/.jenkins-matrix/<BID>/ marker files for when { } and read ci.yaml in steps.

def parseCiBuildArgs(cfg) {
    def buildArgs = [:]
    if (!cfg.build_args) {
        return buildArgs
    }
    cfg.build_args.each { item ->
        if (item instanceof Map) {
            item.each { k, v ->
                buildArgs[k.toString()] = v.toString()
            }
        } else {
            def parts = item.toString().split('=', 2)
            if (parts.size() == 2) {
                buildArgs[parts[0]] = parts[1]
            }
        }
    }
    return buildArgs
}

def matrixCiMarkerPath(String marker) {
    def bid = env.BID ?: ''
    return "${env.WORKSPACE}/.jenkins-matrix/${bid.replace('/', '__')}/${marker}"
}

// Per-BID checkout tree for make/cargo (target/, .config, etc.). Path from env.BID only — not env.CI_*.
def matrixCellDir() {
    def bid = env.BID ?: ''
    return "${env.WORKSPACE}/.matrix/${bid.replace('/', '__')}"
}

def ciConfigPath(String bid) {
    return "jenkins/ci_${(bid ?: '').replace('/', '_')}.yaml"
}

pipeline {
    agent any

    options {
        timestamps()
    }

    post {
        always {
            echo "=== DEBUG: Branch ${env.BRANCH_NAME} ==="
            echo "=== DEBUG: Commit ${env.GIT_COMMIT} ==="
        }
    }

    environment {
        HVISOR_TOOL_URL = 'https://github.com/syswonder/hvisor-tool.git'
        HVISOR_TOOL_PATH = 'hvisor-tool'
        RUST_HOME = '/usr/local/rustup'
        CARGO_HOME = '/usr/local/cargo'
        QEMU_PATH = '/home/light/DEMO/qemu-9.2.3/build'
        TEST_IMG_BASE = '/home/light/DEMO/syswonder/test_img'
        RISCV_TOOLCHAIN_PATH = '/home/light/DEMO/toolchain/riscv64-glibc-ubuntu-24.04-gcc'
        AARCH64_TOOLCHAIN_PATH = '/home/light/DEMO/toolchain/gcc-arm-10.3-2021.07-x86_64-aarch64-none-linux-gnu'
        // All toolchain bins on PATH; same for every matrix cell (no per-arch selection).
        TOOLCHAIN_PATHS = "${env.RISCV_TOOLCHAIN_PATH}/bin:${env.AARCH64_TOOLCHAIN_PATH}/bin"
    }


    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Multi-Platform Matrix') {
            matrix {
                axes {
                    axis {
                        name 'BID'
                        values(
                            'riscv64/qemu-plic',
                            // 'aarch64/rk3568',
                            // 'aarch64/qemu-gicv3',
                        )
                    }
                }

                stages {
                    stage('Load CI config') {
                        steps {
                            script {
                                def cfgFile = ciConfigPath(env.BID)
                                def cfg = readYaml file: cfgFile
                                if (!cfg.build_args) {
                                    error("${cfgFile}: missing build_args")
                                }
                                def buildArgs = [:]
                                cfg.build_args.each { item ->
                                    if (item instanceof Map) {
                                        item.each { k, v ->
                                            buildArgs[k.toString()] = v.toString()
                                        }
                                    } else {
                                        def parts = item.toString().split('=', 2)
                                        if (parts.size() == 2) {
                                            buildArgs[parts[0]] = parts[1]
                                        }
                                    }
                                }
                                if (!buildArgs.ARCH || !buildArgs.BOARD) {
                                    error("${cfgFile}: build_args must include ARCH and BOARD")
                                }
                                def localArch = buildArgs.ARCH
                                def localBoard = buildArgs.BOARD
                                def expectedBid = "${buildArgs.ARCH}/${buildArgs.BOARD}"
                                if (env.BID != expectedBid) {
                                    error("ci.yaml mismatch: BID axis is ${env.BID} but ARCH/BOARD imply ${expectedBid}")
                                }
                                if (!cfg.tests || cfg.tests.isEmpty()) {
                                    error("${cfgFile}: tests must not be empty")
                                }
                                def names = cfg.tests.collect { it.name }
                                def stateDir = "${env.WORKSPACE}/.jenkins-matrix/${(env.BID ?: '').replace('/', '__')}"
                                sh """
                                    mkdir -p '${stateDir}'
                                    rm -f '${stateDir}'/want_compile '${stateDir}'/want_qemu '${stateDir}'/want_board '${stateDir}'/need_hvisor_tool 2>/dev/null || true
                                """
                                if (names.contains('Compile')) {
                                    writeFile file: "${stateDir}/want_compile", text: ''
                                }
                                if (names.contains('Qemu Test')) {
                                    writeFile file: "${stateDir}/want_qemu", text: ''
                                }
                                if (names.contains('Board Test')) {
                                    writeFile file: "${stateDir}/want_board", text: ''
                                }
                                if (names.contains('Qemu Test') || names.contains('Board Test')) {
                                    writeFile file: "${stateDir}/need_hvisor_tool", text: ''
                                }

                                def testsLines = names.collect { "    - ${it}" }.join('\n')
                                echo """========================================
  BID: ${env.BID}
  Tests to run:
${testsLines}
========================================"""
                            }
                        }
                    }

                    // Isolate Rust target/, .config, platform/*/generated, etc. Parallel matrix + one WORKSPACE => cross-ARCH pollution without this.
                    stage('Prepare cell workspace') {
                        steps {
                            script {
                                def cellWs = matrixCellDir()
                                sh """
                                    mkdir -p '${cellWs}'
                                    rsync -a --delete \\
                                        --exclude '.matrix/' \\
                                        --exclude '.jenkins-matrix/' \\
                                        '${env.WORKSPACE}/' '${cellWs}/'
                                """
                            }
                        }
                    }

                    stage('Compile') {
                        when {
                            expression { return fileExists(matrixCiMarkerPath('want_compile')) }
                        }
                        steps {
                            dir(matrixCellDir()) {
                                script {
                                    def cfgFile = ciConfigPath(env.BID)
                                    def cfg = readYaml file: cfgFile
                                    def buildArgs = parseCiBuildArgs(cfg)
                                    def arch = buildArgs.ARCH
                                    def board = buildArgs.BOARD
                                    if (!arch || !board) {
                                        error("${cfgFile}: build_args must include ARCH and BOARD")
                                    }
                                    if ("${arch}/${board}" != env.BID) {
                                        error("Compile: ${cfgFile} ARCH/BOARD (${arch}/${board}) != BID axis (${env.BID})")
                                    }
                                    def fns = load "${WORKSPACE}/jenkins/ciTestFns.groovy"
                                    fns.runCompile([arch: arch, board: board])
                                }
                            }
                        }
                    }

                    stage('Build hvisor-tool') {
                        when {
                            expression { return fileExists(matrixCiMarkerPath('need_hvisor_tool')) }
                        }
                        steps {
                            dir(matrixCellDir()) {
                                script {
                                    def cfgFile = ciConfigPath(env.BID)
                                    def cfg = readYaml file: cfgFile
                                    def buildArgs = parseCiBuildArgs(cfg)
                                    if (!cfg.build_args) {
                                        error("${cfgFile}: missing build_args")
                                    }
                                    def tarch = buildArgs.TARCH
                                    def kdir = buildArgs.KDIR
                                    if (!tarch || !kdir) {
                                        error("${cfgFile}: build_args must include TARCH and KDIR for hvisor-tool")
                                    }
                                    echo "Build hvisor-tool [BID=${env.BID}, TARCH=${tarch}, KDIR=${kdir}]"
                                    if (!fileExists(env.HVISOR_TOOL_PATH)) {
                                        sh "mkdir -p ${env.HVISOR_TOOL_PATH}"
                                    }
                                    dir(env.HVISOR_TOOL_PATH) {
                                        checkout([
                                            $class: 'GitSCM',
                                            branches: [[name: '*/main']],
                                            extensions: [[$class: 'CloneOption', depth: 1, noTags: true]],
                                            userRemoteConfigs: [[url: env.HVISOR_TOOL_URL]]
                                        ])
                                    }
                                    sh """
                                        export PATH=${env.TOOLCHAIN_PATHS}:\$PATH
                                        cd ${env.HVISOR_TOOL_PATH}
                                        make all ARCH=${tarch} KDIR=${kdir}
                                    """
                                }
                            }
                        }
                    }

                    stage('Qemu Test') {
                        when {
                            expression { return fileExists(matrixCiMarkerPath('want_qemu')) }
                        }
                        steps {
                            dir(matrixCellDir()) {
                                script {
                                    def cfgFile = ciConfigPath(env.BID)
                                    def cfg = readYaml file: cfgFile
                                    def buildArgs = parseCiBuildArgs(cfg)
                                    def arch = buildArgs.ARCH
                                    def board = buildArgs.BOARD
                                    if (!arch || !board) {
                                        error("${cfgFile}: build_args must include ARCH and BOARD")
                                    }
                                    def qemuTestCfg = cfg.tests.find { it.name == 'Qemu Test' }
                                    def qemuStepsList = (qemuTestCfg?.steps ?: [])
                                    def qemuSteps = qemuStepsList ? qemuStepsList.join(',') : ''
                                    def prepareScript = "platform/${arch}/${board}/scripts/prepare.sh"
                                    echo "Prepare rootfs (for Qemu Test only) [BID=${env.BID}, ARCH=${arch}, BOARD=${board}]"
                                    def externalFile = "${env.TEST_IMG_BASE}/${arch}/${board}"
                                    def configure = "./platform/${arch}/${board}/"
                                    sh """
                                        cp -r ${externalFile}/* ${configure}
                                        chmod +x "${prepareScript}"
                                        sudo -E "${prepareScript}"
                                    """
                                    def fns = load "${WORKSPACE}/jenkins/ciTestFns.groovy"
                                    fns.runQemuTest([
                                        arch      : arch,
                                        board     : board,
                                        qemuSteps : qemuSteps
                                    ])
                                }
                            }
                        }
                    }

                    stage('Board Test') {
                        when {
                            expression { return fileExists(matrixCiMarkerPath('want_board')) }
                        }
                        steps {
                            dir(matrixCellDir()) {
                                script {
                                    def cfgFile = ciConfigPath(env.BID)
                                    def cfg = readYaml file: cfgFile
                                    def buildArgs = parseCiBuildArgs(cfg)
                                    def arch = buildArgs.ARCH
                                    def board = buildArgs.BOARD
                                    if (!arch || !board) {
                                        error("${cfgFile}: build_args must include ARCH and BOARD")
                                    }
                                    def boardTestCfg = cfg.tests.find { it.name == 'Board Test' }
                                    def boardSteps = (boardTestCfg?.steps ?: [])
                                    def boardTests = boardSteps ? boardSteps.join(',') : 'start_zone1'
                                    def fns = load "${WORKSPACE}/jenkins/ciTestFns.groovy"
                                    fns.runBoardTest([arch: arch, board: board, boardTests: boardTests])
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
