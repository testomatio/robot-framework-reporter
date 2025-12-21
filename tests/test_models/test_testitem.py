from pathlib import Path

import pytest
import uuid
import json
from unittest.mock import Mock, patch
from pytest import Item

from robot.result.model import StatusMixin
from models.test_item import TestItem, STATUS_MAP


class TestTestItem:
    """Tests for TestItem"""

    @pytest.fixture
    def mock_test_object(self):
        """Mock Robot Framework test object"""
        test = Mock()
        test.name = "Example Test Case"

        # Mock parent (suite)
        parent = Mock()
        parent.name = "Example Suite"
        test.parent = parent

        # Mock source
        source = Mock(spec=Path)
        source.name = "test_example.robot"
        test.source = source

        return test

    @pytest.fixture
    def mock_result_object(self):
        """Mock Robot Framework result object"""
        result = Mock()
        result.status = StatusMixin.PASS

        # Mock elapsed_time
        elapsed = Mock()
        elapsed.microseconds = 150000  # 150ms
        result.elapsed_time = elapsed

        return result

    @pytest.mark.parametrize('status', [StatusMixin.PASS, StatusMixin.FAIL, StatusMixin.SKIP])
    def test_initialization_with_different_statuses(self, status, mock_test_object, mock_result_object):
        """Test creating TestItem with different statuses"""
        mock_result_object.status = status
        item = TestItem(mock_test_object, mock_result_object)

        assert item.title == "Example Test Case"
        assert item.sync_title == "Example Test Case"
        assert item.status == STATUS_MAP.get(status)
        assert item.run_time == 150000
        assert item.suite_title == "Example Suite"
        assert item.file == "test_example.robot"
        assert item.source_code is None
        assert item.file_path == mock_test_object.source
        assert item.test_id is None

    @pytest.mark.parametrize('tag', ["@smoke", "@Tgfd"])
    def test_initialization_with_different_tags_in_name(self, tag, mock_test_object, mock_result_object):
        """Test creating TestItem with different tags in name"""
        mock_test_object.name = mock_test_object.name + " " + tag
        item = TestItem(mock_test_object, mock_result_object)

        assert item.title == f"Example Test Case {tag}"
        assert item.sync_title == f"Example Test Case"
        assert item.status == "passed"
        assert item.run_time == 150000
        assert item.suite_title == "Example Suite"
        assert item.file == "test_example.robot"
        assert item.source_code is None
        assert item.file_path == mock_test_object.source
        assert item.test_id is None

    def test_initialization_with_test_id(self, mock_test_object, mock_result_object):
        """Test creating TestItem with test_id"""
        mock_test_object.name = mock_test_object.name + " " + "@Tghjt34ef"
        item = TestItem(mock_test_object, mock_result_object)

        assert item.title == f"Example Test Case @Tghjt34ef"
        assert item.sync_title == f"Example Test Case"
        assert item.status == "passed"
        assert item.run_time == 150000
        assert item.suite_title == "Example Suite"
        assert item.file == "test_example.robot"
        assert item.source_code is None
        assert item.file_path == mock_test_object.source
        assert item.test_id == "ghjt34ef"

    def test_initialization_with_unknown_status(self, mock_test_object, mock_result_object):
        """Test creating TestItem with unknown status"""
        mock_result_object.status = "UNKNOWN_STATUS"

        item = TestItem(mock_test_object, mock_result_object)

        assert item.status is None

    def test_to_dict(self, mock_test_object, mock_result_object):
        """Test converting TestItem to dictionary"""
        item = TestItem(mock_test_object, mock_result_object)

        result = item.to_dict()

        assert isinstance(result, dict)
        assert result['test_id'] is None
        assert result['title'] == "Example Test Case"
        assert result['status'] == "passed"
        assert result['run_time'] == 150000
        assert result['suite_title'] == "Example Suite"
        assert result['file'] == "test_example.robot"

    def test_to_dict_with_test_id(self, mock_test_object, mock_result_object):
        """Test to_dict includes test_id when present"""
        mock_test_object.name = "Login Test @T12345asd"

        item = TestItem(mock_test_object, mock_result_object)
        result = item.to_dict()
        print(result)

        assert result['test_id'] == "12345asd"

    def test_to_dict_with_tags(self, mock_test_object, mock_result_object):
        """Test to_dict correctly handles tests with tags in name"""
        mock_test_object.title = "Example Test Case @smoke @Tgfd"
        item = TestItem(mock_test_object, mock_result_object)

        result = item.to_dict()

        assert isinstance(result, dict)
        assert result['test_id'] is None
        assert result['title'] == "Example Test Case"
        assert result['status'] == "passed"
        assert result['run_time'] == 150000
        assert result['suite_title'] == "Example Suite"
        assert result['file'] == "test_example.robot"

    def test_get_test_id_without_marker(self, mock_test_object, mock_result_object):
        """Test extracting test_id when no @T marker present"""
        mock_test_object.name = "Simple Test Case"

        item = TestItem(mock_test_object, mock_result_object)

        assert item.get_test_id() is None
        assert item.test_id is None

    def test_get_test_id_with_marker(self, mock_test_object, mock_result_object):
        """Test extracting test_id with @T marker"""
        mock_test_object.name = "User Login @T1234fde5"

        item = TestItem(mock_test_object, mock_result_object)

        assert item.get_test_id() == "1234fde5"
        assert item.test_id == "1234fde5"

    def test_get_test_id_with_multiple_markers(self, mock_test_object, mock_result_object):
        """Test extracting test_id when multiple @T markers present (takes last one)"""
        mock_test_object.name = "Test @T111 something @T43299999"

        item = TestItem(mock_test_object, mock_result_object)

        assert item.get_test_id() == "43299999"
        assert item.test_id == "43299999"

    def test_suite_title_extraction(self, mock_test_object, mock_result_object):
        """Test suite title is correctly extracted from parent"""
        mock_test_object.parent.name = "Authentication Suite"

        item = TestItem(mock_test_object, mock_result_object)

        assert item.suite_title == "Authentication Suite"

    @pytest.mark.parametrize('tag', ["@smoke", "@Tgfd"])
    def test_clean_title(self, tag, mock_test_object, mock_result_object):
        item = TestItem(mock_test_object, mock_result_object)
        title = item.title + ' ' + tag

        cleaned_title = item.clean_title(title)
        assert cleaned_title == item.title

