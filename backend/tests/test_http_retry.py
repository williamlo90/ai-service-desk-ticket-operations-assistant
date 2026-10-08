import json,unittest
from io import BytesIO
from urllib.error import HTTPError,URLError
from service_desk.http_retry import recovery_post,TransportStopped


class Opener:
    def __init__(self,items):self.items=iter(items);self.calls=0
    def open(self,*args,**kwargs):
        self.calls+=1;value=next(self.items)
        if isinstance(value,Exception):raise value
        return BytesIO(json.dumps(value).encode())


class HttpRetryTests(unittest.TestCase):
    def error(self,code,after=''):
        return HTTPError('http://fixture/recovery',code,'synthetic',{'Retry-After':after},None)
    def test_lost_reply_and_503_redeliver_bounded(self):
        opener=Opener([URLError('lost'),self.error(503),{'done':True}]);delays=[]
        self.assertTrue(recovery_post('http://fixture/recovery','fixture',{},opener=opener,sleep=delays.append)['done'])
        self.assertEqual(delays,[1,2]);self.assertEqual(opener.calls,3)
    def test_terminal_and_redirect_do_not_retry(self):
        for status in (401,403,404,302):
            opener=Opener([self.error(status)])
            with self.assertRaises(TransportStopped):recovery_post('http://fixture/recovery','fixture',{},opener=opener,sleep=lambda _:self.fail())
            self.assertEqual(opener.calls,1)
    def test_retry_after_is_honored(self):
        opener=Opener([self.error(429,'3'),{'done':False}]);delays=[]
        recovery_post('http://fixture/recovery','fixture',{},opener=opener,sleep=delays.append)
        self.assertEqual(delays,[3])
    def test_exhaustion_is_four_calls(self):
        opener=Opener([self.error(503)]*4);delays=[]
        with self.assertRaisesRegex(TransportStopped,'transport_exhausted'):
            recovery_post('http://fixture/recovery','fixture',{},opener=opener,sleep=delays.append)
        self.assertEqual(opener.calls,4);self.assertEqual(delays,[1,2,4])
    def test_long_retry_after_requires_review(self):
        opener=Opener([self.error(429,'3600')])
        with self.assertRaisesRegex(TransportStopped,'requires_review'):
            recovery_post('http://fixture/recovery','fixture',{},opener=opener,sleep=lambda _:self.fail())
