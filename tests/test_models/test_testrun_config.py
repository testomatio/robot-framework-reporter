import pytest
import os
from unittest.mock import patch

from models.testrun_config import TestrunConfig, TRUE_VARIANTS


class TestTestRunConfig:
    """Tests for TestRunConfig class"""

    def test_init_default_values(self):
        """Test init with default values"""
        with patch.dict(os.environ, {}, clear=True):
            config = TestrunConfig()

            assert config.access_event is None
            assert config.run_id is None
            assert config.batch_upload_disabled is False
            assert config.title is None
            assert config.group_title is None

    def test_init_with_env_variables(self):
        """Test init with env vars"""
        env_vars = {
            'TESTOMATIO_RUN': 'run_12345',
            'TESTOMATIO_DISABLE_BATCH_UPLOAD': 'True',
            'TESTOMATIO_PUBLISH': 'True',
            'TESTOMATIO_TITLE': 'Run1',
            'TESTOMATIO_RUNGROUP_TITLE': 'Group'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = TestrunConfig()

            assert config.run_id == 'run_12345'
            assert config.batch_upload_disabled is True
            assert config.access_event == 'publish'
            assert config.title == 'Run1'
            assert config.group_title == 'Group'

    @pytest.mark.parametrize('value', TRUE_VARIANTS)
    def test_init_disable_batch_upload_true_variations(self, value):
        """Test different true values for TESTOMATIO_DISABLE_BATCH_UPLOAD"""
        with patch.dict(os.environ, {'TESTOMATIO_DISABLE_BATCH_UPLOAD': value}, clear=True):
            config = TestrunConfig()

            assert config.batch_upload_disabled is True

    @pytest.mark.parametrize('value', ['False', 'false', '0', 'anything'])
    def test_init_disable_batch_upload_false_variations(self, value):
        """Test different false values TESTOMATIO_DISABLE_BATCH_UPLOAD"""
        with patch.dict(os.environ, {'TESTOMATIO_DISABLE_BATCH_UPLOAD': value}, clear=True):
            config = TestrunConfig()

            assert config.batch_upload_disabled is False

    @pytest.mark.parametrize('value', TRUE_VARIANTS)
    def test_init_access_event_true_variations(self, value):
        """Test different true values for TESTOMATIO_PUBLISH"""
        with patch.dict(os.environ, {'TESTOMATIO_PUBLISH': value}, clear=True):
            config = TestrunConfig()

            assert config.access_event is 'publish'

    @pytest.mark.parametrize('value', ['False', 'false', '0', 'anything'])
    def test_init_access_event_false_variations(self, value):
        """Test different false values for TESTOMATIO_PUBLISH"""
        with patch.dict(os.environ, {'TESTOMATIO_PUBLISH': value}, clear=True):
            config = TestrunConfig()

            assert config.access_event is None
