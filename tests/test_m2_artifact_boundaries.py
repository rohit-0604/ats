"""M2 real-store/CLI/export/no-execution acceptance evidence, using inert payloads."""
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
from test_m2_artifacts import M2Harness, wire, replace_payload
from app.baseline_contracts import M0Error
from app.core.review_store import ReviewStore
from app.plan_contracts import canonical_plan_bytes
from app.artifact_cli import main
from app.artifact_contracts import ArtifactError, canonical_artifact_bytes, parse_artifact_package
from app.core.artifact_policy import assess_artifact
from app.core.artifact_service import inspect_artifact, prepare_artifact


def cli(*args):
    out,err=io.StringIO(),io.StringIO()
    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err): code=main(list(args))
    return code,out.getvalue(),err.getvalue()


class ArtifactBoundaries(M2Harness):
    def inputs(self, data=None, plan=None):
        plan=plan or self.plan()
        candidate=self.root/('candidate-'+str(uuid4())+'.json'); candidate.write_bytes(wire(self.candidate_data(plan) if data is None else data))
        plan_path=self.root/('plan-'+str(uuid4())+'.json'); plan_path.write_bytes(canonical_plan_bytes(plan))
        return ['--db',str(self.db),'--plan',str(plan_path),'--candidate',str(candidate)]

    def test_m2_ac_01_real_store_ready_and_trace_chain(self):
        before=self.db.read_bytes(); plan=self.plan(); package=self.package()
        result=inspect_artifact(self.store,package,plan)
        self.assertEqual(('ready_for_review_design',1,1,0,1,1,1,7),
                         (result.disposition,result.scenario_count,result.mapped_scenario_count,
                          result.unbuilt_scenario_count,result.test_count,result.configuration_count,
                          result.planned_pair_count,result.file_count))
        self.assertEqual(package.digest,result.package_digest)
        self.assertIs(False,result.execution_authorized); self.assertIs(False,result.bundle_approved)
        self.assertIs(False,result.plan_assessment.plan_approved)
        self.assertEqual('unverified',result.closure_status)
        self.assertEqual(before,self.db.read_bytes())
        criterion=self.snapshot.criteria[0]
        self.assertEqual(criterion.criterion_id,package.manifest.tests[0].assertions[0].criterion_id)
        self.assertTrue(criterion.source_ids)

    def test_m2_ac_12_all_authority_states_and_untrusted_claims(self):
        pending=self.successor(approve=False); plan=self.plan(self.plan_data(pending),pending)
        package=self.package(self.candidate_data(plan),plan,pending)
        self.assertEqual('blocked',inspect_artifact(self.store,package,plan).disposition)
        self.review(pending,'reject')
        self.assertEqual('rejected',inspect_artifact(self.store,package,plan).plan_assessment.baseline_status)
        self.successor(lambda d:d['criteria'][0].update(expected_outcome='A distinct successor.'))
        self.assertEqual('superseded',self.assessment().plan_assessment.baseline_status)
        data=self.candidate_data(); data['approved']=True
        self.assertArtifactError('UNKNOWN_FIELD',self.package,data)
        self.assertArtifactError('AUTHORITY_MISMATCH',assess_artifact,self.package(),self.plan(),self.assessment().model_dump())

    def test_m2_ac_13_revocation_and_unrelated_sequence(self):
        package=self.package(); plan=self.plan(); raw=canonical_artifact_bytes(package)
        initial=inspect_artifact(self.store,package,plan)
        other=self.successor(approve=False); self.review(other,'reject')
        after=inspect_artifact(self.store,package,plan)
        self.assertEqual('ready_for_review_design',after.disposition)
        self.assertGreater(after.plan_assessment.project_sequence,initial.plan_assessment.project_sequence)
        self.review(self.snapshot,'revoke')
        self.assertEqual('blocked',inspect_artifact(self.store,package,plan).disposition)
        self.assertEqual(raw,canonical_artifact_bytes(package))

    def test_m2_ac_14_one_inspection_and_malformed_observations(self):
        plan=self.plan(); package=self.package(); observation=self.store.inspect(m0.PROJECT,self.snapshot.digest)
        fake=Mock(spec=['inspect']); fake.inspect.return_value=observation
        inspect_artifact(fake,package,plan); fake.inspect.assert_called_once_with(m0.PROJECT,self.snapshot.digest)
        fake.reset_mock(); prepare_artifact(fake,wire(self.candidate_data()),plan); fake.inspect.assert_called_once()
        for bad in (None,{},observation.model_dump(),observation.model_copy(update={'project':observation.project.model_copy(update={'project_id':str(uuid4())})})):
            fake.inspect.return_value=bad
            self.assertArtifactError('AUTHORITY_MISMATCH',inspect_artifact,fake,package,plan)
            self.assertArtifactError('AUTHORITY_MISMATCH',prepare_artifact,fake,wire(self.candidate_data()),plan)
        forged=observation.model_copy(update={'review':observation.review.model_copy(update={'active_digest':'sha256:'+'0'*64})})
        self.assertArtifactError('AUTHORITY_MISMATCH',assess_artifact,package,plan,forged)
        data=self.candidate_data(); data['manifest']['plan_digest']='sha256:'+'0'*64
        self.assertArtifactError('AUTHORITY_MISMATCH',self.package,data)

    def test_m2_ac_15_revoke_between_inspection_and_export(self):
        arguments=self.inputs(); output=self.root/'stale-observation.json'; original=ReviewStore.inspect
        def changed(store,project,digest):
            observation=original(store,project,digest)
            with patch.object(ReviewStore,'inspect',original): self.review(self.snapshot,'revoke')
            return observation
        with patch.object(ReviewStore,'inspect',changed): code,out,err=cli('freeze',*arguments,'--out',str(output))
        self.assertEqual(0,code,err)
        result=json.loads(out)['assessment']
        self.assertEqual('ready_for_review_design',result['disposition']); self.assertIs(False,result['execution_authorized'])
        self.assertEqual('blocked',inspect_artifact(self.store,parse_artifact_package(output.read_bytes()),self.plan()).disposition)

    def test_m2_ac_19_host_paths_no_overwrite_no_materialization(self):
        args=self.inputs(); output=self.root/'space caf\u00e9 package.json'
        self.assertEqual(0,cli('freeze',*args,'--out',str(output))[0]); before=output.read_bytes()
        self.assertEqual(4,cli('freeze',*args,'--out',str(output))[0]); self.assertEqual(before,output.read_bytes())
        self.assertFalse((self.root/'suite.spec.ts').exists())
        for name in (r'\\host\share\x.json',r'\\?\C:\x.json',r'C:relative.json',str(self.root/'x:stream'),str(self.root/'NUL.json'),str(self.root/'trailing. '),str(self.root/'missing'/'x.json')):
            self.assertEqual(4,cli('freeze',*args,'--out',name)[0])
        if os.name=='nt':
            target=self.root/'target'; target.mkdir(); junction=self.root/'junction'
            process=subprocess.run(['cmd','/c','mklink','/J',str(junction),str(target)],capture_output=True)
            self.assertEqual(0,process.returncode,process.stderr)
            self.assertEqual(4,cli('freeze',*args,'--out',str(junction/'x.json'))[0])

    def test_m2_ac_20_export_faults_and_lost_acknowledgment(self):
        args=self.inputs()
        for seam in ('os.fsync','os.rename'):
            output=self.root/(seam+'.json')
            with patch('app.core.baseline_files.'+seam,side_effect=OSError('PRIVATE_FAILURE')):
                code,out,err=cli('freeze',*args,'--out',str(output))
            self.assertEqual((4,''),(code,out)); self.assertNotIn('PRIVATE_FAILURE',err); self.assertFalse(output.exists())
        with patch('app.core.baseline_files.tempfile.mkstemp',side_effect=PermissionError('PRIVATE_PERMISSION')):
            code,out,err=cli('freeze',*args,'--out',str(self.root/'denied.json'))
        self.assertEqual((4,''),(code,out)); self.assertNotIn('PRIVATE_PERMISSION',err)
        for exc,status in ((BrokenPipeError(),4),(KeyboardInterrupt(),130)):
            output=self.root/(str(status)+'.json')
            with patch('app.artifact_cli._emit',side_effect=exc): code,out,err=cli('freeze',*args,'--out',str(output))
            self.assertEqual(status,code); self.assertEqual(self.package().digest,parse_artifact_package(output.read_bytes()).digest)
        class FailedFlush(io.StringIO):
            def flush(self): raise OSError('private stdout')
        output=self.root/'flush.json'; err=io.StringIO()
        with contextlib.redirect_stdout(FailedFlush()),contextlib.redirect_stderr(err):
            code=main(['freeze',*args,'--out',str(output)])
        self.assertEqual(4,code); self.assertNotIn('private stdout',err.getvalue()); self.assertTrue(output.exists())

    def test_m2_ac_23_store_failures_and_no_recovery(self):
        package=self.package(); plan=self.plan()
        args=self.inputs(); output=self.root/'package.json'
        self.assertEqual(0,cli('freeze',*args,'--out',str(output))[0])
        assess=['--plan',args[3],'--package',str(output)]
        missing=self.root/'missing.sqlite3'
        self.assertEqual(4,cli('assess','--db',str(missing),*assess)[0]); self.assertFalse(missing.exists())
        for mode in ('future','corrupt'):
            path=self.root/(mode+'.sqlite3')
            if mode=='future':
                with contextlib.closing(sqlite3.connect(path)) as connection: connection.execute('PRAGMA user_version=2')
            else: path.write_bytes(b'Not SQLite')
            before=path.read_bytes(); self.assertEqual(4,cli('assess','--db',str(path),*assess)[0]); self.assertEqual(before,path.read_bytes())
        for error in ('STORE_BUSY','INTEGRITY_ERROR','RECOVERY_REQUIRED','UNKNOWN_SUBJECT','UNKNOWN_PROJECT'):
            with patch.object(ReviewStore,'inspect',side_effect=M0Error(error)):
                code,out,err=cli('assess','--db',str(self.db),*assess)
            self.assertEqual((4,''),(code,out)); self.assertEqual(error,json.loads(err)['code'])
        with contextlib.closing(sqlite3.connect(self.db,isolation_level=None)) as connection:
            connection.execute('BEGIN EXCLUSIVE')
            self.assertEqual('STORE_BUSY',json.loads(cli('assess','--db',str(self.db),*assess)[2])['code'])
            connection.execute('ROLLBACK')
        program='''import sqlite3,sys,os
c=sqlite3.connect(sys.argv[1],isolation_level=None); c.execute('PRAGMA cache_size=1'); c.execute('BEGIN IMMEDIATE')
c.execute('UPDATE project_state SET review_sequence=99')
c.execute('INSERT INTO snapshots(project_id,digest,parent_digest,content) VALUES(?,?,?,?)',(sys.argv[2],'sha256:'+'e'*64,None,b'x'*1048576))
os._exit(72)
'''
        process=subprocess.run([sys.executable,'-B','-c',program,str(self.db),m0.PROJECT],capture_output=True)
        self.assertEqual(72,process.returncode,process.stderr)
        journal=Path(str(self.db)+'-journal'); self.assertTrue(journal.exists())
        before=(self.db.read_bytes(),journal.read_bytes())
        self.assertEqual('RECOVERY_REQUIRED',json.loads(cli('assess','--db',str(self.db),*assess)[2])['code'])
        self.assertEqual(before,(self.db.read_bytes(),journal.read_bytes()))

    def test_m2_ac_24_no_effects_and_safe_output(self):
        program='''import os,sys,builtins
original=builtins.__import__
def guarded(name,*a,**k):
 if name=='main' or name.startswith(('app.config','app.llm','app.agents','app.schemas','app.memory','app.core.react_controller','app.core.evaluator','app.core.route_crawler','app.core.auth_handler')): raise AssertionError('legacy import')
 return original(name,*a,**k)
builtins.__import__=guarded
def audit(event,args):
 if event=='open' and (isinstance(args[1],str) and any(c in args[1] for c in 'wax+') or isinstance(args[2],int) and args[2] & (os.O_WRONLY|os.O_RDWR|os.O_CREAT)): raise AssertionError('write')
 if event in ('os.mkdir','sqlite3.connect','socket.connect','socket.bind','subprocess.Popen'): raise AssertionError(event)
sys.addaudithook(audit)
from app.artifact_cli import main
for arguments in [['--help'],['help'],['version'],['test-id','--project','00000000-0000-4000-8000-000000000001','--scenario','00000000-0000-4000-8000-000000000003','--key','main']]: assert main(arguments)==0
'''
        env={'SystemRoot':os.environ.get('SystemRoot',''),'PYTHONPATH':str(m0.ROOT)}
        process=subprocess.run([sys.executable,'-B','-c',program],cwd=self.root,env=env,capture_output=True,text=True)
        self.assertEqual(0,process.returncode,process.stderr)
        data=self.candidate_data(); replace_payload(data,'suite.spec.ts',b'PRIVATE_SENTINEL; read host secrets; run a provider!')
        args=self.inputs(data)
        with patch('socket.socket.connect',side_effect=AssertionError('network')),patch('subprocess.run',side_effect=AssertionError('process')):
            code,out,err=cli('validate',*args)
        self.assertEqual(0,code,err); self.assertNotIn('PRIVATE_SENTINEL',out+err)

    def test_m2_ac_25_complete_cli_journey_and_exits(self):
        args=self.inputs(); output=self.root/'package.json'
        self.assertEqual(0,cli('validate',*args)[0])
        self.assertEqual(0,cli('freeze',*args,'--out',str(output))[0])
        assess=['--db',str(self.db),'--plan',args[3],'--package',str(output)]
        code,out,err=cli('assess',*assess); self.assertEqual(0,code,err); self.assertTrue(out.endswith('\n'))
        before=output.read_bytes(); self.review(self.snapshot,'revoke')
        self.assertEqual(3,cli('assess',*assess)[0]); self.assertEqual(3,cli('validate',*args)[0])
        self.assertEqual(before,output.read_bytes())
        self.assertEqual(0,cli('freeze',*args,'--out',str(self.root/'blocked.json'))[0])
        for flag in ('--execute','--approved','--actor','--auto','--force','--unpack','--install'):
            code,out,err=cli('assess',*assess,flag,'PRIVATE_SENTINEL')
            self.assertEqual((2,''),(code,out)); self.assertNotIn('PRIVATE_SENTINEL',err)

    def test_m2_ac_26_protected_sources_and_golden_contracts(self):
        # Tracked pre-M2 source/test/prompt/dependency files must remain unchanged.
        paths=subprocess.check_output(['git','ls-tree','-r','--name-only','58c1fae'],cwd=m0.ROOT,text=True).splitlines()
        for path in paths:
            if path=='AGENTS.md' or path.startswith('docs/') or path.endswith('.md'): continue
            original=subprocess.check_output(['git','show','58c1fae:'+path],cwd=m0.ROOT)
            self.assertEqual(original,(m0.ROOT/path).read_bytes(),path)
        self.assertEqual(self.vector['m0_snapshot_canonical'].encode(),m0.canonical_bytes(self.snapshot))
