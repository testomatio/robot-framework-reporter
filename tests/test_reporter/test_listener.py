import pytest
import os
from unittest.mock import Mock, patch
from reporter.listener import ReportListener, ImportListener


@pytest.fixture
def robot_file_with_test_ids(tmp_path):
    """Create a real robot file with test IDs for testing"""
    robot_content = """\
*** Test Cases ***
Test With ID @T12345678
    Log    Test
    Should Be Equal    1    1

Another Test @TABC999de
    Log    Another
    Should Be Equal    2    2
    
Test with Tag @Tfds
    Log    Tag
    Should Be Equal    3    3
"""
    robot_file = tmp_path / "test_with_ids.robot"
    robot_file.write_text(robot_content, encoding='utf-8')
    return robot_file

@pytest.fixture
def mock_env_vars():
    """Mock environment variables"""
    with patch.dict(os.environ, {
        'TESTOMATIO': 'test_api_key_12345',
        'TESTOMATIO_URL': 'https://test.testomat.io'
    }):
        yield


@pytest.fixture
def mock_env_no_api_key():
    """Mock environment without API key"""
    with patch.dict(os.environ, {}, clear=True):
        yield


@pytest.fixture
def mock_connector():
    """Mock Connector"""
    with patch('reporter.listener.Connector') as mock:
        connector_instance = Mock()
        connector_instance.create_test_run.return_value = {'uid': 'run_123'}
        connector_instance.get_tests.return_value = {
            'tests': {
                'Test Suite#Test Name': 'T123'
            },
            'suites': {
                'Test Suite': 'S001'
            }
        }
        connector_instance.update_test_status.return_value = None
        connector_instance.batch_tests_upload.return_value = None
        connector_instance.finish_test_run.return_value = None
        connector_instance.load_tests.return_value = None
        mock.return_value = connector_instance
        yield mock


@pytest.fixture
def mock_test_parser():
    """Mock TestParser"""
    with patch('reporter.listener.TestParser') as mock:
        parser_instance = Mock()
        parser_instance.get_test_code.return_value = "Test code here"
        parser_instance.remove_test_ids.return_value = None
        parser_instance.assign_test_id.return_value = None
        mock.return_value = parser_instance
        yield mock


@pytest.fixture
def mock_test_item():
    """Mock TestItem"""
    with patch('reporter.listener.TestItem') as mock:
        item_instance = Mock()
        item_instance.title = "Test Name"
        item_instance.suite_title = "Test Suite"
        item_instance.file_path = "/path/to/test.robot"
        item_instance.source_code = None
        mock.return_value = item_instance
        yield mock


@pytest.fixture
def mock_suite():
    """Mock Robot Framework suite"""
    suite = Mock()
    suite.source = "/path/to/test.robot"
    return suite


@pytest.fixture
def mock_test_config():
    """Mock TestrunConfig"""
    with patch('reporter.listener.TestrunConfig') as mock:
        config_instance = Mock()
        config_instance.run_id = None
        config_instance.batch_upload_disabled = False
        config_instance.to_dict = lambda: {
            'access_event': None,
            'title': None,
            'group_title': None,
        }
        mock.return_value = config_instance
        yield mock


@pytest.fixture
def mock_test_and_result():
    """Mock test case and result objects"""
    test = Mock()
    test.name = "Example Test @T123"
    test.source = "/path/to/test.robot"
    test.parent = Mock()
    test.parent.name = "Example Suite"

    result = Mock()
    result.status = "PASS"
    result.elapsed_time = Mock()
    result.elapsed_time.microseconds = 150000

    return test, result


@pytest.fixture
def mock_env_with_directory():
    """Mock environment with import directory"""
    with patch.dict(os.environ, {
        'TESTOMATIO': 'test_api_key_12345',
        'TESTOMATIO_IMPORT_DIRECTORY': 'custom/directory'
    }):
        yield


class TestReportListener:

    def test_initialization_with_api_key(self, mock_env_vars, mock_connector):
        """Test successful initialization with API key"""
        listener = ReportListener()

        assert listener.enabled is True
        assert listener.api_key == 'test_api_key_12345'
        assert listener.report_url == 'https://test.testomat.io'
        mock_connector.assert_called_once_with('https://test.testomat.io', 'test_api_key_12345')

    def test_initialization_without_api_key(self, mock_env_no_api_key):
        """Test initialization without API key disables listener"""
        listener = ReportListener()

        assert listener.enabled is False
        assert listener.api_key is None

    def test_initialization_creates_test_run(self, mock_env_vars, mock_connector):
        """Test that initialization creates a test run"""
        listener = ReportListener()

        mock_connector.return_value.create_test_run.assert_called_once()
        assert listener.config.run_id == 'run_123'

    def test_initialization_fails_to_create_run(self, mock_env_vars, mock_connector):
        """Test handling failed test run creation"""
        mock_connector.return_value.create_test_run.return_value = None

        listener = ReportListener()

        assert listener.enabled is False

    def test_initialization_not_creates_run_if_testrun_id_exist(self, mock_connector):
        """Test that initialization not creates a test run if testrun id passed"""
        with patch.dict(os.environ, {
            'TESTOMATIO': 'test_api_key_12345',
            'TESTOMATIO_URL': 'https://test.testomat.io',
            'TESTOMATIO_RUN': 'id1'
        }, clear=True):
            listener = ReportListener()

            mock_connector.return_value.create_test_run.assert_not_called()
            assert listener.config.run_id == 'id1'

    def test_initialization_uses_default_url(self, mock_connector):
        """Test that default URL is used when TESTOMATIO_URL not set"""
        with patch.dict(os.environ, {'TESTOMATIO': 'key123'}, clear=True):
            listener = ReportListener()

            assert listener.report_url == 'https://app.testomat.io'

    def test_initialization_test_results_empty(self, mock_env_vars, mock_connector):
        """Test that test_results list is initialized empty"""
        listener = ReportListener()

        assert listener.test_results == []

    def test_end_test_when_disabled(self, mock_env_no_api_key, mock_test_and_result):
        """Test end_test does nothing when listener is disabled"""
        listener = ReportListener()
        test, result = mock_test_and_result

        # Should not raise any errors
        listener.end_test(test, result)

        assert listener.enabled is False
        assert not hasattr(listener, 'test_results')

    @patch('reporter.listener.TestItem')
    def test_end_test_batch_upload_enabled(self, mock_test_item, mock_env_vars,
                                           mock_connector, mock_test_config, mock_test_and_result):
        """Test end_test appends to test_results when batch upload enabled"""
        listener = ReportListener()
        test, result = mock_test_and_result

        mock_item = Mock()
        mock_item.to_dict.return_value = {'test_id': 'T123', 'status': 'passed'}
        mock_test_item.return_value = mock_item

        listener.end_test(test, result)

        assert len(listener.test_results) == 1
        assert listener.test_results[0] == {'test_id': 'T123', 'status': 'passed'}
        mock_connector.return_value.update_test_status.assert_not_called()

    @patch('reporter.listener.TestItem')
    def test_end_test_batch_upload_disabled(self, mock_test_item, mock_env_vars,
                                            mock_connector, mock_test_config, mock_test_and_result):
        """Test end_test sends immediately when batch upload disabled"""
        listener = ReportListener()
        listener.config.batch_upload_disabled = True
        listener.config.run_id = 'run_123'

        test, result = mock_test_and_result

        mock_item = Mock()
        mock_item.to_dict.return_value = {'test_id': 'T123', 'status': 'passed'}
        mock_test_item.return_value = mock_item

        listener.end_test(test, result)

        mock_connector.return_value.update_test_status.assert_called_once_with(
            run_id='run_123',
            test_id='T123',
            status='passed'
        )
        assert len(listener.test_results) == 0

    @patch('reporter.listener.TestItem')
    def test_end_test_multiple_tests(self, mock_test_item, mock_env_vars,
                                     mock_connector, mock_test_config, mock_test_and_result):
        """Test end_test with multiple tests"""
        listener = ReportListener()
        test, result = mock_test_and_result

        mock_item1 = Mock()
        mock_item1.to_dict.return_value = {'test_id': 'T1', 'status': 'passed'}
        mock_item2 = Mock()
        mock_item2.to_dict.return_value = {'test_id': 'T2', 'status': 'failed'}

        mock_test_item.side_effect = [mock_item1, mock_item2]

        listener.end_test(test, result)
        listener.end_test(test, result)

        assert len(listener.test_results) == 2
        assert listener.test_results[0]['test_id'] == 'T1'
        assert listener.test_results[1]['test_id'] == 'T2'

    def test_end_suite_when_disabled(self, mock_env_no_api_key):
        """Test end_suite does nothing when listener is disabled"""
        listener = ReportListener()

        # Should not raise any errors
        listener.end_suite(Mock(), Mock())

    def test_end_suite_batch_upload_enabled(self, mock_env_vars, mock_connector, mock_test_config):
        """Test end_suite uploads batch when batch upload enabled"""
        listener = ReportListener()
        listener.test_results = [
            {'test_id': 'T1', 'status': 'passed'},
            {'test_id': 'T2', 'status': 'failed'}
        ]

        listener.end_suite(Mock(), Mock())

        mock_connector.return_value.batch_tests_upload.assert_called_once_with(
            'run_123',
            [
                {'test_id': 'T1', 'status': 'passed'},
                {'test_id': 'T2', 'status': 'failed'}
            ]
        )
        assert listener.test_results == []

    def test_end_suite_empty_results(self, mock_env_vars, mock_connector, mock_test_config):
        """Test end_suite with empty test results"""
        listener = ReportListener()
        listener.test_results = []

        listener.end_suite(Mock(), Mock())

        mock_connector.return_value.batch_tests_upload.assert_called_once_with('run_123', [])

    def test_close_when_disabled(self, mock_env_no_api_key):
        """Test close does nothing when listener is disabled"""
        listener = ReportListener()

        # Should not raise any errors
        listener.close()

    def test_close_finishes_test_run(self, mock_env_vars, mock_connector, mock_test_config):
        """Test close finishes the test run"""
        listener = ReportListener()
        listener.config.run_id = 'run_123'

        listener.close()

        mock_connector.return_value.finish_test_run.assert_called_once_with('run_123')


class TestImportListener:

    def test_initialization_with_api_key(self, mock_env_vars, mock_connector):
        """Test successful initialization with API key"""
        listener = ImportListener()

        assert listener.enabled is True
        assert listener.api_key == 'test_api_key_12345'
        assert listener.report_url == 'https://test.testomat.io'
        mock_connector.assert_called_once_with('https://test.testomat.io', 'test_api_key_12345')

    def test_initialization_without_api_key(self, mock_env_no_api_key):
        """Test initialization without API key disables listener"""
        listener = ImportListener()

        assert listener.enabled is False
        assert listener.api_key is None

    def test_initialization_with_default_parameters(self, mock_env_vars, mock_connector):
        """Test initialization with default parameters"""
        listener = ImportListener()

        assert listener.remove_ids is False
        assert listener.no_detach is False
        assert listener.no_empty is False
        assert listener.create is False
        assert listener.structure is False
        assert listener.directory is None
        assert listener.tests == []

    def test_initialization_with_custom_parameters(self, mock_env_vars, mock_connector):
        """Test initialization with custom parameters"""
        listener = ImportListener(
            remove_ids=True,
            no_detach=True,
            no_empty=True,
            create=True,
            structure=True
        )

        assert listener.remove_ids is True
        assert listener.no_detach is True
        assert listener.no_empty is True
        assert listener.create is True
        assert listener.structure is True

    def test_initialization_with_directory_env_var(self, mock_env_with_directory, mock_connector):
        """Test initialization reads directory from environment"""
        listener = ImportListener()

        assert listener.directory == 'custom/directory'

    def test_initialization_uses_default_url(self, mock_connector):
        """Test that default URL is used when TESTOMATIO_URL not set"""
        with patch.dict(os.environ, {'TESTOMATIO': 'key123'}, clear=True):
            listener = ImportListener()

            assert listener.report_url == 'https://app.testomat.io'

    def test_start_suite_when_disabled(self, mock_env_no_api_key, mock_suite):
        """Test start_suite does nothing when listener is disabled"""
        listener = ImportListener(remove_ids=True)

        # Should not raise any errors
        listener.start_suite(mock_suite, Mock())

    def test_start_suite_when_remove_ids_false(self, mock_env_vars, mock_connector,
                                               mock_test_parser, mock_suite):
        """Test start_suite does nothing when remove_ids is False"""
        listener = ImportListener(remove_ids=False)

        listener.start_suite(mock_suite, Mock())

        mock_test_parser.assert_not_called()

    def test_start_suite_removes_ids_from_file(self, mock_env_vars, mock_connector,
                                                mock_suite, robot_file_with_test_ids):
        """Test start_suite removes IDs from robot file"""
        original_content = robot_file_with_test_ids.read_text(encoding='utf-8')
        assert '@T12345678' in original_content
        assert '@TABC999de' in original_content

        listener = ImportListener(remove_ids=True)
        mock_suite.source = str(robot_file_with_test_ids)

        listener.start_suite(mock_suite, Mock())
        modified_content = robot_file_with_test_ids.read_text(encoding='utf-8')
        assert '@T12345678' not in modified_content
        assert '@TABC999de' not in modified_content
        assert 'Test With ID' in modified_content
        assert 'Another Test' in modified_content

    def test_start_suite_skips_directories(self, mock_env_vars, mock_connector,
                                           mock_test_parser, mock_suite):
        """Test start_suite skips directory sources"""
        listener = ImportListener(remove_ids=True)
        mock_suite.source = "/path/to/directory"

        with patch('os.path.isdir', return_value=True):
            listener.start_suite(mock_suite, Mock())

        mock_test_parser.assert_not_called()

    def test_start_suite_handles_none_source(self, mock_env_vars, mock_connector,
                                             mock_test_parser, mock_suite):
        """Test start_suite handles None source"""
        listener = ImportListener(remove_ids=True)
        mock_suite.source = None

        listener.start_suite(mock_suite, Mock())

        mock_test_parser.assert_not_called()

    def test_end_test_when_disabled(self, mock_env_no_api_key, mock_test_and_result):
        """Test end_test does nothing when listener is disabled"""
        listener = ImportListener()

        test, result = mock_test_and_result
        listener.end_test(test, result)

        assert listener.enabled is False
        assert not hasattr(listener, 'tests')

    def test_end_test_when_remove_ids_true(self, mock_env_vars, mock_connector, mock_test_and_result):
        """Test end_test does nothing when remove_ids is True"""
        listener = ImportListener(remove_ids=True)

        test, result = mock_test_and_result
        listener.end_test(test, result)

        assert listener.enabled is True
        assert listener.remove_ids is True
        assert listener.tests == []

    def test_end_test_adds_test_with_source_code(self, mock_env_vars, mock_connector,
                                                 mock_test_and_result,
                                                 robot_file_with_test_ids):
        """Test end_test adds test item with source code"""
        listener = ImportListener(remove_ids=False)

        test, result = mock_test_and_result
        test.source = robot_file_with_test_ids
        test.name = 'Test With ID @T12345678'
        listener.end_test(test, result)

        assert len(listener.tests) == 1
        test_item = listener.tests[0]
        assert test_item
        assert test_item.title == test.name
        assert test_item.file_path == robot_file_with_test_ids
        assert test_item.file == robot_file_with_test_ids.name
        assert test_item.test_id == '12345678'
        assert test_item.source_code == """\
Test With ID @T12345678
    Log    Test
    Should Be Equal    1    1

"""

    def test_end_test_adds_test_with_tag_in_name(self, mock_env_vars, mock_connector,
                                                 mock_test_and_result,
                                                 robot_file_with_test_ids):
        """Test end_test adds test item with tag in name"""
        listener = ImportListener(remove_ids=False)

        test, result = mock_test_and_result
        test.source = robot_file_with_test_ids
        test.name = 'Test with Tag @Tfds'
        listener.end_test(test, result)

        assert len(listener.tests) == 1
        test_item = listener.tests[0]
        assert test_item
        assert test_item.title == test.name
        assert test_item.file_path == robot_file_with_test_ids
        assert test_item.file == robot_file_with_test_ids.name
        assert test_item.test_id is None
        assert test_item.source_code == """\
Test with Tag @Tfds
    Log    Tag
    Should Be Equal    3    3
"""

    def test_end_test_multiple_tests(self, mock_env_vars, mock_connector,
                                     mock_test_item, mock_test_parser):
        """Test end_test with multiple tests"""
        listener = ImportListener()

        listener.end_test(Mock(), Mock())
        listener.end_test(Mock(), Mock())
        listener.end_test(Mock(), Mock())

        assert len(listener.tests) == 3

    def test_close_when_disabled(self, mock_env_no_api_key):
        """Test close does nothing when listener is disabled"""
        listener = ImportListener()

        # Should not raise any errors
        listener.close()
        assert listener.enabled is False
        assert not hasattr(listener, 'tests')

    def test_close_when_remove_ids_true(self, mock_env_vars, mock_connector):
        """Test close does nothing when remove_ids is True"""
        listener = ImportListener(remove_ids=True)

        listener.close()

        mock_connector.return_value.load_tests.assert_not_called()

    def test_close_when_no_tests(self, mock_env_vars, mock_connector):
        """Test close does nothing when tests list is empty"""
        listener = ImportListener()

        listener.close()

        mock_connector.return_value.load_tests.assert_not_called()
        assert listener.tests == []

    @patch('reporter.listener.parse_test_list')
    def test_close_loads_tests(self, mock_parse, mock_env_vars, mock_connector,
                               mock_test_item, mock_test_parser):
        """Test close loads tests to testomat.io"""
        listener = ImportListener(
            no_detach=True,
            no_empty=True,
            create=True,
            structure=True
        )
        listener.directory = 'test/dir'

        # Add mock test
        test_item = Mock()
        test_item.title = "Test Name"
        test_item.suite_title = "Test Suite"
        test_item.file_path = "/path/to/test.robot"
        listener.tests = [test_item]

        listener.close()

        mock_connector.return_value.load_tests.assert_called_once_with(
            [test_item],
            no_detach=True,
            no_empty=True,
            create=True,
            structure=True,
            directory='test/dir'
        )

    @patch('reporter.listener.parse_test_list')
    def test_close_gets_test_ids(self, mock_parse, mock_env_vars, mock_connector):
        """Test close retrieves test IDs from API"""
        listener = ImportListener()
        test_item = Mock()
        test_item.title = "Test Name"
        test_item.suite_title = "Test Suite"
        listener.tests = [test_item]

        listener.close()

        mock_connector.return_value.get_tests.assert_called_once()

    @patch('reporter.listener.parse_test_list')
    def test_close_handles_failed_get_tests(self, mock_parse, mock_env_vars, mock_connector,
                                            mock_test_parser):
        """Test close handles when get_tests returns None"""
        listener = ImportListener()
        test_item = Mock()
        listener.tests = [test_item]

        mock_connector.return_value.get_tests.return_value = None

        listener.close()

        # Should return early, not call parse_test_list or assign_test_id
        mock_parse.assert_not_called()
        mock_test_parser.assert_not_called()

    @patch('reporter.listener.parse_test_list')
    def test_close_assigns_test_ids(self, mock_parse, mock_env_vars, mock_connector,
                                    mock_test_parser):
        """Test close assigns test IDs to matching tests"""
        listener = ImportListener()

        # Setup test item
        test_item = Mock()
        test_item.title = "Test Name @as"
        test_item.sync_title = "Test Name"
        test_item.suite_title = "Test Suite"
        test_item.file_path = "/path/to/test.robot"
        listener.tests = [test_item]

        # Setup parsed test
        parsed_test = Mock()
        parsed_test.id = "@T123"
        parsed_test.title = "Test Name"
        parsed_test.suite = "Test Suite"
        mock_parse.return_value = [parsed_test]

        listener.close()

        mock_test_parser.assert_called_once_with("/path/to/test.robot")
        mock_test_parser.return_value.assign_test_id.assert_called_once_with("Test Name @as", "@T123")

    @patch('reporter.listener.parse_test_list')
    def test_close_only_assigns_matching_tests(self, mock_parse, mock_env_vars,
                                               mock_connector, mock_test_parser):
        """Test close only assigns IDs to tests with matching title and suite"""
        listener = ImportListener()

        # Setup test items
        test_item1 = Mock()
        test_item1.title = "Test One"
        test_item1.sync_title = "Test One"
        test_item1.suite_title = "Suite A"
        test_item1.file_path = "/path/test1.robot"

        test_item2 = Mock()
        test_item2.title = "Test Two"
        test_item2.sync_title = "Test Two"
        test_item2.suite_title = "Suite B"
        test_item2.file_path = "/path/test2.robot"

        listener.tests = [test_item1, test_item2]

        # Setup parsed test (only matches test_item1)
        parsed_test = Mock()
        parsed_test.id = "@T123"
        parsed_test.title = "Test One"
        parsed_test.suite = "Suite A"
        mock_parse.return_value = [parsed_test]

        listener.close()

        # Should only be called for test_item1
        assert mock_test_parser.call_count == 1
        mock_test_parser.assert_called_with("/path/test1.robot")

    @patch('reporter.listener.parse_test_list')
    def test_close_handles_multiple_matching_tests(self, mock_parse, mock_env_vars,
                                                   mock_connector, mock_test_parser):
        """Test close with multiple matching tests"""
        listener = ImportListener()

        # Setup test items
        test_item1 = Mock()
        test_item1.title = "Test Name"
        test_item1.sync_title = "Test Name"
        test_item1.suite_title = "Suite"
        test_item1.file_path = "/path/test1.robot"

        test_item2 = Mock()
        test_item2.title = "Test Name"
        test_item2.sync_title = "Test Name"
        test_item2.suite_title = "Suite"
        test_item2.file_path = "/path/test2.robot"

        listener.tests = [test_item1, test_item2]

        # Setup parsed test
        parsed_test = Mock()
        parsed_test.id = "@T999"
        parsed_test.title = "Test Name"
        parsed_test.suite = "Suite"
        mock_parse.return_value = [parsed_test]

        listener.close()

        # Should be called for both tests
        assert mock_test_parser.call_count == 2
