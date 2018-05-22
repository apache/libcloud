"""
Module for Google Big Q Engine Driver.
"""

from google.cloud import bigquery
from google import oauth2
from google.api_core.exceptions import NotFound


API_VERSION = 'v1'
DEFAULT_TASK_COMPLETION_TIMEOUT = 180


class GoogleBQ(bigquery.Client):
    """ Google Big Query client """

    def __init__(self, credentials):
        """
        Init Google Big Query client
        :param credentials: dict. Credentials
        """
        project_id = credentials['project_id']
        credentials = oauth2.service_account.Credentials.from_service_account_info(credentials)
        super(GoogleBQ, self).__init__(project_id, credentials)


class GoogleBQBillingExcepton(Exception):
    pass


class GoogleBQBilling():
    """ Google Big Query client with business logic for billing """

    BILLING_TABLE_PREFIX = 'gcp_billing_export_v1_'
    BILLING_DATASET_NAME = 'billing'

    def __init__(self, credentials):
        self.client = GoogleBQ(credentials)
        self.billing_table = self._get_billing_table()

    def _get_billing_table(self):
        dataset_ref = self.client.dataset(self.BILLING_DATASET_NAME)
        try:
            for table in self.client.list_tables(dataset_ref):
                if table.table_id.startswith(self.BILLING_TABLE_PREFIX):
                    return table
        except NotFound:
            # list_tables raises exception if dataset is missing
            raise GoogleBQBillingExcepton('Project has not billing dataset')

        raise GoogleBQBillingExcepton('Project has not billing table')

    @property
    def billing_table_name(self):
        """ Use this value in FROM clause of query """
        return '{}.{}'.format(self.BILLING_DATASET_NAME, self.billing_table)

    def execute(self, query):
        """
        Execute query and return result. Result will be chunked.
        :param query: str. BQ query
        :return: dict which represent row from result
        """
        # prepare query, example:
        # SELECT * FROM {billing_table} LIMIT 1
        query_job = self.client.query(query)
        for row in query_job:
            yield dict(row.items())
