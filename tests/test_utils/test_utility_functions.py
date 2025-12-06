from models.testomat_item import TestomatItem
from utils.utils import parse_test_list


class TestParseTestList:

    def test_parse_empty_response(self):
        """Test parsing empty response"""
        raw_response = {
            "tests": {},
            "suites": {}
        }

        result = parse_test_list(raw_response)

        assert result == []
        assert isinstance(result, list)

    def test_parse_single_test_name_only(self):
        """Test parsing single test with name only (1 part)"""
        raw_response = {
            "tests": {
                "Simple Test": "T001"
            },
            "suites": {}
        }

        result = parse_test_list(raw_response)

        assert len(result) == 1
        assert isinstance(result[0], TestomatItem)
        assert result[0].id == "T001"
        assert result[0].title == "Simple Test"
        assert result[0].file_name is None
        assert result[0].suite is None

    def test_parse_test_with_suite_and_name(self):
        """Test parsing test with suite#name format (2 parts)"""
        raw_response = {
            "tests": {
                "Authentication Suite#Login Test": "T002"
            },
            "suites": {
                "Authentication Suite": "S001"
            }
        }

        result = parse_test_list(raw_response)

        assert len(result) == 1
        assert result[0].id == "T002"
        assert result[0].title == "Login Test"
        assert result[0].file_name is None
        assert result[0].suite == "Authentication Suite"

    def test_parse_test_with_two_parts_no_suite_match(self):
        """Test parsing test with 2 parts but first part is not a suite"""
        raw_response = {
            "tests": {
                "SomethingElse#Test Name": "T003"
            },
            "suites": {
                "Real Suite": "S001"
            }
        }

        result = parse_test_list(raw_response)

        assert len(result) == 1
        assert result[0].id == "T003"
        assert result[0].title == "Test Name"
        assert result[0].file_name is None
        assert result[0].suite is None

    def test_parse_test_with_file_suite_and_name(self):
        """Test parsing test with file#suite#name format (3 parts)"""
        raw_response = {
            "tests": {
                "test_auth.robot#Authentication Suite#Login Test": "T004"
            },
            "suites": {
                "Authentication Suite": "S001"
            }
        }

        result = parse_test_list(raw_response)

        assert len(result) == 1
        assert result[0].id == "T004"
        assert result[0].title == "Login Test"
        assert result[0].file_name == "test_auth.robot"
        assert result[0].suite is None

    def test_parse_multiple_tests_same_id(self):
        """Test parsing multiple test keys with same ID (should merge)"""
        raw_response = {
            "tests": {
                "Test Name": "T005",
                "Auth Suite#Test Name": "T005",
                "file.robot#Suite#Test Name": "T005"
            },
            "suites": {
                "Auth Suite": "S001"
            }
        }

        result = parse_test_list(raw_response)

        assert len(result) == 1
        assert result[0].id == "T005"
        assert result[0].title == "Test Name"
        assert result[0].file_name == "file.robot"

    def test_parse_multiple_different_tests(self):
        """Test parsing multiple different tests"""
        raw_response = {
            "tests": {
                "Test One": "T001",
                "Suite A#Test Two": "T002",
                "file.robot#Suite B#Test Three": "T003"
            },
            "suites": {
                "Suite A": "S001",
                "Suite B": "S002"
            }
        }

        result = parse_test_list(raw_response)

        assert len(result) == 3

        tests_by_id = {item.id: item for item in result}

        assert tests_by_id["T001"].title == "Test One"
        assert tests_by_id["T001"].suite is None

        assert tests_by_id["T002"].title == "Test Two"
        assert tests_by_id["T002"].suite == "Suite A"

        assert tests_by_id["T003"].title == "Test Three"
        assert tests_by_id["T003"].file_name == "file.robot"
