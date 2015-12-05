import asyncio


class Message(object):

    def __init__(self, payload=None):
        self.payload = payload

    def __repr__(self):
        return 'Message (Payload: {0})'.format(self.payload)


class QueryMessage(Message):
    '''Special type of message that expects a response'''
  
    result = None
    '''Future, set in ``AbstractActor.ask`` if not set by user'''


class StopMessage(Message):
    '''Special type of message that tells actors to quit processing 
    their inbox
    '''

