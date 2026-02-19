import pytest
import os
import requests
from requests.exceptions import HTTPError, ConnectionError
from unittest.mock import Mock, patch

from api_connectors.testomatio_connector import Connector, MAX_RETRIES_DEFAULT, MaxRetriesException, \
    RETRY_INTERVAL_DEFAULT
from models.test_item import TestItem


class TestConnector:
    """Tests for Connector"""

    @pytest.fixture
    def connector(self):
        return Connector("https://api.testomat.io", "test_api_key_123")

    @pytest.fixture
    def mock_response(self):
        """Fixture to create mock response objects"""

        def _create_response(status_code: int):
            response = Mock()
            response.status_code = status_code
            return response

        return _create_response

    def test_init_basic(self):
        """Test init Connector"""
        connector = Connector("https://example.com", "api_key")

        assert connector.base_url == "https://example.com"
        assert connector.api_key == "api_key"
        assert connector.jwt == ""
        assert connector.max_retries == MAX_RETRIES_DEFAULT
        assert connector.retry_interval == RETRY_INTERVAL_DEFAULT
        assert isinstance(connector._session, requests.Session)

    @patch.dict(os.environ, {}, clear=True)
    def test_apply_proxy_settings_no_proxy(self, connector):
        """Test config without proxy"""
        with patch.object(connector, '_test_proxy_connection', return_value=True):
            connector._apply_proxy_settings()

            assert connector._session.proxies == {}
            assert connector._session.verify is True

    @patch.dict(os.environ, {'HTTP_PROXY': 'http://proxy.example.com:8080'})
    def test_apply_proxy_settings_with_proxy_working(self, connector):
        """Test config with working proxy"""
        with patch.object(connector, '_test_proxy_connection', return_value=True):
            connector._apply_proxy_settings()

            expected_proxies = {
                "http": "http://proxy.example.com:8080",
                "https": "http://proxy.example.com:8080"
            }
            assert connector._session.proxies == expected_proxies
            assert connector._session.verify is False

    @patch.dict(os.environ, {'HTTP_PROXY': 'http://proxy.example.com:8080'})
    def test_apply_proxy_settings_with_proxy_failing(self, connector):
        """Test fallback when proxies not working"""
        with patch.object(connector, '_test_proxy_connection', return_value=False):
            connector._apply_proxy_settings()

            assert connector._session.proxies == {}
            assert connector._session.verify is True

    @patch('requests.Session.get')
    def test_test_proxy_connection_success(self, mock_get, connector):
        """Test successful connection check"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = connector._test_proxy_connection(timeout=1)

        assert result is True
        assert mock_get.call_count == 1

    @patch('requests.Session.get')
    @patch('time.sleep')
    def test_test_proxy_connection_timeout(self, mock_sleep, mock_get, connector):
        """Test check connection timeout"""
        mock_get.side_effect = requests.exceptions.RequestException("Connection failed")

        result = connector._test_proxy_connection(timeout=1, retry_interval=0.1)

        assert result is False
        assert mock_get.call_count > 1

    def test_init_with_env_variables(self):
        """Test init with env vars"""
        max_failures = '12'
        interval = '10'
        env_vars = {
            'TESTOMATIO_MAX_REQUEST_FAILURES': max_failures,
            'TESTOMATIO_REQUEST_INTERVAL': interval
        }

        with patch.dict(os.environ, env_vars, clear=True):
            connector = Connector("https://example.com", "api_key")

            assert connector.base_url == "https://example.com"
            assert connector.api_key == "api_key"
            assert connector.jwt == ""
            assert connector.max_retries == int(max_failures)
            assert connector.retry_interval == int(interval)
            assert isinstance(connector._session, requests.Session)

    def test_init_max_request_retries_with_correct_value(self):
        """Test different true values for TESTOMATIO_MAX_REQUEST_FAILURES"""
        value = '4'
        with patch.dict(os.environ, {'TESTOMATIO_MAX_REQUEST_FAILURES': value}, clear=True):
            connector = Connector("https://example.com", "api_key")

            assert connector.max_retries == int(value)

    def test_init_max_request_retries_with_incorrect_value(self):
        """Test different false values TESTOMATIO_MAX_REQUEST_FAILURES"""
        value = 'word'
        with patch.dict(os.environ, {'TESTOMATIO_MAX_REQUEST_FAILURES': value}, clear=True):
            connector = Connector("https://example.com", "api_key")

            assert connector.max_retries != value
            assert connector.max_retries == MAX_RETRIES_DEFAULT

    def test_init_retry_interval_with_correct_value(self):
        """Test different true values for TESTOMATIO_REQUEST_INTERVAL"""
        value = '4'
        with patch.dict(os.environ, {'TESTOMATIO_REQUEST_INTERVAL': value}, clear=True):
            connector = Connector("https://example.com", "api_key")

            assert connector.retry_interval == int(value)

    def test_init_retry_interval_with_incorrect_value(self):
        """Test different false values TESTOMATIO_REQUEST_INTERVAL"""
        value = 'word'
        with patch.dict(os.environ, {'TESTOMATIO_REQUEST_INTERVAL': value}, clear=True):
            connector = Connector("https://example.com", "api_key")

            assert connector.retry_interval != value
            assert connector.retry_interval == RETRY_INTERVAL_DEFAULT

    @pytest.mark.parametrize("status_code", [400, 404, 429, 500])
    def test_should_not_retry_with_non_retry_status_codes(self, status_code, connector):
        """Should not retry on status codes < 501"""
        response = Mock()
        response.status_code = status_code

        assert connector._should_retry(response) is False

    @pytest.mark.parametrize("status_code", [501, 502, 503, 504])
    def test_should_retry_on_error_codes(self, status_code, connector):
        """Should retry on status codes >= 501 (excluding skipped)"""
        response = Mock()
        response.status_code = status_code

        assert connector._should_retry(response) is True

    @pytest.mark.parametrize("status_code", [200, 201, 204, 301, 302, 304])
    def test_should_not_retry_on_success_codes(self, status_code, connector):
        """Should not retry on 2xx and 3xx status codes"""
        response = Mock()
        response.status_code = status_code

        assert connector._should_retry(response) is False

    def test_successful_send_request_on_first_attempt(self, connector, mock_response):
        """send_request method should return response on successful first attempt"""
        response = mock_response(200)
        connector._session = Mock()
        connector._apply_proxy_settings = Mock()
        connector._session.get = Mock(return_value=response)

        method, url = 'get', 'https://api.example.com/test'
        result = connector._send_request_with_retry(method, url)

        assert result == response
        assert connector._session.get.call_count == 1

    @patch('time.sleep')
    def test_send_request_retry_on_retryable_status_code(self, mock_sleep, connector, mock_response):
        """send_request method should retry on status codes that require retry"""
        connector.max_retries = 2
        connector.retry_interval = 5

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response(503))
        connector._session = mock_session
        connector._apply_proxy_settings = Mock()
        method, url = 'get', 'https://api.example.com/test'

        with pytest.raises(MaxRetriesException):
            connector._send_request_with_retry(method, url)

        assert mock_sleep.call_count == 2

    def test_send_request_no_retry_on_non_retryable_status_code(self, connector, mock_response):
        """send_request method should not retry on status codes in skip list"""
        expected_response = mock_response(400)
        mock_session = Mock()
        mock_session.get = Mock(return_value=expected_response)
        connector._session = mock_session
        connector._apply_proxy_settings = Mock()

        method, url = 'get', 'https://api.example.com/test'
        result = connector._send_request_with_retry(method, url)

        assert result == expected_response
        assert connector.session.get.call_count == 1

    @patch('time.sleep')
    def test_send_request_retry_then_success_with_counter(self, mock_sleep, connector, mock_response):
        """send_request method should retry and eventually succeed"""
        connector.max_retries = 3

        call_count = 0

        def get_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return mock_response(503)
            return mock_response(200)

        mock_session = Mock()
        mock_session.get = Mock(side_effect=get_response)

        connector._session = mock_session
        connector._apply_proxy_settings = Mock()

        method, url = 'get', 'https://api.example.com/test'
        result = connector._send_request_with_retry(method, url)

        assert result.status_code == 200
        assert mock_session.get.call_count == 3
        assert mock_sleep.call_count == 2

    @patch('requests.Session.post')
    def test_load_tests_success(self, mock_post, connector):
        """Test successful load test"""
        mock_test = Mock(spec=TestItem)
        mock_test.title = "Test Login"
        mock_test.suite_title = "TestAuth"
        mock_test.source_code = "def test_login(): pass"
        mock_test.file_path = "test_auth.py"
        mock_test.file = "test_auth.py"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {'TESTOMATIO_SYNC_LABELS': 'feature, smoke'}, clear=True):
            connector.load_tests([mock_test])

        assert mock_post.call_count == 1
        call_args = mock_post.call_args

        assert f'{connector.base_url}/api/load' in call_args[0][0]
        assert 'api_key=test_api_key_123' in call_args[0][0]

        payload = call_args[1]['json']
        assert payload['framework'] == 'pytest'
        assert payload['language'] == 'python'
        assert len(payload['tests']) == 1
        assert payload['tests'][0]['name'] == 'Test Login'
        assert payload['tests'][0]['labels'] == 'feature,smoke'

    @patch('requests.Session.post')
    def test_load_tests_connection_error(self, mock_post, connector):
        """Test handling connection error on load_tests"""
        mock_post.side_effect = ConnectionError("Connection failed")

        result = connector.load_tests([])

        assert result is None

    @patch('requests.Session.post')
    def test_create_test_run_success(self, mock_post, connector):
        """Test that test run successfully created"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"uid": "run_123", "title": "Test Run"}
        mock_post.return_value = mock_response

        result = connector.create_test_run(
            access_event='publish',
            title='Run',
            group_title='Group1'
        )

        mock_post.assert_called_once_with(
            f'{connector.base_url}/api/reporter',
            json={
                "api_key": "test_api_key_123",
                "access_event": "publish",
                "title": "Run",
                "group_title": "Group1",
            }
        )

        assert result == {"uid": "run_123", "title": "Test Run"}

    @patch('requests.Session.post')
    def test_create_test_run_filters_none_values(self, mock_post, connector):
        """Test None values filtered"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"uid": "run_123"}
        mock_post.return_value = mock_response

        connector.create_test_run(
            title=None,
            access_event=None,
            group_title=None,
        )

        payload = mock_post.call_args[1]['json']
        expected_payload = {
            "api_key": "test_api_key_123",
        }
        assert payload == expected_payload

    @patch('requests.Session.post')
    def test_create_test_run_http_error(self, mock_post, connector):
        """Test HTTP error handled wher create test run"""
        mock_post.side_effect = HTTPError("HTTP Error")

        result = connector.create_test_run(
            None, None, None
        )
        assert result is None

    @patch('requests.Session.post')
    def test_update_test_status_success(self, mock_post, connector):
        """Test successful test status update"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        connector.update_test_status(
            run_id="run_123",
            status="passed",
            title="Test Login",
            suite_title="Auth Suite",
            test_id="test_789",
            file="file.robot",
            run_time=1.5,
        )

        assert mock_post.call_count == 1
        call_args = mock_post.call_args

        assert f'{connector.base_url}/api/reporter/run_123/testrun' in call_args[0][0]

        payload = call_args[1]['json']
        assert payload['status'] == 'passed'
        assert payload['suite_title'] == 'Auth Suite'
        assert payload['test_id'] == 'test_789'
        assert payload['file'] == 'file.robot'
        assert payload['title'] == 'Test Login'
        assert payload['run_time'] == 1.5

    @patch('requests.Session.post')
    def test_update_test_status_filters_none_values(self, mock_post, connector):
        """Test update test status filters keys with none value"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        connector.update_test_status(
            run_id="run_123",
            status="passed",
            title="Test Login",
            suite_title="Auth Suite",
            test_id="test_789",
            run_time=1.5,
            file=None
        )

        assert mock_post.call_count == 1
        call_args = mock_post.call_args

        assert f'{connector.base_url}/api/reporter/run_123/testrun' in call_args[0][0]

        payload = call_args[1]['json']
        assert payload['status'] == 'passed'
        assert payload['title'] == 'Test Login'
        assert payload['run_time'] == 1.5
        assert payload['suite_title'] == 'Auth Suite'
        assert payload['test_id'] == 'test_789'
        assert 'file' not in payload

    @patch('requests.Session.put')
    def test_finish_test_run(self, mock_put, connector):
        """Test finish test run"""
        connector.finish_test_run("run_123")

        mock_put.assert_called_once_with(
            f'{connector.base_url}/api/reporter/run_123?api_key={connector.api_key}',
            json={"status_event": "finish"}
        )

    @patch('requests.Session.put')
    def test_finish_test_run_connection_error(self, mock_put, connector):
        """Test handling connection error when finish test run"""
        mock_put.side_effect = ConnectionError("Connection failed")

        result = connector.finish_test_run("run_123")
        assert result is None

    def test_disconnect(self, connector):
        """Test session closed"""
        with patch.object(connector._session, 'close') as mock_close:
            connector.disconnect()
            assert mock_close.call_count == 1

    def test_session_property_getter(self, connector):
        """Test getter for session property"""
        with patch.object(connector, '_apply_proxy_settings') as mock_apply:
            session = connector.session

            assert session is connector._session
            assert mock_apply.call_count == 1

    def test_session_property_setter(self, connector):
        """Test setter for session property"""
        new_session = requests.Session()

        with patch.object(connector, '_apply_proxy_settings') as mock_apply:
            connector.session = new_session

            assert connector._session is new_session
            assert mock_apply.call_count == 1

    @patch('requests.Session.post')
    def test_batch_upload_success(self, mock_post, connector):
        """Test successful batch upload"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        tests = [{} for _ in range(0, 100)]
        run_id = 'AS23Fd'

        connector.batch_tests_upload(run_id, tests)

        assert mock_post.call_count == len(tests) / connector.batch_size
        call_args = mock_post.call_args

        assert f'{connector.base_url}/api/reporter/{run_id}/testrun' in call_args[0][0]

