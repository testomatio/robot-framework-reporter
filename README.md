[![Support Ukraine Badge](https://bit.ly/support-ukraine-now)](https://github.com/support-ukraine/support-ukraine)

# Testomat.io plugin for Robot Framework
A powerful plugin that integrates your tests with [Testomat.io](https://testomat.io) platform for test management, reporting and analytics

## Features
- ✅ Sync tests with testomat.io
- 📊 Real-time test execution reporting

## Uses testomat.io API:

- https://testomatio.github.io/check-tests/ - for sync
- https://testomatio.github.io/reporter/ - for reporting

## Table of Contents
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Advanced Usage](#advanced-usage)
  - [Basic Configuration](#basic-configuration)
  - [Import Listener](#import-listener)
    - [Listener Configuration](#import-listener-configuration)
    - [Clean Test IDs](#clean-test-ids)
    - [Disable Detach Test](#detaching-tests)
    - [Remove Empty Suites](#removing-empty-suites)
    - [Keep Test IDs Between Projects](#keep-test-ids-between-projects)
    - [Keep structure](#keep-structure)
  - [Report Listener](#report-listener)
    - [Listener Configuration](#report-listener-configuration)

## Installation
Prerequisites:
 - Python 3.10+
 - Robot Framework 4.0+
 - Active [testomat.io](https://testomat.io) account 

Install via pip:
```bash
pip install robot-framework-reporter
```
## Quick Start

### Get your API token
1. Login to [Testomat.io](https://testomat.io)
2. Create project or go to existing project
3. Click on "Import Tests from Source Code"
4. Copy your project token(starts with "tstmt_")
### Sync tests
Synchronize tests to Testomat.io using **ImportListener**:
```bash
TESTOMATIO=your_token robot --listener Testomatio.ImportListener path/to/tests
```
### Report tests
Execute tests and send results to Testomat.io using **ReportListener**:
```bash
TESTOMATIO=your_token robot --listener Testomatio.ReportListener path/to/tests
```
### Example of test

After importing tests to Testomat.io, each test is automatically assigned a unique Test ID.  
Testomat.io Test ID is a string value that starts with `@T` and contains 8 characters after.

Test ID is appended to the test name:
```robotframework
*** Test Cases ***
Test Addition @T96c700e6
    [Documentation]    Check addition of two numbers
    [Tags]    math    positive
    ${result}=    Evaluate    10 + 5
    Should Be Equal As Numbers    ${result}    15
```

**Before import** (original test):
```robotframework
*** Test Cases ***
Test Addition
    [Documentation]    Check addition of two numbers
    [Tags]    math    positive
    ${result}=    Evaluate    10 + 5
    Should Be Equal As Numbers    ${result}    15
```

**After import** (with Test ID):
```robotframework
*** Test Cases ***
Test Addition @T96c700e6
    [Documentation]    Check addition of two numbers
    [Tags]    math    positive
    ${result}=    Evaluate    10 + 5
    Should Be Equal As Numbers    ${result}    15
```

> 💡 **Note:** Test ID is added automatically to the test name when using `ImportListener`. You don't need to add them manually.

## Advanced Usage

 Testomat.io integration with Robot Framework is implemented through the Listener Interface. Currently, two Listeners are available:
- **ImportListener**. Used for synchronizing tests with Testomat.io
- **ReportListener**. Used for reporting test results to Testomat.io

### Basic Configuration

 Listeners can be configured through parameters or environment variables. Each Listener has its own configuration options, which are described in the corresponding sections.

> 💡 **Note:** Parameters and environment variables configure different aspects of the Listener's behavior. Each configuration option is available through only one method - either as a parameter or as an environment variable, not both.

#### Common Environment Variables

Both Listeners use the following environment variables:

| Variable      | Description                                 | Required | Default                   |
|---------------|---------------------------------------------|----------|---------------------------|
| `TESTOMATIO`  | API key for accessing Testomat.io           | ✅ Yes    | -                         |
| `TESTOMATIO_URL` | Testomat.io server URL                      | ➖ No     | `https://app.testomat.io` |
| `TESTOMATIO_REQUEST_INTERVAL` | Interval between requests to Testomat.io in seconds | ➖ No     | `5` |
| `TESTOMATIO_MAX_REQUEST_FAILURES`| Max attempts to send request to Testomat.io | ➖ No     | `5` |

### Import Listener
Used for importing tests to Testomat.io.
#### Import Listener Configuration
###### Environment variables
| Variable                      | Description                                                                                                                                                                                      | Required | Default |
|-------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|---------|
 | `TESTOMATIO_IMPORT_DIRECTORY` | Specifies directory where tests will be imported                                                                                                                                                 | ➖ No     | `None`  |
| `TESTOMATIO_SYNC_LABELS`      | Assign labels to a test case when you import test to Testomat.io. <br/>Labels must exist in project and their scope must be enabled for tests. To pass multiple labels, separate them by a comma | ➖ No     | `None`  |

###### Listener Parameters
| Parameter  | Description                                                    | Required | Type  | Default |
|------------|----------------------------------------------------------------|------|-------|---------|
| remove_ids | Remove all test ids from source code                           |➖ No|`bool`|`False`|
| no_detach  | Disables detaching tests on Testomat.io                        | ➖ No |`bool`|`False`|
| no_empty   | Removes empty suites on Testomat.io                            | ➖ No |`bool`|`False`|
| create     | Use to import Test ids set in source code into another project | ➖ No |`bool`|`False`|
| structure  | Force to keep original file structure                          | ➖ No |`bool`|`False`|
#### Clean Test IDs
If you want to import the synced project as new project, you have to clean the test ids. To clean up test ids  use **remove_ids** parameter:
```bash
TESTOMATIO=your_key robot --listener Testomatio.ImportListener:remove_ids=1 path/to/tests
```
This method may be unsafe, as it cleans all @T* tags from tests names. So if you have a tag like @Test1234 in test name this may also be removed. If you use this option make sure if all the test titles a proper before committing the tests in GIT.
#### Detaching tests
If a test from a previous import was not found on next import it is marked as "detached". This is done to ensure that deleted tests are not staying in Testomatio while deleted in codebase.

To disable this behavior and don't mark anything on detached on import use **no_detach** parameter:
```bash
TESTOMATIO=your_key robot --listener Testomatio.ImportListener:no_detach=1 path/to/tests
```
#### Removing empty suites
If tests were marked with IDs and imported to already created suites in Testomat.io newly imported suites may become empty. Use **no_empty** parameter to clean them up after import.
```bash
TESTOMATIO=your_key robot --listener Testomatio.ImportListener:no_empty=1 path/to/tests
```
This prevents usage **structure** parameter.
#### Keep Test IDs between projects
To import tests with Test IDs set in source code into another project use **create** parameter. In this case, a new project will be populated with the same Test IDs.
```bash
TESTOMATIO=your_key robot --listener Testomatio.ImportListener:create=1 path/to/tests
```
#### Keep structure
When tests in source code have IDs assigned and those tests are imported, Testomat.io uses current structure in a project to put the tests in. If folders in source code doesn't match folders in Testomat.io project, existing structure in source code will be ignored. To force using the structure from the source code, use **structure** parameter on import:
```bash
TESTOMATIO=your_key robot --listener Testomatio.ImportListener:structure=1 path/to/tests
```
### Report Listener
Used for reporting test results to Testomat.io. By default, sends test results in batches after each test suite completes.
#### Report Listener Configuration

###### Environment variables
| Variable                          | Description                                                                            | Required | Default |
|-----------------------------------|----------------------------------------------------------------------------------------|----------|---------|
 | `TESTOMATIO_DISABLE_BATCH_UPLOAD` | Disables batch uploading and uploads each test result one by one                       | ➖ No     | `False` |
 | `TESTOMATIO_BATCH_SIZE`           | Changes size of batch for batch uploading. Maximum is 100.                             | ➖ No     | `50`    |
 | `TESTOMATIO_RUN`                  | Id of existing test run to use for sending test results to                             | ➖ No     | `None`  |
| `TESTOMATIO_PUBLISH`              | Publish run after reporting and provide a public URL                                   | ➖ No     | `False` |
| `TESTOMATIO_TITLE`                | Name of a test run to create on Testomat.io                                            | ➖ No     | `None`  |
| `TESTOMATIO_RUNGROUP_TITLE`       | Create a group (folder) for a test run. If group already exists, attach test run to it | ➖ No     | `None`  |

###### Listener Parameters
Currently, has no parameters