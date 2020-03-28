pipeline {
  agent {
    kubernetes {
      defaultContainer 'jnlp'
      yaml """
apiVersion: v1
kind: Pod
metadata:
  namespace: mgt
  name: redcloud3-builder
  labels:
    app: redcloud3-builder
spec:
  serviceAccountName: jenkins
  containers:
  - name: kaniko
    image: gcr.io/kaniko-project/executor:debug-v0.17.1
    imagePullPolicy: Always
    command:
    - /busybox/sh
    - "-c"
    args:
    - /busybox/cat
    tty: true
    volumeMounts:
      - name: jenkins-docker-cfg
        mountPath: /kaniko/.docker
  - name: ubuntu
    image: ubuntu:18.04
    command:
    - cat
    tty: true
  - name: python
    image: python:2.7
    command:
    - cat
    tty: true
  - name: maven
    image: maven:3.6.1-jdk-8-alpine
    command:
    - cat
    tty: true
    volumeMounts:
      - name: maven-m2-repository
        mountPath: /root/.m2/repository
      - name: maven-settings
        mountPath: /root/.m2
  - name: selenium
    image: selenium/standalone-chrome:3.141.59
  - name: zap
    image: owasp/zap2docker-stable:2.9.0
    command:
    - cat
    tty: true
    env:
    - name: MY_POD_IP
      valueFrom:
        fieldRef:
          fieldPath: status.podIP
  volumes:
  - name: maven-m2-repository
    persistentVolumeClaim:
      claimName: jenkins-agent
  - name: maven-settings
    configMap:
      name: jenkins-agent-maven-settings
      items:
        - key: settings.xml
          path: settings.xml
  - name: jenkins-docker-cfg
    projected:
      sources:
      - secret:
          name: docker-registry-credentials
          items:
            - key: .dockerconfigjson
              path: config.json
"""
    }
  }

  environment {
    MANAGEMENT_NAMESPACE = "mgt"
    GITHUB_GROUP = "green-redcloud3"
    GITHUB_PROJECT = "spring-petclinic"
    GITHUB_PROJECT_URL = "https://github.com/green-redcloud3/spring-petclinic"
    DEVCLOUD_REGISTRY_ADDRESS = "docker-nexus.mgt.green.perspectatechdemos.com"
    QUAY_REGISTRY_ADDRESS = "quay-quay-enterprise.apps.green.perspectatechdemos.com"
    APPLICATION_MAJOR_VERSION = "1"
    APPLICATION_MINOR_VERSION = "0"
    DEVCLOUD_DOCKER_TAG = "${DEVCLOUD_REGISTRY_ADDRESS}/${GITHUB_PROJECT}:${APPLICATION_MAJOR_VERSION}.${APPLICATION_MINOR_VERSION}.${env.BUILD_NUMBER}"
    DEVCLOUD_BRANCH_TAG = "master"
    MATTERMOST_CHANNEL = "green-redcloud3-spring-petclinic"
    MATTERMOST_WEBHOOK = "https://mattermost.mgt.green.perspectatechdemos.com/hooks/8sddzhr8x7d57nfbm7echm37py"
    ARTIFACTORY_URL = "https://artifactory.mgt.green.perspectatechdemos.com"
    NEXUS_ARTIFACT_URL = "https://nexus.mgt.green.perspectatechdemos.com/#browse/search/docker"
    SONARQUBE_URL = "https://sonarqube.mgt.green.perspectatechdemos.com"
    // we set this for now as there is some weirdness related to BUILD_URL env variable
    // definitely not best practice
    BUILD_URL = "https://jenkins.mgt.green.perspectatechdemos.com/job/green-redcloud3/job/spring-petclinic/job/${BRANCH_NAME}/${BUILD_NUMBER}"
    DEV_DEPLOYMENT_URL = "https://green-redcloud3-spring-petclinic.dev.green.perspectatechdemos.com"
    TEST_DEPLOYMENT_URL = "https://green-redcloud3-spring-petclinic.test.green.perspectatechdemos.com"
    PROD_DEPLOYMENT_URL = "https://green-redcloud3-spring-petclinic.prod.green.perspectatechdemos.com"
    REPOSITORY_SOURCE_FOLDER = "."
  }

  // triggers { pollSCM '* * * * *' }
  options {
    disableConcurrentBuilds()
    skipDefaultCheckout()
  }

  stages {
    stage('Build') {
      steps {
        updateGitlabCommitStatus name: 'build', state: 'pending'
        container('maven') {
          sh 'env; pwd;ls -al'
	  checkout changelog: false, poll: false, scm: [$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'green-redcloud3-token', url: "${GITHUB_PROJECT_URL}.git"]]] 
          dir('.') {
            sh 'ls -al'
            sh 'mvn compile'
          }
        }
        mattermostSend channel: "${MATTERMOST_CHANNEL}", endpoint: "${MATTERMOST_WEBHOOK}", message: "Job: ${JOB_NAME} \nStage: ${STAGE_NAME}\nBuild: ${BUILD_URL}\nCommit: ${GITHUB_PROJECT_URL}"
      }
    }
    stage('Test') {
      steps {
        container('maven') {
          dir('.') {
            sh 'ls -al'
            sh 'mvn test'
          }
        }
        mattermostSend channel: "${MATTERMOST_CHANNEL}", endpoint: "${MATTERMOST_WEBHOOK}", message: "Job: ${JOB_NAME} \nStage: ${STAGE_NAME}\nBuild: ${BUILD_URL}\nCommit: ${GITHUB_PROJECT_URL}"
      }
    }
    stage('SAST') {
      steps {
        container('maven') {
          dir('.') {
            withSonarQubeEnv('sonarqube') { 
            sh "mvn compile && mvn sonar:sonar -Dsonar.projectKey=${GITHUB_GROUP}-${GITHUB_PROJECT}"
            }
          }
        }
        mattermostSend channel: "${MATTERMOST_CHANNEL}", endpoint: "${MATTERMOST_WEBHOOK}", message: "Job: ${JOB_NAME} \nStage: ${STAGE_NAME}\nBuild: ${BUILD_URL}\nCommit: ${GITHUB_PROJECT_URL}\nStatic Application Security Test: ${SONARQUBE_URL}/dashboard?id=${GITHUB_GROUP}-${GITHUB_PROJECT}"
      }
    }
    stage('SAST Quality Gate') {
      steps {
        container('maven') {
          timeout(time: 10, unit: 'MINUTES') {
              waitForQualityGate abortPipeline: true
            }
        }
        mattermostSend channel: "${MATTERMOST_CHANNEL}", endpoint: "${MATTERMOST_WEBHOOK}", message: "Job: ${JOB_NAME} \nStage: ${STAGE_NAME}\nBuild: ${BUILD_URL}\nCommit: ${GITHUB_PROJECT_URL}\nQuality Gate: ${SONARQUBE_URL}/dashboard?id=${GITHUB_GROUP}-${GITHUB_PROJECT}"
      }
    }    
    stage('Package') {
      steps {
        container(name: 'kaniko', shell: '/busybox/sh') {
          dir('.') {
            withEnv(['PATH+EXTRA=/busybox']) {
              retry(3) {
              sh '''#!/busybox/sh
              /kaniko/executor --whitelist-var-run --context `pwd` --destination ${DEVCLOUD_DOCKER_TAG}
              '''
            }
          }
        }
        }
        mattermostSend channel: "${MATTERMOST_CHANNEL}", endpoint: "${MATTERMOST_WEBHOOK}", message: "Job: ${JOB_NAME} \nStage: ${STAGE_NAME}\nBuild: ${BUILD_URL}\nCommit: ${GITHUB_PROJECT_URL}\nArtifact: ${NEXUS_ARTIFACT_URL}"
      }
    }
    stage('Deploy Dev') {
      steps {
        container('ubuntu') {
            sh "apt update -y && apt-get install wget git -y"
            checkout changelog: false, poll: false, scm: [$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'green-redcloud3-token', url: "${GITHUB_PROJECT_URL}.git"]]]
            sh "cd /usr/local/bin && wget https://redcloud3.s3.amazonaws.com/tools/oc-4.3.2-linux.tar.gz && tar -xvf oc-4.3.2-linux.tar.gz"
          dir('.') {
            sh "sed 's#__PROJECT__#dev#g' springboot.yaml > springboot-dev.yaml"
            sh "sed -i 's#__IMAGE_TAG__#${DEVCLOUD_DOCKER_TAG}#' springboot-dev.yaml"
            sh "cat springboot-dev.yaml"
            sh "oc apply -f springboot-dev.yaml"
          }
        }
        mattermostSend channel: "${MATTERMOST_CHANNEL}", endpoint: "${MATTERMOST_WEBHOOK}", message: "Job: ${JOB_NAME} \nStage: ${STAGE_NAME}\nBuild: ${BUILD_URL}\nCommit: ${GITHUB_PROJECT_URL}\nDevelopment URL: ${DEV_DEPLOYMENT_URL}"
      }
    }
    stage('Validate Dev') {
      steps {
        container('maven') {
          sh "echo 'selenium script validation'"
        }
        mattermostSend channel: "${MATTERMOST_CHANNEL}", endpoint: "${MATTERMOST_WEBHOOK}", message: "Job: ${JOB_NAME} \nStage: ${STAGE_NAME}\nBuild: ${BUILD_URL}\nCommit: ${GITHUB_PROJECT_URL}\nDevelopment URL: ${DEV_DEPLOYMENT_URL}"
      }
    }
    stage('ZAP Scan Dev') {
      steps {
        container('zap') {
          sh "/zap/zap.sh -quickurl ${DEV_DEPLOYMENT_URL} -cmd -quickprogress -quickout \${WORKSPACE}/\${REPOSITORY_SOURCE_FOLDER}/zap_scan_dev.xml"
        }
        container('python') {
          sh "echo 'this is the python container'"
          sh "pwd"
          sh "pip install lxml"
          sh "ls -al \${WORKSPACE}/\${REPOSITORY_SOURCE_FOLDER}"
          sh "cd \${WORKSPACE}/\${REPOSITORY_SOURCE_FOLDER}; python zap_scan_dev.py"
          sh "ls -al \${WORKSPACE}/"
          sh "ls -al \${WORKSPACE}/\${REPOSITORY_SOURCE_FOLDER}"
          sh "cp -f \${WORKSPACE}/\${REPOSITORY_SOURCE_FOLDER}/zap_scan_dev.xml \${WORKSPACE}/zap_scan_dev.xml || true"
          sh "cp -f \${WORKSPACE}/\${REPOSITORY_SOURCE_FOLDER}/zap_scan_dev.html \${WORKSPACE}/zap_scan_dev.html || true"
          archiveArtifacts(artifacts: 'zap_scan_dev.xml')
          archiveArtifacts(artifacts: 'zap_scan_dev.html')
        }
        mattermostSend channel: "${MATTERMOST_CHANNEL}", endpoint: "${MATTERMOST_WEBHOOK}", message: "Job: ${JOB_NAME} \nStage: ${STAGE_NAME}\nZAP Scan Dev: ${BUILD_URL}\nCommit: ${GITHUB_PROJECT_URL}\nDevelopment URL: ${DEV_DEPLOYMENT_URL}"
      }
    }    
    stage('Deploy Test') {
      steps {
        container('ubuntu') {
          dir('.') {
            sh "sed 's#__PROJECT__#test#g' springboot.yaml > springboot-test.yaml"
            sh "sed -i 's#__IMAGE_TAG__#${DEVCLOUD_DOCKER_TAG}#' springboot-test.yaml"
            sh "cat springboot-test.yaml"
            sh "oc apply -f springboot-test.yaml"
          }
        }
        mattermostSend channel: "${MATTERMOST_CHANNEL}", endpoint: "${MATTERMOST_WEBHOOK}", message: "Job: ${JOB_NAME} \nStage: ${STAGE_NAME}\nBuild: ${BUILD_URL}\nCommit: ${GITHUB_PROJECT_URL}\nTest URL: ${TEST_DEPLOYMENT_URL}"
      }
    }
    stage('Validate Test') {
      steps {
        container('maven') {
          sh "echo 'selenium script validation'"
        }
        mattermostSend channel: "${MATTERMOST_CHANNEL}", endpoint: "${MATTERMOST_WEBHOOK}", message: "Job: ${JOB_NAME} \nStage: ${STAGE_NAME}\nBuild: ${BUILD_URL}\nCommit: ${GITHUB_PROJECT_URL}\nTest URL: ${TEST_DEPLOYMENT_URL}"
      }
    }
    stage('Deploy Prod') {
      steps {
        container('ubuntu') {
          dir('.') {
            sh "sed 's#__PROJECT__#prod#g' springboot.yaml > springboot-prod.yaml"
            sh "sed -i 's#__IMAGE_TAG__#${DEVCLOUD_DOCKER_TAG}#' springboot-prod.yaml"
            sh "cat springboot-prod.yaml"
            sh "oc apply -f springboot-prod.yaml"
          }
        }
        mattermostSend channel: "${MATTERMOST_CHANNEL}", endpoint: "${MATTERMOST_WEBHOOK}", message: "Job: ${JOB_NAME} \nStage: ${STAGE_NAME}\nBuild: ${BUILD_URL}\nCommit: ${GITHUB_PROJECT_URL}\nProduction URL: ${PROD_DEPLOYMENT_URL}"
      }
    }
    stage('Validate Prod') {
      steps {
        container('maven') {
          sh "echo 'selenium script validation'"
        }
        mattermostSend channel: "${MATTERMOST_CHANNEL}", endpoint: "${MATTERMOST_WEBHOOK}", message: "Job: ${JOB_NAME} \nStage: ${STAGE_NAME}\nBuild: ${BUILD_URL}\nCommit: ${GITHUB_PROJECT_URL}\nProduction URL: ${PROD_DEPLOYMENT_URL}"
      }
    }       

   }

  post {
    success {
      // mail body: "SUCCESS\nJob: ${JOB_NAME} \nStage: ${STAGE_NAME}\nBuild: ${BUILD_URL}\nCommit: ${GITHUB_PROJECT_URL}", from: 'jenkins@localhost', replyTo: 'jenkins@localhost', subject: "Build ${GITHUB_PROJECT}", to: 'jenkins@localhost'
      mattermostSend channel: "${MATTERMOST_CHANNEL}", endpoint: "${MATTERMOST_WEBHOOK}", message: "SUCCESS\nJob: ${JOB_NAME} \nStage: ${STAGE_NAME}\nBuild: ${BUILD_URL}\nCommit: ${GITHUB_PROJECT_URL}"
      updateGitlabCommitStatus name: 'build', state: 'success'
    }
    failure {
      // mail body: "SUCCESS\nJob: ${JOB_NAME} \nStage: ${STAGE_NAME}\nBuild: ${BUILD_URL}\nCommit: ${GITHUB_PROJECT_URL}", from: 'jenkins@localhost', replyTo: 'jenkins@localhost', subject: "FAILURE Build ${GITHUB_PROJECT}", to: 'jenkins@localhost'
      mattermostSend channel: "${MATTERMOST_CHANNEL}", endpoint: "${MATTERMOST_WEBHOOK}", message: "FAILED\nJob: ${JOB_NAME} \nStage: ${STAGE_NAME}\nBuild: ${BUILD_URL}\nCommit: ${GITHUB_PROJECT_URL}"
      updateGitlabCommitStatus name: 'build', state: 'failed'
    }
  }
}
