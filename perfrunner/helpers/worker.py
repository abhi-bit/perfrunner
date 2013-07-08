from uuid import uuid4

from celery import Celery
from celery.contrib.methods import task
from fabric.api import cd, run
from fabric import state
from logger import logger
from spring.wgen import WorkloadGen

from perfrunner.settings import BROKER_URL, REPO

celery = Celery('workers', broker=BROKER_URL)


class Worker(object):

    def __init__(self, host=None, ssh_username=None, ssh_password=None):
        if host and ssh_username and ssh_password:
            self.is_remote = True

            state.env.user = ssh_username
            state.env.password = ssh_password
            state.env.host_string = host
            state.env.warn_only = True
            state.output.running = False
            state.output.stdout = False

            self.temp_dir = '/tmp/{0}'.format(uuid4().hex[:12])
            self._initialize_project()
        else:
            self.is_remote = False

    def _initialize_project(self):
        logger.info('Intializing remote worker environment')
        run('mkdir {0}'.format(self.temp_dir))
        with cd(self.temp_dir):
            run('git clone {0}'.format(REPO))
            run('./perfrunner/scripts/env.sh')

    def start(self):
        if self.is_remote:
            logger.info('Starting remote Celery worker')
            with cd('{0}/perfrunner'.format(self.temp_dir)):
                run('/tmp/prenv/bin/celery worker -A perfrunner.helpers.worker 2>1 &')

    @task
    def task_run_workload(self, settings, target):
        wg = WorkloadGen(settings, target)
        wg.run()

    def run_workload(self, settings, target):
        if self.is_remote:
            self.task_run_workload.apply(settings, target)
        else:
            self.task_run_workload(settings, target)

    def terminate(self):
        if self.is_remote:
            logger.info('Terminating remote Celery worker')
            run('ps auxww|grep "celery worker"|awk "{print $2}"|xargs kill -9')

    def __del__(self):
        if self.is_remote:
            logger.info('Cleaning up remote worker environment')
            run('rm -fr {0}'.format(self.temp_dir))
