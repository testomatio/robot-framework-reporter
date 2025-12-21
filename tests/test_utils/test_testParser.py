import pathlib

import pytest
import tempfile
import shutil
from pathlib import Path

import robot.errors

from utils.test_parser import TestParser


@pytest.fixture
def robot_file_content():
    """Content based on string_test.robot"""
    return """*** Settings ***
Documentation    Tests work with strings
Library          String

*** Variables ***
${TEST_STRING}    Hello World
${EMPTY_STRING}    ${EMPTY}

*** Test Cases ***
Test String Length @Tc51dd44d
    [Documentation]    Check string length
    [Tags]    string    positive
    ${length}=    Get Length    ${TEST_STRING}
    Should Be Equal As Numbers    ${length}    11
    Log    String length: ${length}

Test String Contains @Td664d936
    [Documentation]    Check substring
    [Tags]    string    positive
    Should Contain    ${TEST_STRING}    World
    Should Contain    ${TEST_STRING}    Hello
    Log    String contains substrings

Test @tag @Td664d9fe
    [Documentation]    Test
    [Tags]    string
    Log    Simple test

Test Without ID with @tag
    [Documentation]    Test without ID
    [Tags]    string
    Log    Simple test without ID

Test Without ID
    [Documentation]    Test without ID
    [Tags]    string
    Log    Simple test without ID

*** Keywords ***
Convert To Uppercase
    [Arguments]    ${text}
    ${upper}=    Convert To Upper Case    ${text}
    RETURN    ${upper}
"""


@pytest.fixture
def temp_robot_file(robot_file_content):
    """Create temporary robot file for testing"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.robot', delete=False, encoding='utf-8')
    temp_file.write(robot_file_content)
    temp_file.close()

    yield temp_file.name

    Path(temp_file.name).unlink(missing_ok=True)


@pytest.fixture
def parser(temp_robot_file):
    """Create TestParser instance"""
    return TestParser(temp_robot_file)


class TestTestParserInitialization:

    def test_initialization(self, temp_robot_file):
        """Test TestParser initialization"""
        parser = TestParser(temp_robot_file)

        assert parser.file_path == temp_robot_file
        assert parser.model is not None

    def test_initialization_with_nonexistent_file(self):
        """Test initialization with non-existent file"""
        with pytest.raises(robot.errors.DataError):
            TestParser("/nonexistent/path/test.robot")

    def test_initialization_with_invalid_robot_file(self, tmp_path):
        """Test initialization with invalid robot file"""
        invalid_file = tmp_path / "invalid.robot"
        invalid_file.write_text("This is not a valid robot file content\n@#$%^&*()")

        # Should still create parser, but model might be empty/invalid
        parser = TestParser(str(invalid_file))
        assert parser.model is not None


class TestGetTestCode:

    def test_get_test_code_test_with_id(self, parser):
        """Test getting code for test with ID"""
        code = parser.get_test_code("Test String Length @Tc51dd44d")

        assert code is not None
        assert "Test String Length @Tc51dd44d" in code
        assert "[Documentation]    Check string length" in code
        assert "Get Length" in code

    def test_get_test_code_another_test(self, parser):
        """Test getting code for second test"""
        code = parser.get_test_code("Test String Contains @Td664d936")

        assert code is not None
        assert "Test String Contains @Td664d936" in code
        assert "[Documentation]    Check substring" in code
        assert "Should Contain" in code

    def test_get_test_code_test_without_id(self, parser):
        """Test getting code for test without ID"""
        code = parser.get_test_code("Test Without ID")

        assert code is not None
        assert "Test Without ID" in code
        assert "[Documentation]    Test without ID" in code

    def test_get_test_code_nonexistent_test(self, parser):
        """Test getting code for non-existent test"""
        code = parser.get_test_code("Nonexistent Test")

        assert code is None

    def test_get_test_code_preserves_indentation(self, parser):
        """Test that indentation is preserved in test code"""
        code = parser.get_test_code("Test String Length @Tc51dd44d")

        # Check that indentation is preserved
        lines = code.split('\n')
        assert any(line.startswith('    ') for line in lines)

    def test_get_test_code_includes_all_steps(self, parser):
        """Test that all test steps are included"""
        code = parser.get_test_code("Test String Length @Tc51dd44d")

        assert "Get Length" in code
        assert "Should Be Equal As Numbers" in code
        assert "Log" in code

    def test_get_test_code_case_sensitive(self, parser):
        """Test that test name search is case-sensitive"""
        code = parser.get_test_code("test string length")  # lowercase

        # Should not find "Test String Length" (with capital letters)
        assert code is None

    def test_get_test_code_partial_name_not_found(self, parser):
        """Test that partial test name doesn't match"""
        code = parser.get_test_code("Test String Length")  # without ID

        # Should not find because full name includes @Tc51dd44d
        assert code is None


class TestAssignTestId:

    def test_assign_test_id_to_test_without_id(self, parser, temp_robot_file):
        """Test assigning ID to test without ID"""
        parser.assign_test_id("Test Without ID", "@T99999")

        # Verify the change
        new_parser = TestParser(temp_robot_file)
        code = new_parser.get_test_code("Test Without ID @T99999")

        assert code is not None
        assert "Test Without ID @T99999" in code

    def test_assign_test_id_to_test_with_existing_id(self, parser, temp_robot_file):
        """Test assigning new ID to test with existing ID not dublicates ID"""
        parser.assign_test_id("Test String Length @Tc51dd44d", "@Tc51dd44d")

        new_parser = TestParser(temp_robot_file)
        code = new_parser.get_test_code("Test String Length @Tc51dd44d @Tc51dd44d")

        assert code is None

        code = new_parser.get_test_code("Test String Length @Tc51dd44d")

        assert code is not None

    def test_assign_test_id_preserves_tag_in_test_name(self, parser, temp_robot_file):
        """Test assigning new ID to test with non-existent ID preserve tag"""
        parser.assign_test_id("Test Without ID with @tag", "@Tc51dd44d")

        new_parser = TestParser(temp_robot_file)
        code = new_parser.get_test_code("Test Without ID with @tag @Tc51dd44d")

        assert code is not None

    def test_assign_test_id_nonexistent_test(self, parser):
        """Test assigning ID to non-existent test raises error"""
        with pytest.raises(ValueError, match="Test 'Nonexistent' not found"):
            parser.assign_test_id("Nonexistent", "@T123")

    def test_assign_test_id_saves_file(self, parser, temp_robot_file):
        """Test that assign_test_id saves changes to file"""
        parser.assign_test_id("Test Without ID", "@TSAVED")

        # Read file directly
        with open(temp_robot_file, 'r', encoding='utf-8') as f:
            content = f.read()

        assert "Test Without ID @TSAVED" in content

    def test_assign_test_id_preserves_other_tests(self, parser, temp_robot_file):
        """Test that assigning ID doesn't affect other tests"""
        parser.assign_test_id("Test Without ID", "@TNEW")

        # Check other tests are unchanged
        new_parser = TestParser(temp_robot_file)
        code = new_parser.get_test_code("Test String Length @Tc51dd44d")

        assert code is not None
        assert "Test String Length @Tc51dd44d" in code


class TestRemoveTestIds:

    def test_remove_test_ids_all_tests(self, parser, temp_robot_file):
        """Test removing IDs from all tests"""
        parser.remove_test_ids()

        # Read file directly
        with open(temp_robot_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # IDs should be removed
        assert "@Tc51dd44d" not in content
        assert "@Td664d936" not in content
        # Test names should remain (without IDs)
        assert "Test String Length" in content
        assert "Test String Contains" in content

    def test_remove_test_ids_preserves_tests_without_ids(self, parser, temp_robot_file):
        """Test that tests without IDs are preserved"""
        parser.remove_test_ids()

        new_parser = TestParser(temp_robot_file)
        code = new_parser.get_test_code("Test Without ID")

        assert code is not None
        assert "Test Without ID" in code

    def test_remove_test_ids_preserves_tags_in_name(self, parser, temp_robot_file):
        """Test that tags in test name preserved"""
        parser.remove_test_ids()

        new_parser = TestParser(temp_robot_file)
        code = new_parser.get_test_code("Test @tag")

        assert code is not None
        assert "Test @tag" in code
        assert "@Td664d9fe" not in code

    def test_remove_test_ids_saves_file(self, parser, temp_robot_file):
        """Test that remove_test_ids saves changes"""
        parser.remove_test_ids()

        # Create new parser to verify persistence
        new_parser = TestParser(temp_robot_file)

        # Try to find test with old name (should fail)
        code = new_parser.get_test_code("Test String Length @Tc51dd44d")
        assert code is None

        # Should find with new name (ID removed, trailing space)
        code = new_parser.get_test_code("Test String Length")
        assert code is not None

    def test_remove_test_ids_preserves_documentation(self, parser, temp_robot_file):
        """Test that remove_test_ids preserves test documentation and tags"""
        parser.remove_test_ids()

        new_parser = TestParser(temp_robot_file)
        code = new_parser.get_test_code("Test String Length")

        assert "[Documentation]    Check string length" in code
        assert "[Tags]    string    positive" in code

    def test_remove_test_ids_preserves_file_structure(self, parser, temp_robot_file):
        """Test that file structure is preserved after removing IDs"""
        parser.remove_test_ids()

        with open(temp_robot_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check structure is intact
        assert "*** Settings ***" in content
        assert "*** Variables ***" in content
        assert "*** Test Cases ***" in content
        assert "*** Keywords ***" in content


class TestFindTest:

    def test_find_test_existing(self, parser):
        """Test finding existing test"""
        test_node = parser._find_test("Test Without ID")

        assert test_node is not None
        assert hasattr(test_node, 'name')
        assert test_node.name == "Test Without ID"

    def test_find_test_with_id(self, parser):
        """Test finding test with ID"""
        test_node = parser._find_test("Test String Length @Tc51dd44d")

        assert test_node is not None
        assert test_node.name == "Test String Length @Tc51dd44d"

    def test_find_test_nonexistent(self, parser):
        """Test finding non-existent test returns None"""
        test_node = parser._find_test("Does Not Exist")

        assert test_node is None

    def test_find_test_case_sensitive(self, parser):
        """Test that search is case-sensitive"""
        test_node = parser._find_test("test without id")

        assert test_node is None


class TestFindTestEndLine:

    def test_find_test_end_line_with_end_lineno_attribute(self, parser):
        """Test finding end line when end_lineno attribute exists"""
        test_node = parser._find_test("Test Without ID")

        end_line = parser._find_test_end_line(test_node)

        assert isinstance(end_line, int)
        assert end_line > 0

    def test_find_test_end_line_manual_search(self, parser):
        """Test manual end line detection"""
        test_node = parser._find_test("Test String Length @Tc51dd44d")

        end_line = parser._find_test_end_line(test_node)

        assert isinstance(end_line, int)
        assert end_line > test_node.lineno


class TestUpdateName:

    def test_update_name_changes_token_value(self, parser):
        """Test that _update_name changes the token value"""
        test_node = parser._find_test("Test Without ID")

        parser._update_name(test_node, "Updated Test Name")

        # Check that token was updated
        from robot.parsing.lexer.tokens import Token
        for token in test_node.header.tokens:
            if token.type == Token.TESTCASE_NAME:
                assert token.value == "Updated Test Name"
                break
