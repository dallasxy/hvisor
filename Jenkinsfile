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
                                cfg.build_args.each { line ->
                                    def parts = line.toString().split('=', 2)
                                    if (parts.size() == 2) {
                                        env."${parts[0]}" = parts[1]
                                    }
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

                                def expectedBid = "${env.ARCH}/${env.BOARD}"
                                if (env.BID != expectedBid) {
                                    error("ci.yaml mismatch: BID axis is ${env.BID} but ARCH/BOARD imply ${expectedBid}")
                                }

                                if (env.ARCH == 'riscv64') {
                                    env.PATH_TOOLCHAIN = "${env.RISCV_TOOLCHAIN_PATH}/bin"
                                } else if (env.ARCH == 'aarch64') {
                                    env.PATH_TOOLCHAIN = "${env.AARCH64_TOOLCHAIN_PATH}/bin"
                                } else {
                                    env.PATH_TOOLCHAIN = ''
                                }

                                if (env.CI_HAS_QEMU_TEST == 'true') {
                                    env.CURRENT_PREPARE_SCRIPT = "platform/${env.ARCH}/${env.BOARD}/scripts/prepare.sh"
                                    env.CURRENT_TEST_SCRIPT = "platform/${env.ARCH}/${env.BOARD}/scripts/run_qemu.sh"
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
                                def fns = load 'jenkins/ciTestFns.groovy'
                                fns.runCompile([:])
                            }
                        }
                    }

                    stage('Build hvisor-tool') {
                        when {
                            expression { env.CI_NEEDS_HVISOR_TOOL == 'true' }
                        }
                        steps {
                            echo "Build hvisor-tool [TARCH=${env.TARCH}, KDIR=${env.KDIR}]"
                            script {
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
                            }
                            sh """
                                export PATH=${env.PATH_TOOLCHAIN}:\$PATH
                                cd ${env.HVISOR_TOOL_PATH}
                                make all ARCH=${env.TARCH} KDIR=${env.KDIR}
                            """
                        }
                    }

                    stage('Prepare Rootfs') {
                        when {
                            expression { env.CI_HAS_QEMU_TEST == 'true' }
                        }
                        steps {
                            echo "Prepare rootfs [ARCH=${env.ARCH}, BOARD=${env.BOARD}]"
                            script {
                                def externalFile = "${env.TEST_IMG_BASE}/${env.ARCH}/${env.BOARD}"
                                def configure = "./platform/${env.ARCH}/${env.BOARD}/"
                                sh """
                                    cp -r ${externalFile}/* ${configure}
                                    chmod +x "${env.CURRENT_PREPARE_SCRIPT}"
                                    sudo -E "${env.CURRENT_PREPARE_SCRIPT}"
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
                                def fns = load 'jenkins/ciTestFns.groovy'
                                fns.runQemuTest([:])
                            }
                        }
                    }

                    stage('Board Test') {
                        when {
                            expression { env.CI_HAS_BOARD_TEST == 'true' }
                        }
                        steps {
                            script {
                                def fns = load 'jenkins/ciTestFns.groovy'
                                fns.runBoardTest([:])
                            }
                        }
                    }
                }
            }
        }
    }
}
