from robot.running import TestCase
from robot.result import TestCase as TestCaseResult
from robot.result.model import StatusMixin

STATUS_MAP = {
    StatusMixin.PASS: 'passed',
    StatusMixin.FAIL: 'failed',
    StatusMixin.SKIP: 'skipped'
}


class TestItem:

    def __init__(self, test_object: TestCase, result_object: TestCaseResult):
        self.title = test_object.name
        self.status = STATUS_MAP.get(result_object.status, None)
        self.run_time = result_object.elapsed_time.microseconds
        self.suite_title = test_object.parent.name
        self.file = test_object.source.name
        self.source_code = None
        self.file_path = test_object.source
        self.test_id = self.get_test_id()

    def to_dict(self):
        data = {
            'test_id': self.test_id,
            'title': self.title,
            'status': self.status,
            'run_time': self.run_time,
            'suite_title': self.suite_title,
            'file': self.file,
        }
        return data

    def get_test_id(self) -> str | None:
        """Returns testomatio test id from test title"""
        test_id = None
        split = self.title.split('@T')
        if len(split) > 1:
            test_id = split[-1]
        return test_id

