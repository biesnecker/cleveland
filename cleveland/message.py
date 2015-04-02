import asyncio

class Message(object):

    def __init__(self, payload=None):
        self.payload = payload

    def __repr__(self):
        return 'Message (Payload: {0})'.format(self.payload)

# Special type of message that expects a response
class QueryMessage(Message):

    def __init__(self, payload=None):
        super().__init__(payload)
        self.result = asyncio.Future()

# Special type of message that tells actors to quit processing their inbox
class StopMessage(Message): pass