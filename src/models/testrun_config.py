import os

TRUE_VARIANTS = {'True', 'true', 'TRUE', '1'}


class TestrunConfig:

    def __init__(self):
        self.run_id = os.getenv('TESTOMATIO_RUN', None)
        self.access_event = 'publish' if os.environ.get("TESTOMATIO_PUBLISH", None) in TRUE_VARIANTS else None
        self.batch_upload_disabled = os.getenv('TESTOMATIO_DISABLE_BATCH_UPLOAD', None) in TRUE_VARIANTS
        self.title = os.getenv('TESTOMATIO_TITLE', None)
        self.group_title = os.getenv('TESTOMATIO_RUNGROUP_TITLE', None)

    def to_dict(self):
        result = {
            'access_event': self.access_event,
            'title': self.title,
            'group_title': self.group_title,
        }
        return result
