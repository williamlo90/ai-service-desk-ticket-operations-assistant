import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
import json
import socket
from threading import Thread,Lock
from urllib.request import Request,urlopen

spec=importlib.util.spec_from_file_location('business_pilot',Path(__file__).resolve().parents[2]/'scripts/business_pilot.py')
pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)
TASK={'id':'test','pair':'test','condition':'manual','text':'I need read access to reports.',
      'advice':None,'expected_category':'access_request','expected_missing':['requester_identity']}
ANSWER={'category':'access_request','missing':['requester_identity'],
        'evidence':'I need read access to reports.','next_step':'clarify'}


class PilotTests(unittest.TestCase):
    def test_idle_browser_connection_does_not_block_other_requests(self):
        with TemporaryDirectory() as folder,patch.object(pilot,'tasks',return_value=[TASK]):
            server=pilot.ThreadingHTTPServer(('127.0.0.1',0),pilot.Handler)
            server.study=pilot.Study(Path(folder)/'study.json');server.study_lock=Lock()
            thread=Thread(target=server.serve_forever,daemon=True);thread.start()
            idle=socket.create_connection(server.server_address,timeout=2)
            try:
                url='http://127.0.0.1:'+str(server.server_port)+'/state'
                request=Request(url,headers={'Host':f'127.0.0.1:{pilot.PORT}'})
                with urlopen(request,timeout=2) as response:state=json.loads(response.read())
                self.assertFalse(state['running']);self.assertEqual(state['index'],0)
                self.assertFalse(server.study.path.exists())
            finally:
                idle.close();server.shutdown();server.server_close();thread.join(2)

    def test_read_does_not_start_timer_or_disclose_answer(self):
        with TemporaryDirectory() as folder,patch.object(pilot,'tasks',return_value=[TASK]):
            study=pilot.Study(Path(folder)/'study.json');state=study.state()
            self.assertFalse(state['running'])
            self.assertNotIn('expected_missing',state['task'])
            self.assertFalse(study.path.exists())

    def test_pause_excluded_and_resume_persists_completed_observation(self):
        with TemporaryDirectory() as folder,patch.object(pilot,'tasks',return_value=[TASK]),patch.object(pilot,'monotonic',side_effect=[10,20,40,55]):
            p=Path(folder)/'study.json';study=pilot.Study(p)
            study.act('start',{});study.act('pause',{});study.act('resume',{});study.act('submit',ANSWER)
            row=study.rows[0]
            self.assertEqual(row['elapsed_seconds'],45)
            self.assertEqual(row['active_seconds'],25)
            self.assertEqual(row['interruption_seconds'],20)
            self.assertTrue(row['correct_automatic_rubric'])
            self.assertIsNone(pilot.Study(p).state()['task'])

    def test_unstarted_and_paused_submit_rejected(self):
        with TemporaryDirectory() as folder,patch.object(pilot,'tasks',return_value=[TASK]):
            study=pilot.Study(Path(folder)/'study.json')
            with self.assertRaises(ValueError):study.act('submit',ANSWER)
            study.act('start',{});study.act('pause',{})
            with self.assertRaises(ValueError):study.act('submit',ANSWER)
            self.assertFalse(study.path.exists())

    def test_wrong_answer_retained_as_failure(self):
        with TemporaryDirectory() as folder,patch.object(pilot,'tasks',return_value=[TASK]):
            study=pilot.Study(Path(folder)/'study.json');study.act('start',{})
            study.act('submit',{**ANSWER,'category':'unsupported'})
            self.assertFalse(study.rows[0]['correct_automatic_rubric'])
