class TestomatItem:

    def __init__(self, test_id: str, title: str, file_name: str, suite: str):
        self.id = test_id
        self.title = title
        self.file_name = file_name
        self.suite = suite

    def __str__(self) -> str:
        return f'TestomatItem: {self.id} - {self.title} - {self.suite} - {self.file_name}'

    def __repr__(self):
        return f'TestomatItem: {self.id} - {self.title} - {self.suite} - {self.file_name}'
