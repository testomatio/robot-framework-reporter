import os
from robot.api import logger
from robot.model import TestSuite
from robot.running import TestCase
from robot.result import TestCase as CaseResult

from api_connectors.testomatio_connector import Connector
from models.test_item import TestItem
from models.testrun_config import TestrunConfig
from utils.test_parser import TestParser
from utils.utils import parse_test_list

DEFAULT_URL = 'https://app.testomat.io'


class ReportListener:
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self):
        self.enabled = True

        self.report_url = os.getenv('TESTOMATIO_URL') or DEFAULT_URL
        self.api_key = os.getenv('TESTOMATIO')
        if not self.api_key:
            self.enabled = False
            return

        self.config = TestrunConfig()
        self.connector = Connector(self.report_url, self.api_key)
        if not self.config.run_id:
            run_details = self.connector.create_test_run(**self.config.to_dict())
            if run_details:
                self.config.run_id = run_details.get('uid')

                message = f"\n[TESTOMATIO] Test Run successfully created.\nSee run aggregation at: {run_details.get('url')} \n"
                public_url = run_details.get('public_url')
                if self.config.access_event and public_url:
                    message += f"Public url: {public_url}\n"
                logger.info(message, also_console=True)
            else:
                # TODO: add log "Failed to create run"
                self.enabled = False

        self.suite_start_time = None
        self.test_results = []

    def end_test(self, data: TestCase, result: CaseResult):
        if not self.enabled:
            return

        test = TestItem(data, result)
        if self.config.batch_upload_disabled:
            self.connector.update_test_status(run_id=self.config.run_id, **test.to_dict())
        else:
            self.test_results.append(test.to_dict())

    def end_suite(self, data, result):
        if not self.enabled:
            return

        if not self.config.batch_upload_disabled:
            self.connector.batch_tests_upload(self.config.run_id, self.test_results.copy())
            self.test_results = []

    def close(self):
        if not self.enabled:
            return

        if self.config.run_id:
            self.connector.finish_test_run(self.config.run_id)


class ImportListener:

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, remove_ids: bool = False, no_detach: bool = False, no_empty: bool = False,
                 create: bool = False, structure: bool = False):
        self.enabled = True

        self.report_url = os.getenv('TESTOMATIO_URL') or DEFAULT_URL
        self.api_key = os.getenv('TESTOMATIO')
        if not self.api_key:
            self.enabled = False
            return

        self.connector = Connector(self.report_url, self.api_key)
        self.remove_ids = remove_ids
        self.no_detach = no_detach
        self.no_empty = no_empty
        self.create = create
        self.structure = structure
        self.directory = os.getenv('TESTOMATIO_IMPORT_DIRECTORY', None)
        self.tests = []

    def start_suite(self, suite: TestSuite, result: CaseResult):
        if not self.enabled or not self.remove_ids:
            return

        if suite.source and not os.path.isdir(suite.source):
            parser = TestParser(suite.source)
            parser.remove_test_ids()

    def start_test(self, test: TestCase, result: CaseResult):
        """Clearing execution body and add keyword to skip test"""
        test.body.clear()
        test.body.create_keyword(name='skip', args=['Import only'])

    def end_test(self, test: TestCase, result: CaseResult):
        if not self.enabled or self.remove_ids:
            return

        test_item = TestItem(test, result)
        parser = TestParser(test.source)
        test_item.source_code = parser.get_test_code(test.name)
        self.tests.append(test_item)

    def close(self):
        if not self.enabled or self.remove_ids:
            return

        if not self.tests:
            return

        self.connector.load_tests(self.tests.copy(),
                                  no_detach=self.no_detach,
                                  no_empty=self.no_empty,
                                  create=self.create,
                                  structure=self.structure,
                                  directory=self.directory)
        test_ids = self.connector.get_tests()
        if not test_ids:
            # TODO: Add log 'Failed to get test ids from testomat.io'
            return

        parsed_tests = parse_test_list(test_ids)
        for test in self.tests:
            for testomatio_test in parsed_tests:
                if test.title == testomatio_test.title and test.suite_title == testomatio_test.suite:
                    parser = TestParser(test.file_path)
                    parser.assign_test_id(test.title, testomatio_test.id)
