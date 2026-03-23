pipeline {
    agent any

    post {
        always {
            echo "=== DEBUG: Build Started for ${env.BRANCH_NAME} ==="
            echo "=== DEBUG: Commit ID is ${env.GIT_COMMIT} ==="
        }
    }

    environment {
        HVISOR_TOOL_URL = 'https://github.com/syswonder/hvisor-tool.git'
        HVISOR_TOOL_PATH = 'hvisor-tool'
        DEFAULT_SCRIPT_DIR = "./platform/aarch64/qemu-gicv3/scripts"
    }

    stages {
        stage("environment setup") {
            steps {
                sh """
                    . "/usr/local/cargo/env"
                    cargo --version
                """
            }
        }

        stage('Multi-Architecture Matrix Build') {
            matrix {
                axes {
                    axis {
                        name 'ARCH'
                        values 'riscv64'
                    }
                    axis {
                        name 'BOARD'
                        values 'qemu-plic'
                    }
                    axis {
                        name 'TARCH'
                        values 'riscv'
                    }
                    axis {
                        name 'KDIR'
                        values '/home/light/DEMO/linux/linux-6.10'
                    }
                }

                stages {
                    stage('Check Source Code & scripts') {
                        steps {
                            script {
                                echo "Checking [ARCH=${ARCH}, BOARD=${BOARD}]"

                                def specificDir = "platform/${ARCH}/${BOARD}/scripts"
                                def defaultDir = DEFAULT_SCRIPT_DIR

                                if (fileExists("${specificDir}/prepare.sh")) {
                                    env.CURRENT_PREPARE_SCRIPT = "${specificDir}/prepare.sh"
                                    echo "Using specific prepare script: ${env.CURRENT_PREPARE_SCRIPT}"
                                } else if (fileExists("${defaultDir}/prepare.sh")) {
                                    env.CURRENT_PREPARE_SCRIPT = "${defaultDir}/prepare.sh"
                                    echo "Using default prepare script: ${env.CURRENT_PREPARE_SCRIPT}"
                                } else {
                                    error "[${ARCH}/${BOARD}] No prepare.sh script found!"
                                }
                            }

                            script {
                                if (!fileExists("${HVISOR_TOOL_PATH}")) {
                                    sh "mkdir -p ${HVISOR_TOOL_PATH}"
                                }

                                dir(HVISOR_TOOL_PATH) {
                                    checkout([
                                        $class: 'GitSCM',
                                        branches: [[name: '*/main']],
                                        extensions: [[$class: 'CloneOption', depth: 1, noTags: true]],
                                        userRemoteConfigs: [[url: HVISOR_TOOL_URL]]
                                    ])
                                }
                            }
                        }
                    }

                    stage('Compile') {
                        steps {
                            echo "Compiling [ARCH=${ARCH}, BOARD=${BOARD}]"

                            sh """
                                make dtb ARCH=${ARCH} BOARD=${BOARD}
                                make all ARCH=${ARCH} BOARD=${BOARD} MODE=release

                                if [ -d "${HVISOR_TOOL_PATH}" ]; then
                                    cd ${HVISOR_TOOL_PATH}
                                    make all ARCH=${TARCH} KDIR=${KDIR} || true
                                fi
                            """
                        }
                    }

                    stage('Prepare Rootfs') {
                        steps {
                            script {
                                def externalFile = "/home/light/DEMO/syswonder/test_img/${ARCH}/${BOARD}"
                                def configure = "./platform/${ARCH}/${BOARD}/"

                                sh """
                                    cp -r ${externalFile}/* ${configure}
                                    chmod +x "${env.CURRENT_PREPARE_SCRIPT}"
                                    sudo "${env.CURRENT_PREPARE_SCRIPT}"
                                """
                            }
                        }
                    }

                    stage('Test') {
                        steps {
                            sh """
                                make run ARCH=${ARCH} BOARD=${BOARD}
                            """
                        }
                    }
                }
            }
        }
    }
}