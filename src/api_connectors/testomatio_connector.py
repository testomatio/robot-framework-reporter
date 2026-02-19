
import requests
import logging
import time
import os
from os import getenv
from os.path import join, normpath
from requests.exceptions import HTTPError, ConnectionError

from api_connectors.exception import ReportFailedException
from models.test_item import TestItem
from utils.utils import safe_string_list

MAX_RETRIES_DEFAULT = 5
RETRY_INTERVAL_DEFAULT = 5
DEFAULT_BATCH_SIZE = 50

log = logging.getLogger('testomatio_rf_reporter')

FORBIDDEN_MESSAGE = 'Authentication failed. Please check your Testomatio project token. It may be invalid or expired'


class MaxRetriesException(Exception):
    pass


class Connector:
    def __init__(self, base_url: str = '', api_key: str = None):
        max_retries = os.environ.get('TESTOMATIO_MAX_REQUEST_FAILURES', '')
        retry_interval = os.environ.get('TESTOMATIO_REQUEST_INTERVAL', '')
        batch_size = os.environ.get('TESTOMATIO_BATCH_SIZE', '')
        self.base_url = base_url
        self._session = requests.Session()
        self.jwt: str = ''
        self.api_key = api_key
        self.max_retries = int(max_retries) if max_retries.isdigit() else MAX_RETRIES_DEFAULT
        self.retry_interval = int(retry_interval) if retry_interval.isdigit() else RETRY_INTERVAL_DEFAULT
        self.batch_size = int(batch_size) if (batch_size.isdigit() and int(batch_size) <= 100) else DEFAULT_BATCH_SIZE

    @property
    def session(self):
        """Get the session, creating it and applying proxy settings if necessary."""
        self._apply_proxy_settings()
        return self._session

    @session.setter
    def session(self, value):
        """Allow setting a custom session, while still applying proxy settings."""
        self._session = value
        self._apply_proxy_settings()

    def _apply_proxy_settings(self):
        """Apply proxy settings based on environment variables, fallback to no proxy if unavailable."""
        http_proxy = getenv("HTTP_PROXY")
        log.debug(f"HTTP_PROXY: {http_proxy}")
        if http_proxy:
            self._session.proxies = {"http": http_proxy, "https": http_proxy}
            self._session.verify = False
            log.debug(f"Proxy settings applied: {self._session.proxies}")

            if not self._test_proxy_connection(timeout=1):
                log.debug("Proxy is unavailable. Falling back to a direct connection.")
                self._session.proxies.clear()
                self._session.verify = True
        else:
            log.debug("No proxy settings found. Using a direct connection.")
            self._session.proxies.clear()
            self._session.verify = True
            self._test_proxy_connection()

    def _test_proxy_connection(self, test_url="https://api.ipify.org?format=json", timeout=30, retry_interval=1):
        log.debug("Current session: %s", self._session.proxies)
        log.debug("Current verify: %s", self._session.verify)

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self._session.get(test_url, timeout=5)
                response.raise_for_status()
                log.debug("Internet connection is available.")
                return True
            except requests.exceptions.RequestException as e:
                log.error("Internet connection is unavailable. Error: %s", e)
                time.sleep(retry_interval)

        log.error("Internet connection check timed out after %d seconds.", timeout)
        return False

    def _should_retry(self, response: requests.Response) -> bool:
        """Checks if request should be retried.
        Retry only on 501+ status codes
        """
        return response.status_code >= 501

    def _send_request_with_retry(self, method: str, url: str, **kwargs):
        """Send HTTP request with retry logic"""
        for attempt in range(self.max_retries):
            log.debug(f'Trying to send request to {self.base_url}. Attempt {attempt+1}/{self.max_retries}')
            try:
                request_func = getattr(self.session, method)
                response = request_func(url, **kwargs)

                if self._should_retry(response):
                    if attempt < self.max_retries:
                        log.error(f'Request attempt failed. Response code: {response.status_code}. '
                                  f'Retrying in {self.retry_interval} seconds')
                        time.sleep(self.retry_interval)
                        continue

                return response
            except ConnectionError as ce:
                log.error(f'Failed to connect to {self.base_url}: {ce}')
                raise
            except HTTPError as he:
                log.error(f'HTTP error occurred while connecting to {self.base_url}: {he}')
                raise
            except Exception as e:
                log.error(f'An unexpected exception occurred. Please report an issue: {e}')
                raise

        log.error(f'Retries attempts exceeded.')
        raise MaxRetriesException()

    def load_tests(
            self,
            tests: list[TestItem],
            no_empty: bool = False,
            no_detach: bool = False,
            structure: bool = False,
            create: bool = False,
            directory: str = None
    ):
        # TODO: add description import. Change framework to RF when implemented on backend
        request = {
            "framework": "pytest",
            "language": "python",
            "noempty": no_empty,
            "no-detach": no_detach,
            "structure": structure if not no_empty else False,
            "create": create,
            "sync": True,
            "tests": []
        }
        for test in tests:
            request['tests'].append({
                "name": test.title,
                "suites": [
                    test.suite_title
                ],
                "code": test.source_code,
                "file": str(test.file_path) if structure else (
                    test.file if directory is None else normpath(join(directory, test.file))),
                "labels": safe_string_list(getenv('TESTOMATIO_SYNC_LABELS')),
            })
        try:
            response = self._send_request_with_retry('post', f'{self.base_url}/api/load?api_key={self.api_key}', json=request)
        except Exception as e:
            log.error(f'Failed to import tests')
            return

        if response.status_code < 400:
            log.info(f'Tests loaded to {self.base_url}')
        elif response.status_code == 403:
            log.error(FORBIDDEN_MESSAGE)
        else:
            log.error(f'Failed to load tests to {self.base_url}. Status code: {response.status_code}')

    def get_tests(self) -> dict|None:
        try:
            response = self._send_request_with_retry('get', f'{self.base_url}/api/test_data?api_key={self.api_key}')
            if response.status_code == 200:
                log.info(f'Test ids received')
                return response.json()
            elif response.status_code == 403:
                log.error(FORBIDDEN_MESSAGE)
        except Exception as e:
            log.error(f'Failed to get test ids')
            return

    def create_test_run(self, access_event: str | None, title: str | None, group_title: str | None) -> dict | None:
        # TODO: add labels, kind, shared run, envs
        request = {
            "api_key": self.api_key,
            "access_event": access_event,
            "title": title,
            "group_title": group_title
        }
        filtered_request = {k: v for k, v in request.items() if v is not None}
        try:
            response = self._send_request_with_retry('post', f'{self.base_url}/api/reporter', json=filtered_request)
        except Exception as e:
            log.error(f'Failed to create run on Testomat.io')
            return

        if response.status_code == 200:
            log.info(f'Test run created {response.json()["uid"]}')
            return response.json()
        elif response.status_code == 403:
            log.error(FORBIDDEN_MESSAGE)

    def update_test_status(self, run_id: str,
                           status: str,
                           title: str,
                           suite_title: str,
                           file: str,
                           test_id: str,
                           run_time: float) -> None:
        # TODO: add rid, suite_id, message, stack, artifacts, steps, overwrite, meta, example
        request = {
            "status": status,
            "title": title,
            "suite_title": suite_title,
            "test_id": test_id,
            "file": file,
            "run_time": run_time,
        }
        filtered_request = {k: v for k, v in request.items() if v is not None}
        try:
            response = self._send_request_with_retry('post', f'{self.base_url}/api/reporter/{run_id}/testrun?api_key={self.api_key}',
                                                     json=filtered_request)
        except Exception as e:
            log.error(f'Failed to report test')
            return
        if response.status_code == 200:
            log.info('Test status updated')
        elif response.status_code == 403:
            log.error(FORBIDDEN_MESSAGE)
            raise ReportFailedException

    def batch_tests_upload(self, run_id: str,
                           tests: list) -> None:
        if not tests:
            log.info(f'No tests to report. Report skipped')
            return

        try:
            batch_size = self.batch_size
            log.info(f'Starting batch test report into test run. Run id: {run_id}, number of tests: {len(tests)}, '
                     f'batch size: {batch_size}')
            for i in range(0, len(tests), batch_size):
                batch = tests[i:i+batch_size]
                batch_index = i // batch_size + 1
                request = {
                    'tests': batch,
                    'batch_index': batch_index
                }
                response = self._send_request_with_retry('post', f'{self.base_url}/api/reporter/{run_id}/testrun?api_key={self.api_key}',
                                                         json=request)
                if response.status_code == 200:
                    log.info(f'Tests status updated. Batch index: {batch_index}')
                elif response.status_code == 403:
                    log.error(FORBIDDEN_MESSAGE)
                    raise ReportFailedException
        except ReportFailedException as e:
            raise
        except Exception as e:
            log.error(f'Failed to report test')
            return

    def finish_test_run(self, run_id: str) -> None:
        try:
            response = self._send_request_with_retry('put', f'{self.base_url}/api/reporter/{run_id}?api_key={self.api_key}',
                                                     json={"status_event": "finish"}
                                                    )
            if response.status_code == 403:
                log.error(FORBIDDEN_MESSAGE)
        except Exception as e:
            log.error(f'Failed to finish run')
            return

    def disconnect(self):
        self.session.close()
