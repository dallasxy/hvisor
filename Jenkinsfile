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
                            'aarch64/rk3568',
                        )
                    }
                }

                stages {
                    stage('Load CI config') {
                        steps {
                            script {
                                def cfg = readYaml file: "platform/${env.BID}/ci.yaml"
                                if (!cfg.build_args) {
                                    error("platform/${env.BID}/ci.yaml: missing build_args")
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
                                    error("platform/${env.BID}/ci.yaml: build_args must include ARCH and BOARD")
                                }
                                def localArch = buildArgs.ARCH
                                def localBoard = buildArgs.BOARD
                                def expectedBid = "${buildArgs.ARCH}/${buildArgs.BOARD}"
                                if (env.BID != expectedBid) {
                                    error("ci.yaml mismatch: BID axis is ${env.BID} but ARCH/BOARD imply ${expectedBid}")
                                }
                                if (!cfg.tests || cfg.tests.isEmpty()) {
                                    error("platform/${env.BID}/ci.yaml: tests must not be empty")
                                }
                                def names = cfg.tests.collect { it.name }
                                env.CI_HAS_COMPILE = names.contains('Compile') ? 'true' : 'false'
                                env.CI_HAS_QEMU_TEST = names.contains('Qemu Test') ? 'true' : 'false'
                                env.CI_HAS_BOARD_TEST = names.contains('Board Test') ? 'true' : 'false'
                                env.CI_NEEDS_HVISOR_TOOL = (env.CI_HAS_QEMU_TEST == 'true' || env.CI_HAS_BOARD_TEST == 'true') ? 'true' : 'false'

                                def qemuTestCfg = cfg.tests.find { it.name == 'Qemu Test' }
                                def qemuSteps = (qemuTestCfg?.steps ?: [])
                                env.CI_QEMU_TEST_STEPS = qemuSteps ? qemuSteps.join(',') : ''

                                if (env.CI_HAS_QEMU_TEST == 'true') {
                                    env.CURRENT_PREPARE_SCRIPT = "platform/${localArch}/${localBoard}/scripts/prepare.sh"
                                    env.CURRENT_TEST_SCRIPT = "platform/${localArch}/${localBoard}/scripts/run_qemu.sh"
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

                    stage('Compile') {
                        when {
                            expression { env.CI_HAS_COMPILE == 'true' }
                        }
                        steps {
                            script {
                                def bidParts = (env.BID ?: '').tokenize('/')
                                if (bidParts.size() != 2) {
                                    error("invalid BID format '${env.BID}', expected ARCH/BOARD")
                                }
                                def arch = bidParts[0]
                                def board = bidParts[1]
                                def fns = load 'jenkins/ciTestFns.groovy'
                                fns.runCompile([arch: arch, board: board])
                            }
                        }
                    }

                    stage('Build hvisor-tool') {
                        when {
                            expression { env.CI_NEEDS_HVISOR_TOOL == 'true' }
                        }
                        steps {
                            script {
                                def cfg = readYaml file: "platform/${env.BID}/ci.yaml"
                                if (!cfg.build_args) {
                                    error("platform/${env.BID}/ci.yaml: missing build_args")
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
                                def tarch = buildArgs.TARCH
                                def kdir = buildArgs.KDIR
                                if (!tarch || !kdir) {
                                    error("platform/${env.BID}/ci.yaml: build_args must include TARCH and KDIR for hvisor-tool")
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

                    stage('Qemu Test') {
                        when {
                            expression { env.CI_HAS_QEMU_TEST == 'true' }
                        }
                        steps {
                            script {
                                def bidParts = (env.BID ?: '').tokenize('/')
                                if (bidParts.size() != 2) {
                                    error("invalid BID format '${env.BID}', expected ARCH/BOARD")
                                }
                                def arch = bidParts[0]
                                def board = bidParts[1]
                                echo "Prepare rootfs (for Qemu Test only) [BID=${env.BID}, ARCH=${arch}, BOARD=${board}]"
                                def externalFile = "${env.TEST_IMG_BASE}/${arch}/${board}"
                                def configure = "./platform/${arch}/${board}/"
                                sh """
                                    cp -r ${externalFile}/* ${configure}
                                    chmod +x "${env.CURRENT_PREPARE_SCRIPT}"
                                    sudo -E "${env.CURRENT_PREPARE_SCRIPT}"
                                """
                                def fns = load 'jenkins/ciTestFns.groovy'
                                fns.runQemuTest([arch: arch, board: board])
                            }
                        }
                    }

                    stage('Board Test') {
                        when {
                            expression { env.CI_HAS_BOARD_TEST == 'true' }
                        }
                        steps {
                            script {
                                def bidParts = (env.BID ?: '').tokenize('/')
                                if (bidParts.size() != 2) {
                                    error("invalid BID format '${env.BID}', expected ARCH/BOARD")
                                }
                                def arch = bidParts[0]
                                def board = bidParts[1]
                                def fns = load 'jenkins/ciTestFns.groovy'
                                fns.runBoardTest([arch: arch, board: board])
                            }
                        }
                    }
                }
            }
        }
    }
}
