import re

from robot.api.parsing import get_model
from robot.parsing.lexer.tokens import Token
from robot.parsing.model.blocks import TestCase

from utils.constants import TEST_ID_PATTERN


class TestParser:

    def __init__(self, file_path):
        self.file_path = file_path
        self.model = get_model(file_path)

    def get_test_code(self, test_name: str) -> str | None:
        """Receive test source code"""
        test_node = self._find_test(test_name)
        if not test_node:
            return None

        with open(self.file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        start_line = test_node.lineno - 1
        end_line = self._find_test_end_line(test_node)

        return ''.join(lines[start_line:end_line])

    def assign_test_id(self, test_name: str, test_id: str):
        """Assigns test id for given test"""
        if re.search(TEST_ID_PATTERN, test_name):
            return

        test_node = self._find_test(test_name)
        if not test_node:
            raise ValueError(f"Test '{test_name}' not found")

        new_name = f'{test_name} {test_id}'
        self._update_name(test_node, new_name)
        self.save()

    def remove_test_ids(self):
        """Removes testomatio id from test name for all tests in file"""
        for section in self.model.sections:
            if hasattr(section, 'header') and section.header.type == Token.TESTCASE_HEADER:
                for test in section.body:
                    if hasattr(test, 'name') and re.search(TEST_ID_PATTERN, test.name):
                        new_name = re.sub(TEST_ID_PATTERN, '', test.name).strip()
                        self._update_name(test, new_name)

        self.save()

    def _find_test(self, test_name: str) -> TestCase | None:
        """Finds test in model by name"""
        for section in self.model.sections:
            if hasattr(section, 'header') and section.header.type == Token.TESTCASE_HEADER:
                for test in section.body:
                    if hasattr(test, 'name') and test.name == test_name:
                        return test
        return None

    def _find_test_end_line(self, test_node):
        """Finds test end line"""
        if hasattr(test_node, 'end_lineno') and test_node.end_lineno:
            return test_node.end_lineno

        # if attribute not found, manual looking
        with open(self.file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        start = test_node.lineno
        for i in range(start, len(lines)):
            if lines[i].strip() and not lines[i].startswith((' ', '\t')):
                return i
        return len(lines)

    def _update_name(self, test: TestCase, new_name: str):
        """Updated test name token with given value"""
        for token in test.header.tokens:
            if token.type == Token.TESTCASE_NAME:
                token.value = new_name
                break

    def save(self):
        self.model.save(self.file_path)
