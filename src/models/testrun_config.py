import os

TRUE_VARIANTS = {'True', 'true', 'TRUE', '1'}


class TestrunConfig:

    def __init__(self):
        self.run_id = os.getenv('TESTOMATIO_RUN', None)
        self.batch_upload_disabled = os.getenv('TESTOMATIO_DISABLE_BATCH_UPLOAD', None) in TRUE_VARIANTS
