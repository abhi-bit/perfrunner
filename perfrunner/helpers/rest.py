import time

import requests
from logger import logger

from perfrunner.helpers import Helper


class RestHelper(Helper):

    def __init__(self, cluster_spec_fname, test_config_fname=None):
        super(RestHelper, self).__init__(cluster_spec_fname, test_config_fname)
        self.auth = (self.rest_username, self.rest_password)

    def get(self, **kwargs):
        return requests.get(auth=self.auth, **kwargs)

    def post(self, **kwargs):
        return requests.post(auth=self.auth, **kwargs)

    def set_data_path(self, host_port):
        logger.info('Configuring data paths: {0}'.format(host_port))

        API = 'http://{0}/nodes/self/controller/settings'.format(host_port)
        data = {
            'path': self.data_path, 'index_path': self.index_path
        }
        self.post(url=API, data=data)

    def set_auth(self, host_port):
        logger.info('Configuring cluster authentication: {0}'.format(host_port))

        API = 'http://{0}/settings/web'.format(host_port)
        data = {
            'username': self.rest_username, 'password': self.rest_password,
            'port': 'SAME'
        }
        self.post(url=API, data=data)

    def set_mem_quota(self, host_port, mem_quota):
        logger.info('Configuring memory quota: {0}'.format(host_port))

        API = 'http://{0}/pools/default'.format(host_port)
        data = {
            'memoryQuota': mem_quota
        }
        self.post(url=API, data=data)

    def add_node(self, host_port, new_host):
        logger.info('Adding new node: {0}'.format(new_host))

        API = 'http://{0}/controller/addNode'.format(host_port)
        data = {
            'hostname': new_host,
            'user': self.rest_username, 'password': self.rest_password
        }
        self.post(url=API, data=data)

    @staticmethod
    def ns_1(host_port):
        return 'ns_1@{0}'.format(host_port.split(':')[0])

    def rebalance(self, host_port, known_nodes, ejected_nodes):
        logger.info('Starting rebalance')

        API = 'http://{0}/controller/rebalance'.format(host_port)
        known_nodes = ','.join(map(self.ns_1, known_nodes))
        ejected_nodes = ','.join(ejected_nodes)
        data = {
            'knownNodes': known_nodes,
            'ejectedNodes': ejected_nodes
        }
        self.post(url=API, data=data)

    def get_tasks(self, host_port):
        API = 'http://{0}/pools/default/tasks'.format(host_port)
        return self.get(url=API).json()

    def get_rebalance_status(self, host_port):
        for task in self.get_tasks(host_port):
            if task['type'] == 'rebalance':
                is_running = bool(task['status'] == 'running')
                progress = task.get('progress')
                return is_running, progress

    def create_bucket(self, host_port, name, ram_quota, replica_number=1,
                      replica_index=0):
        logger.info('Adding new bucket: {0}'.format(name))

        API = 'http://{0}/pools/default/buckets'.format(host_port)
        data = {
            'name': name, 'bucketType': 'membase', 'ramQuotaMB': ram_quota,
            'replicaNumber': replica_number, 'replicaIndex': replica_index,
            'authType': 'sasl', 'saslPassword': ''
        }
        self.post(url=API, data=data)

    def configure_auto_compaction(self, host_port, settings):
        logger.info('Applying auto-compaction settings')

        API = 'http://{0}/controller/setAutoCompaction'.format(host_port)
        data = {
            'databaseFragmentationThreshold[percentage]': settings.db_percentage,
            'viewFragmentationThreshold[percentage]': settings.view_percentage,
            'parallelDBAndViewCompaction': str(settings.parallel).lower()
        }
        self.post(url=API, data=data)

    def get_bucket_stats(self, host_port, bucket):
        API = 'http://{0}/pools/default/buckets/{1}/stats'.format(host_port,
                                                                  bucket)
        return self.get(url=API).json()

    def add_remote_cluster(self, host_port, remote_host_port, name):
        logger.info('Adding remote cluster {0} with reference {1}'.format(
            remote_host_port, name
        ))

        API = 'http://{0}/pools/default/remoteClusters'.format(host_port)
        data = {
            'hostname': remote_host_port, 'name': name,
            'username': self.rest_username, 'password': self.rest_password
        }
        self.post(url=API, data=data)

    def start_replication(self, host_port, from_bucket, to_bucket, to_cluster):
        logger.info('Starting replication from {0} to {1} at {2}'.format(
            from_bucket, to_bucket, to_cluster
        ))

        API = 'http://{0}/controller/createReplication'.format(host_port)
        data = {
            'replicationType': 'continuous',
            'toBucket': from_bucket, 'fromBucket': to_bucket,
            'toCluster': to_cluster
        }
        self.post(url=API, data=data)