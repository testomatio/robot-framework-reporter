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

            assert config.run_id is None
            assert config.batch_upload_disabled is False

    def test_init_with_env_variables(self):
        """Test init with env vars"""
        env_vars = {
            'TESTOMATIO_RUN': 'run_12345',
            'TESTOMATIO_DISABLE_BATCH_UPLOAD': 'True',
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = TestrunConfig()

            assert config.run_id == 'run_12345'
            assert config.batch_upload_disabled is True

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
