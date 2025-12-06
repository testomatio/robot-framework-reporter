import pytest
from models.testomat_item import TestomatItem


class TestTestomatItem:

    def test_initialization(self):
        """Test creating TestomatItem with all parameters"""
        item = TestomatItem(
            test_id="12345",
            title="Login Test",
            file_name="test_auth.robot",
            suite="Authentication Suite"
        )

        assert item.id == "12345"
        assert item.title == "Login Test"
        assert item.file_name == "test_auth.robot"
        assert item.suite == "Authentication Suite"
