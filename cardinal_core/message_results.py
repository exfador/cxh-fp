class MessageSendFailure(list):
    def __init__(self, sent_messages):
        super().__init__()
        self.sent_messages = tuple(sent_messages)
