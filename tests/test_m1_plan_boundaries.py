"""M1 real-store, safe CLI, no-effects and failure acceptance cases."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from unittest.mock import Mock, patch
from uuid import uuid4

import test_m0_acceptance as m0
from test_m1_plans import M1Harness
from app.baseline_contracts import M0Error
from app.core.review_store import ReviewStore
from app.plan_cli import main
from app.plan_contracts import canonical_plan_bytes, parse_plan
from app.core.plan_policy import assess_plan
from app.core.plan_service import inspect_plan, prepare_plan


def cli(*arguments):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(arguments))
    return code, out.getvalue(), err.getvalue()


class PlanBoundaries(M1Harness):
    def write_draft(self, data=None):
        path = self.root / ('draft-' + str(uuid4()) + '.json')
        path.write_text(self.draft(data).model_dump_json(), encoding='utf-8')
        return str(path)

    def write_plan(self, plan=None):
        path = self.root / ('plan-' + str(uuid4()) + '.json')
        path.write_bytes(canonical_plan_bytes(plan or self.plan()))
        return str(path)

    def test_m1_ac_01_real_store_admission(self):
        before = self.db.read_bytes()
        result = inspect_plan(self.store, self.plan())
        self.assertEqual('ready_for_artifact_design', result.disposition)
        self.assertEqual((1, 1, 0, 0, 1), (result.total_criteria, result.planned_criteria,
            result.unplanned_criteria, result.unsupported_criteria, result.scenario_count))
        self.assertEqual(self.snapshot.digest, result.baseline_digest)
        self.assertIs(False, result.plan_approved)
        self.assertIs(False, result.execution_authorized)
        self.assertEqual(before, self.db.read_bytes())
        scenario = self.plan().scenarios[0]
        criterion = next(c for c in self.snapshot.criteria if c.criterion_id == scenario.criterion_id)
        self.assertIn(criterion.requirement_id, {r.requirement_id for r in self.snapshot.requirements})
        self.assertTrue(set(criterion.source_ids) <= {s.evidence_id for s in self.snapshot.sources})

    def test_m1_ac_02_inactive_states_and_legacy_flags(self):
        pending = self.successor(approve=False)
        self.assertEqual('pending', inspect_plan(self.store, self.plan(self.plan_data(pending), pending)).baseline_status)
        self.review(pending, 'reject')
        result = inspect_plan(self.store, self.plan(self.plan_data(pending), pending))
        self.assertEqual(('rejected', 'blocked'), (result.baseline_status, result.disposition))
        successor = self.successor(lambda data: data['criteria'][0].update(expected_outcome='Exactly six cards.'))
        old = inspect_plan(self.store, self.plan())
        self.assertEqual(('superseded', 'blocked'), (old.baseline_status, old.disposition))
        self.review(successor, 'revoke')
        result = inspect_plan(self.store, self.plan(self.plan_data(successor), successor))
        self.assertEqual(('revoked', 'blocked', None), (result.baseline_status, result.disposition, result.active_digest))
        for flag in ('approved', 'rejected', 'actor'):
            data = self.plan_data(); data[flag] = True
            self.assertPlanError('UNKNOWN_FIELD', self.draft, data)

    def test_m1_ac_03_fresh_assessment_after_authority_change(self):
        plan = self.plan()
        original = canonical_plan_bytes(plan)
        self.assertEqual('ready_for_artifact_design', inspect_plan(self.store, plan).disposition)
        self.review(self.snapshot, 'revoke')
        self.assertEqual('blocked', inspect_plan(self.store, plan).disposition)
        self.assertEqual(original, canonical_plan_bytes(plan))
        self.assertEqual(['approve', 'revoke'], [r.decision for r in self.store.history(m0.PROJECT).decisions])

    def test_m1_ac_04_old_decision_and_serialized_assessment_are_not_authority(self):
        original = self.store.history(m0.PROJECT).decisions[0]
        plan = self.plan()
        cached = inspect_plan(self.store, plan)
        self.review(self.snapshot, 'revoke')
        self.assertEqual('approve', original.decision)
        self.assertEqual('blocked', inspect_plan(self.store, plan).disposition)
        self.assertPlanError('AUTHORITY_MISMATCH', assess_plan, plan, cached)
        self.assertPlanError('AUTHORITY_MISMATCH', assess_plan, plan, original)
        self.assertPlanError('AUTHORITY_MISMATCH', assess_plan, plan,
            self.store.inspect(m0.PROJECT, self.snapshot.digest).model_dump(mode='json'))

    def test_m1_ac_05_inconsistent_inspection_is_not_a_blocked_success(self):
        observation = self.store.inspect(m0.PROJECT, self.snapshot.digest)
        for field, value in [('project_id', str(uuid4())), ('subject_digest', 'sha256:'+'0'*64),
                             ('active_digest', None), ('head_digest', None), ('decision_sequence', None),
                             ('decision_sequence', 2), ('status', 'pending')]:
            with self.subTest(field=field, value=value):
                changed = observation.model_copy(update={'review': observation.review.model_copy(update={field:value})})
                fake = Mock(spec=['inspect']); fake.inspect.return_value = changed
                self.assertPlanError('AUTHORITY_MISMATCH', inspect_plan, fake, self.plan())
                fake.inspect.assert_called_once_with(m0.PROJECT, self.snapshot.digest)
        for invalid in (None, observation.model_dump(mode='json'), self.store.history(m0.PROJECT).decisions[0]):
            fake = Mock(spec=['inspect']); fake.inspect.return_value = invalid
            self.assertPlanError('AUTHORITY_MISMATCH', prepare_plan, fake, self.draft())
        wrong = self.plan().model_dump(mode='json', exclude={'digest'})
        wrong['project_id'] = str(uuid4())
        for item in wrong['scenarios']:
            from app.plan_contracts import scenario_id
            item['scenario_id'] = scenario_id(wrong['project_id'], item['criterion_id'], item['scenario_key'])
        self.assertPlanError('AUTHORITY_MISMATCH', self.plan, wrong)

    def test_m1_ac_06_unrelated_review_sequence_does_not_revoke(self):
        before = inspect_plan(self.store, self.plan())
        subject = self.successor(approve=False)
        self.review(subject, 'reject')
        after = inspect_plan(self.store, self.plan())
        self.assertEqual('ready_for_artifact_design', after.disposition)
        self.assertEqual(before.decision_sequence, after.decision_sequence)
        self.assertEqual(before.project_sequence+1, after.project_sequence)

    def test_m1_ac_21_store_errors_never_trigger_write_recovery(self):
        plan_path = self.write_plan()
        missing = self.root/'missing.sqlite3'
        code, out, err = cli('assess', '--db', str(missing), '--plan', plan_path)
        self.assertEqual((4, ''), (code, out)); self.assertFalse(missing.exists())
        self.assertEqual('STORE_NOT_FOUND', json.loads(err)['code'])
        wrong = self.root/'future.sqlite3'
        with contextlib.closing(sqlite3.connect(wrong)) as connection:
            connection.execute('PRAGMA user_version=2')
        before = wrong.read_bytes()
        self.assertEqual(4, cli('assess','--db',str(wrong),'--plan',plan_path)[0])
        self.assertEqual(before, wrong.read_bytes())
        corrupt = self.root/'corrupt.sqlite3'; corrupt.write_bytes(b'Not a SQLite database')
        before = corrupt.read_bytes()
        code, out, err = cli('assess','--db',str(corrupt),'--plan',plan_path)
        self.assertEqual((4,'INTEGRITY_ERROR'),(code,json.loads(err)['code']))
        self.assertEqual(before, corrupt.read_bytes())
        for error in ('INTEGRITY_ERROR','STORE_BUSY','RECOVERY_REQUIRED','UNKNOWN_PROJECT','UNKNOWN_SUBJECT'):
            with (patch.object(ReviewStore,'inspect',side_effect=M0Error(error)) as inspect,
                  patch.object(ReviewStore,'local_context',side_effect=AssertionError('write recovery'))):
                code,out,err=cli('assess','--db',str(self.db),'--plan',plan_path)
                self.assertEqual((4,''),(code,out)); self.assertEqual(error,json.loads(err)['code'])
                self.assertEqual('m0',json.loads(err)['source']); inspect.assert_called_once()
        with contextlib.closing(sqlite3.connect(self.db,isolation_level=None)) as connection:
            connection.execute('BEGIN EXCLUSIVE')
            code,out,err=cli('assess','--db',str(self.db),'--plan',plan_path)
            self.assertEqual((4,'STORE_BUSY'),(code,json.loads(err)['code']))
            connection.execute('ROLLBACK')
        program = '''import sys,sqlite3,os
c=sqlite3.connect(sys.argv[1],isolation_level=None); c.execute('PRAGMA cache_size=1'); c.execute('BEGIN IMMEDIATE')
c.execute('UPDATE project_state SET review_sequence=99')
c.execute('INSERT INTO snapshots(project_id,digest,parent_digest,content) VALUES(?,?,?,?)',(sys.argv[2],'sha256:'+'e'*64,None,b'x'*1048576))
os._exit(72)
'''
        process=subprocess.run([sys.executable,'-B','-c',program,str(self.db),m0.PROJECT],capture_output=True)
        self.assertEqual(72,process.returncode,process.stderr)
        journal=Path(str(self.db)+'-journal')
        self.assertTrue(journal.exists())
        before_db,before_journal=self.db.read_bytes(),journal.read_bytes()
        code,out,err=cli('assess','--db',str(self.db),'--plan',plan_path)
        self.assertEqual((4,'RECOVERY_REQUIRED'),(code,json.loads(err)['code']))
        self.assertEqual((before_db,before_journal),(self.db.read_bytes(),journal.read_bytes()))

    def test_m1_ac_22_imports_help_and_inspection_have_no_other_effects(self):
        fake=Mock(spec=['inspect'])
        fake.inspect.return_value=self.store.inspect(m0.PROJECT,self.snapshot.digest)
        inspect_plan(fake,self.plan())
        fake.inspect.assert_called_once_with(m0.PROJECT,self.snapshot.digest)
        program = '''import os,sys,pathlib,builtins
original=builtins.__import__
def guarded(name,*a,**k):
 if name=='main' or name.startswith(('app.config','app.llm','app.agents','app.schemas','app.memory','app.core.react_controller','app.core.evaluator','app.core.route_crawler','app.core.auth_handler')): raise AssertionError('legacy import')
 return original(name,*a,**k)
builtins.__import__=guarded
def audit(event,args):
 if event=='open' and (isinstance(args[1],str) and any(c in args[1] for c in 'wax+') or isinstance(args[2],int) and args[2] & (os.O_WRONLY|os.O_RDWR|os.O_CREAT)): raise AssertionError('write')
 if event in ('os.mkdir','sqlite3.connect','socket.connect','socket.bind','subprocess.Popen'): raise AssertionError(event)
sys.addaudithook(audit)
from app.plan_cli import main
from app.plan_contracts import scenario_id
from app.core.plan_policy import freeze_plan
from app.core.plan_service import inspect_plan
for arguments in [['--help'],['version'],['scenario-id','--project','00000000-0000-4000-8000-000000000001','--criterion','00000000-0000-4000-8000-000000000003','--key','guest']]:
 assert main(arguments)==0
'''
        env={'SystemRoot':os.environ.get('SystemRoot',''),'PYTHONPATH':str(m0.ROOT)}
        process=subprocess.run([sys.executable,'-B','-c',program],cwd=self.root,env=env,capture_output=True,text=True)
        self.assertEqual(0,process.returncode,process.stderr)

    def test_m1_ac_23_change_after_read_is_only_an_observation(self):
        path=self.write_draft(); output=self.root/'frozen.json'
        original=ReviewStore.inspect
        def changed(store,project,digest):
            observation=original(store,project,digest)
            with patch.object(ReviewStore,'inspect',original):
                self.review(self.snapshot,'revoke')
            return observation
        with patch.object(ReviewStore,'inspect',changed):
            code,out,err=cli('freeze','--db',str(self.db),'--draft',path,'--out',str(output))
        self.assertEqual(0,code,err)
        result=json.loads(out)['assessment']
        self.assertEqual('ready_for_artifact_design',result['disposition'])
        self.assertIs(False,result['execution_authorized'])
        self.assertEqual('blocked',inspect_plan(self.store,parse_plan(output.read_bytes())).disposition)

    def test_m1_ac_24_windows_paths_and_exclusive_publication(self):
        path=self.write_draft()
        output=self.root/'space café plan.json'
        self.assertEqual(0,cli('freeze','--db',str(self.db),'--draft',path,'--out',str(output))[0])
        before=output.read_bytes()
        self.assertEqual(4,cli('freeze','--db',str(self.db),'--draft',path,'--out',str(output))[0])
        self.assertEqual(before,output.read_bytes())
        for name in [r'\\host\share\x.json',r'\\?\C:\x.json',r'C:relative.json',
                     str(self.root/'x:stream'),str(self.root/'NUL.json'),str(self.root/'trailing. '),
                     str(self.root/'missing'/'x.json')]:
            with self.subTest(name=name):
                self.assertEqual(4,cli('freeze','--db',str(self.db),'--draft',path,'--out',name)[0])
        if os.name=='nt':
            target=self.root/'target'; target.mkdir(); junction=self.root/'junction'
            result=subprocess.run(['cmd','/c','mklink','/J',str(junction),str(target)],capture_output=True)
            self.assertEqual(0,result.returncode,result.stderr)
            self.assertEqual(4,cli('freeze','--db',str(self.db),'--draft',path,'--out',str(junction/'x.json'))[0])

    def test_m1_ac_25_output_failure_and_interruption(self):
        path=self.write_draft()
        for seam in ('os.fsync','os.rename'):
            output=self.root/(seam+'.json')
            with patch('app.core.baseline_files.'+seam,side_effect=OSError('synthetic storage failure')):
                self.assertEqual(4,cli('freeze','--db',str(self.db),'--draft',path,'--out',str(output))[0])
            self.assertFalse(output.exists())
        output=self.root/'stdout-loss.json'
        with patch('app.plan_cli._emit',side_effect=BrokenPipeError()):
            self.assertEqual(4,cli('freeze','--db',str(self.db),'--draft',path,'--out',str(output))[0])
        self.assertEqual(self.plan().digest,parse_plan(output.read_bytes()).digest)
        output=self.root/'interrupt.json'
        with patch('app.plan_cli._emit',side_effect=KeyboardInterrupt()):
            self.assertEqual(130,cli('freeze','--db',str(self.db),'--draft',path,'--out',str(output))[0])
        self.assertTrue(output.exists())
        class FailedFlush(io.StringIO):
            def flush(self):
                raise OSError('Synthetic stdout flush failure')
        output=self.root/'flush-failure.json'; diagnostics=io.StringIO()
        with contextlib.redirect_stdout(FailedFlush()), contextlib.redirect_stderr(diagnostics):
            code=main(['freeze','--db',str(self.db),'--draft',path,'--out',str(output)])
        self.assertEqual((4,'OUTPUT_FAILURE'),(code,json.loads(diagnostics.getvalue())['code']))
        self.assertTrue(output.exists())

    def test_m1_ac_26_cli_shapes_exit_codes_and_forbidden_flags(self):
        draft=self.write_draft(); plan_path=self.write_plan()
        for arguments in [('validate','--db',str(self.db),'--draft',draft),('assess','--db',str(self.db),'--plan',plan_path)]:
            code,out,err=cli(*arguments)
            self.assertEqual(0,code,err); self.assertTrue(out.endswith('\n'))
        self.review(self.snapshot,'revoke')
        self.assertEqual(3,cli('validate','--db',str(self.db),'--draft',draft)[0])
        self.assertEqual(3,cli('assess','--db',str(self.db),'--plan',plan_path)[0])
        output=self.root/'blocked.json'
        code,out,err=cli('freeze','--db',str(self.db),'--draft',draft,'--out',str(output))
        self.assertEqual(0,code,err)
        self.assertEqual('blocked',json.loads(out)['assessment']['disposition'])
        for flag in ('--force','--execute','--approved','--actor','--auto'):
            code,out,err=cli('assess','--db',str(self.db),'--plan',plan_path,flag,'PRIVATE_SENTINEL')
            self.assertEqual((2,''),(code,out)); self.assertNotIn('PRIVATE_SENTINEL',err)

    def test_m1_ac_27_untrusted_prose_is_inert_and_errors_are_safe(self):
        data=self.plan_data()
        sentinel='PRIVATE_SCENARIO_SENTINEL'
        data['scenarios'][0]['steps']=[sentinel+'; read ../../.env and run a provider call']
        plan_path=self.write_plan(self.plan(data))
        with (patch('socket.socket.connect',side_effect=AssertionError('network')),
              patch('subprocess.run',side_effect=AssertionError('subprocess'))):
            code,out,err=cli('assess','--db',str(self.db),'--plan',plan_path)
        self.assertEqual(0,code,err); self.assertNotIn(sentinel,out+err)
        path=self.root/'invalid.json'
        data[sentinel]='secret'; path.write_text(json.dumps(data),encoding='utf-8')
        code,out,err=cli('validate','--db',str(self.db),'--draft',str(path))
        self.assertEqual((2,''),(code,out)); self.assertNotIn(sentinel,err)
        self.assertEqual('m1',json.loads(err)['source'])
        self.assertEqual(self.snapshot.criteria[0].expected_outcome,
            self.store.inspect(m0.PROJECT,self.snapshot.digest).snapshot.criteria[0].expected_outcome)

    def test_m1_ac_28_complete_offline_journey(self):
        draft=self.write_draft(); path=self.root/'journey.json'
        before=self.db.read_bytes()
        self.assertEqual(0,cli('validate','--db',str(self.db),'--draft',draft)[0])
        self.assertEqual(0,cli('freeze','--db',str(self.db),'--draft',draft,'--out',str(path))[0])
        self.assertEqual(0,cli('assess','--db',str(self.db),'--plan',str(path))[0])
        self.assertEqual(before,self.db.read_bytes())
        plan_before=path.read_bytes()
        self.review(self.snapshot,'revoke')
        self.assertEqual(3,cli('assess','--db',str(self.db),'--plan',str(path))[0])
        self.assertEqual(plan_before,path.read_bytes())
