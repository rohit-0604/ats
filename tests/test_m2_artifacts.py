"""Offline M2 contracts, mappings and independent byte-identity evidence."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4, uuid5
from unittest.mock import patch

import test_m0_acceptance as m0
from test_m1_plans import M1Harness
from app.plan_contracts import scenario_id
from app.artifact_contracts import (
    ArtifactCandidateV1, ArtifactPackageV1, ArtifactManifestV1, ArtifactAssessmentV1,
    ArtifactError, MAX_FILE, MAX_TOTAL, MAX_ENCODED, MAX_INPUT,
    canonical_artifact_bytes, canonical_manifest_bytes, manifest_digest, test_id,
    parse_artifact_candidate, parse_artifact_package, bounded_artifact_json,
)
from app.core.artifact_policy import freeze_artifact_candidate, assess_artifact
from app.core.artifact_service import inspect_artifact, prepare_artifact

FIXTURE = Path(__file__).parent / 'fixtures' / 'artifacts' / 'golden.json'


def wire(data):
    return json.dumps(data, ensure_ascii=True, separators=(',', ':')).encode('utf-8')


def digest(raw):
    return 'sha256:' + hashlib.sha256(raw).hexdigest()


def replace_payload(data, path, raw, role=None):
    files = data['manifest']['files']
    entry = next((v for v in files if v['path'] == path), None)
    if entry is None:
        entry = dict(path=path, role=role or 'data')
        files.append(entry)
    entry.update(size_bytes=len(raw), digest=digest(raw))
    payload = next((v for v in data['payloads'] if v['path'] == path), None)
    if payload is None:
        payload = dict(path=path)
        data['payloads'].append(payload)
    payload['content_base64'] = base64.b64encode(raw).decode('ascii')


def independent_id(project, scenario, key):
    name = json.dumps(['ats-test-v1', project, key], ensure_ascii=False,
                      sort_keys=True, separators=(',', ':'))
    return str(uuid5(UUID(scenario), name))


class M2Harness(M1Harness):
    def setUp(self):
        super().setUp()
        self.av = json.loads(FIXTURE.read_text(encoding='utf-8'))

    def candidate_data(self, plan=None):
        plan = plan or self.plan()
        data = copy.deepcopy(self.av['candidate'])
        manifest = data['manifest']
        manifest.update(project_id=plan.project_id, baseline_digest=plan.baseline_digest,
                        plan_digest=plan.digest, tests=[], scenario_dispositions=[])
        for scenario in plan.scenarios:
            item = copy.deepcopy(self.av['candidate']['manifest']['tests'][0])
            item.update(test_id=independent_id(plan.project_id, scenario.scenario_id, 'main'),
                        scenario_id=scenario.scenario_id)
            item['assertions'][0]['criterion_id'] = scenario.criterion_id
            manifest['tests'].append(item)
            manifest['scenario_dispositions'].append(dict(scenario_id=scenario.scenario_id,
                                                          status='mapped', reason=None))
        return data

    def package(self, data=None, plan=None, snapshot=None):
        plan = plan or self.plan()
        return freeze_artifact_candidate(wire(self.candidate_data(plan) if data is None else data),
                                         plan, snapshot or self.snapshot)

    def assertArtifactError(self, code, fn, *args, **kwargs):
        with self.assertRaises(ArtifactError) as caught:
            fn(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)
        return caught.exception

    def assessment(self, data=None, plan=None, snapshot=None):
        plan = plan or self.plan()
        package = self.package(data, plan, snapshot)
        return inspect_artifact(self.store, package, plan)


class ArtifactContracts(M2Harness):
    def test_m2_ac_02_independent_golden_and_set_order(self):
        plan = self.plan(self.av['plan_draft'])
        package = self.package(self.av['candidate'], plan)
        self.assertEqual(self.av['package'], package.model_dump(mode='json'))
        self.assertEqual(self.av['canonical_package'].encode(), canonical_artifact_bytes(package))
        self.assertEqual(self.av['canonical_manifest'].encode(), canonical_manifest_bytes(package.manifest))
        self.assertEqual(self.av['test_id'], test_id(plan.project_id, plan.scenarios[0].scenario_id, 'main'))
        data = self.candidate_data()
        for field in ('files', 'tests', 'configurations', 'scenario_dispositions'):
            data['manifest'][field].reverse()
        data['payloads'].reverse()
        self.assertEqual(canonical_artifact_bytes(self.package()), canonical_artifact_bytes(self.package(data)))

    def test_m2_ac_03_every_file_role_changes_revision(self):
        original = self.package()
        original_bytes = canonical_artifact_bytes(original)
        for entry in original.manifest.files:
            with self.subTest(role=entry.role):
                data = self.candidate_data()
                raw = base64.b64decode(next(p['content_base64'] for p in data['payloads'] if p['path'] == entry.path))
                replace_payload(data, entry.path, raw + b'x')
                changed = self.package(data)
                self.assertNotEqual(original.digest, changed.digest)
                self.assertEqual(original.manifest.tests[0].test_id, changed.manifest.tests[0].test_id)
        self.assertEqual(original_bytes, canonical_artifact_bytes(original))

    def test_m2_ac_04_raw_bytes_and_noncanonical_base64(self):
        for raw in (b'', b'\x00\xff\x80', b'line\r\n', b'line\n', 'caf\u00e9'.encode()):
            data = self.candidate_data(); replace_payload(data, 'data.bin', raw)
            package = self.package(data)
            value = next(p.content_base64 for p in package.payloads if p.path == 'data.bin')
            self.assertEqual(raw, base64.b64decode(value))
        for value in ('Zg', 'Zh==', 'Zg===', 'Zg==\n', 'Zg==AAAA', '____', '\u00e9===', '=AAA'):
            data = self.candidate_data(); data['payloads'][0]['content_base64'] = value
            self.assertArtifactError('INVALID_BASE64', parse_artifact_candidate, wire(data))

    def test_m2_ac_05_payload_integrity_and_references(self):
        changes = [lambda d: d['payloads'].pop(),
                   lambda d: d['payloads'].append(dict(path='extra', content_base64='')),
                   lambda d: d['manifest']['files'][0].update(size_bytes=999),
                   lambda d: d['manifest']['files'][0].update(digest='sha256:'+'0'*64)]
        for change in changes:
            data = self.candidate_data(); change(data)
            self.assertArtifactError('INTEGRITY_ERROR', parse_artifact_candidate, wire(data))
        for change in (lambda d: d['manifest']['tests'][0].update(spec_path='missing'),
                       lambda d: d['manifest']['configurations'][0].update(config_path='helper.ts'),
                       lambda d: d['manifest']['tests'][0]['assertions'][0].update(path='data.bin')):
            data = self.candidate_data(); change(data)
            self.assertArtifactError('INVALID_REFERENCE', self.package, data)

    def test_m2_ac_06_logical_paths_and_collisions(self):
        for path in ('../x', '/a', 'a\\b', 'C:x', '//host/share', 'CON.txt', 'a/NUL',
                     'com1.js', 'a.', 'a/..', 'a//b', 'a:stream', '.x', 'a b', '\u00e9', 'x'*241):
            data = self.candidate_data(); data['manifest']['files'][0]['path'] = path
            self.assertArtifactError('PATH_POLICY', parse_artifact_candidate, wire(data))
        for path in ('HELPER.ts', 'helper.ts/x'):
            data = self.candidate_data(); replace_payload(data, path, b'x')
            self.assertArtifactError('PATH_POLICY', parse_artifact_candidate, wire(data))

    def test_m2_ac_07_multiple_scenarios_tests_configurations(self):
        pd = self.plan_data(); s = pd['scenarios'][0]
        pd['scenarios'].append(dict(s, scenario_key='other', scenario_id=scenario_id(m0.PROJECT,s['criterion_id'],'other')))
        plan = self.plan(pd); data = self.candidate_data(plan)
        config = dict(data['manifest']['configurations'][0], configuration_key='webkit')
        data['manifest']['configurations'].append(config)
        for t in data['manifest']['tests']:
            t['configuration_keys'].append('webkit')
        t = copy.deepcopy(data['manifest']['tests'][0]); t.update(test_key='boundary',test_id=independent_id(m0.PROJECT,t['scenario_id'],'boundary'))
        t['configuration_keys'] = ['chromium']; data['manifest']['tests'].append(t)
        result = self.assessment(data, plan)
        self.assertEqual((2,3,2,5),(result.scenario_count,result.test_count,result.configuration_count,result.planned_pair_count))

    def test_m2_ac_08_identity_and_duplicate_rejection(self):
        plan = self.plan(); scenario = plan.scenarios[0].scenario_id
        self.assertEqual(independent_id(m0.PROJECT,scenario,'main'),test_id(m0.PROJECT,scenario,'main'))
        for args in ((str(uuid4()),scenario,'main'),(m0.PROJECT,str(uuid4()),'main'),(m0.PROJECT,scenario,'new')):
            self.assertNotEqual(test_id(m0.PROJECT,scenario,'main'),test_id(*args))
        data = self.candidate_data(); data['manifest']['tests'][0]['test_id'] = str(uuid4())
        self.assertArtifactError('TEST_ID_MISMATCH', self.package, data)
        data = self.candidate_data(); data['manifest']['tests'].append(copy.deepcopy(data['manifest']['tests'][0]))
        self.assertArtifactError('DUPLICATE_ID', self.package, data)
        data = self.candidate_data(); t = data['manifest']['tests'][0]; t['scenario_id'] = str(uuid4()); t['test_id'] = independent_id(m0.PROJECT,t['scenario_id'],'main')
        self.assertArtifactError('INVALID_REFERENCE', self.package, data)

    def test_m2_ac_09_configuration_sets(self):
        data = self.candidate_data(); data['manifest']['configurations'].append(dict(data['manifest']['configurations'][0],configuration_key='unused'))
        result = self.assessment(data)
        self.assertEqual('blocked', result.disposition)
        self.assertEqual(['CONFIGURATION_UNUSED'],[i.code for i in result.issues])
        self.assertEqual(1,result.planned_pair_count)
        for keys, code in ((['foreign'],'INVALID_REFERENCE'),(['chromium','chromium'],'DUPLICATE_ID')):
            data = self.candidate_data(); data['manifest']['tests'][0]['configuration_keys'] = keys
            self.assertArtifactError(code,self.package,data)

    def test_m2_ac_10_dispositions_and_assertion_ranges(self):
        for change in (lambda d: d['manifest']['scenario_dispositions'].clear(),
                       lambda d: d['manifest']['scenario_dispositions'][0].update(scenario_id=str(uuid4())),
                       lambda d: d['manifest']['scenario_dispositions'][0].update(status='unbuilt',reason='Later'),
                       lambda d: d['manifest']['tests'][0]['assertions'][0].update(criterion_id=str(uuid4())),
                       lambda d: d['manifest']['tests'][0]['assertions'][0].update(start_byte=10,end_byte=10),
                       lambda d: d['manifest']['tests'][0]['assertions'][0].update(end_byte=9999)):
            data = self.candidate_data(); change(data)
            with self.assertRaises(ArtifactError): self.package(data)
        data = self.candidate_data(); a = data['manifest']['tests'][0]['assertions']; a.append(copy.deepcopy(a[0]))
        self.assertArtifactError('DUPLICATE_ID',self.package,data)
        a[-1]['start_byte'] = 1
        self.package(data)  # Overlapping compound assertions are allowed.

    def test_m2_ac_11_visible_unsupported_unplanned_and_empty(self):
        def mixed(d):
            d['criteria'].append(dict(d['criteria'][0],criterion_id=str(uuid4()),automation_support='unsupported',support_reason='Manual review'))
            d['criteria'].append(dict(d['criteria'][0],criterion_id=str(uuid4())))
        snapshot = self.successor(mixed); pd = self.plan_data(snapshot)
        dropped = pd['scenarios'].pop(); next(d for d in pd['dispositions'] if d['criterion_id']==dropped['criterion_id']).update(status='unplanned',reason='Later')
        plan = self.plan(pd,snapshot); result = self.assessment(self.candidate_data(plan),plan,snapshot)
        self.assertEqual('blocked',result.disposition)
        self.assertEqual((1,1),(result.plan_assessment.unsupported_criteria,result.plan_assessment.unplanned_criteria))
        data = self.candidate_data(); data['manifest']['tests'] = []
        data['manifest']['files'] = [f for f in data['manifest']['files'] if f['role']!='spec']
        data['payloads'] = [p for p in data['payloads'] if p['path']!='suite.spec.ts']
        data['manifest']['scenario_dispositions'][0].update(status='unbuilt',reason='Later')
        result = inspect_artifact(self.store,self.package(data),self.plan())
        self.assertEqual({'PLAN_BLOCKED','SCENARIO_UNBUILT','NO_TESTS','CONFIGURATION_UNUSED'}, {i.code for i in result.issues})
        # PLAN_BLOCKED reflects superseded baseline above, not an invented pass.
        unsupported = self.successor(lambda d:[c.update(automation_support='unsupported',support_reason='Manual') for c in d['criteria']])
        plan = self.plan(self.plan_data(unsupported),unsupported)
        self.assertEqual(0,len(plan.scenarios))
        self.assertArtifactError('LIMIT_EXCEEDED',self.package,self.candidate_data(plan),plan,unsupported)

    def test_m2_ac_16_declarations_never_prove_execution(self):
        data = self.candidate_data(); replace_payload(data,'suite.spec.ts',b'import(process.env.UNTRUSTED); /* no actual test */')
        result = self.assessment(data)
        self.assertEqual('unverified',result.closure_status)
        self.assertIs(False,result.execution_authorized)
        self.assertIs(False,result.bundle_approved)
        self.assertNotIn('syntax_valid',result.model_dump())

    def test_m2_ac_17_strict_models_and_wire(self):
        data = self.candidate_data()
        for raw in (b'[]', b'null', b'{"schema_version":1,"schema_version":1}', b'NaN', b'\xef\xbb\xbf'+wire(data),b'\xff'):
            with self.assertRaises(ArtifactError): parse_artifact_candidate(raw)
        for field,value,code in (('other',True,'UNKNOWN_FIELD'),('schema_version',True,'INVALID_INPUT'),('schema_version',2,'UNSUPPORTED_VERSION')):
            changed = copy.deepcopy(data); changed[field]=value
            self.assertArtifactError(code,parse_artifact_candidate,wire(changed))
        for value in ('\ud800','\u0001'):
            changed=copy.deepcopy(data); changed['manifest']['configurations'][0]['project_name']=value
            self.assertArtifactError('INVALID_INPUT',parse_artifact_candidate,wire(changed))
        package=self.package(); original=canonical_artifact_bytes(package)
        with self.assertRaises(Exception): package.manifest.files[0].path='x'
        self.assertArtifactError('INTEGRITY_ERROR',package.model_copy,update={'digest':'sha256:'+'0'*64})
        result=self.assessment()
        for field in ('bundle_approved','execution_authorized'):
            for value in (True,0,'false'):
                self.assertArtifactError('INVALID_INPUT',result.model_copy,update={field:value})
        self.assertEqual(original,canonical_artifact_bytes(package))

    def test_m2_ac_18_decoder_and_model_bounds(self):
        # Detailed positive/negative size boundaries are separate named regressions below.
        for field,limit,template in (('files',256,self.candidate_data()['manifest']['files'][0]),
                                     ('tests',5000,self.candidate_data()['manifest']['tests'][0]),
                                     ('configurations',64,self.candidate_data()['manifest']['configurations'][0]),
                                     ('scenario_dispositions',5000,self.candidate_data()['manifest']['scenario_dispositions'][0])):
            data=self.candidate_data(); data['manifest'][field]=[template]*(limit+1)
            self.assertArtifactError('LIMIT_EXCEEDED',parse_artifact_candidate,wire(data))
        data=self.candidate_data(); data['manifest']['tests'][0]['assertions']*=65
        self.assertArtifactError('LIMIT_EXCEEDED',parse_artifact_candidate,wire(data))
        data=self.candidate_data(); data['manifest']['tests'][0]['configuration_keys']*=65
        self.assertArtifactError('LIMIT_EXCEEDED',parse_artifact_candidate,wire(data))

    def test_m2_ac_21_tamper_and_noncanonical_input(self):
        package=self.package(); raw=canonical_artifact_bytes(package)
        pretty=json.dumps(package.model_dump(mode='json'),indent=2).encode()
        self.assertEqual(raw,canonical_artifact_bytes(parse_artifact_package(pretty)))
        data=json.loads(raw); data['manifest']['configurations'][0]['project_name']='Changed'
        self.assertArtifactError('INTEGRITY_ERROR',parse_artifact_package,wire(data))
        data=json.loads(raw); data['payloads'][0]['content_base64']='eA=='
        self.assertArtifactError('INTEGRITY_ERROR',parse_artifact_package,wire(data))

    def test_m2_ac_22_oracle_preservation_is_revision_not_semantics(self):
        original=self.package()
        for code in (b'expect(cards).toBeVisible()',b'test.skip()',b'try{expect(0).toBe(4)}catch{}',b'for (const x of []) {expect(x).toBe(4)}'):
            data=self.candidate_data(); replace_payload(data,'suite.spec.ts',code)
            changed=self.package(data)
            self.assertNotEqual(original.digest,changed.digest)
            self.assertEqual(original.manifest.baseline_digest,changed.manifest.baseline_digest)
            self.assertEqual(original.manifest.tests[0].assertions[0].criterion_id,changed.manifest.tests[0].assertions[0].criterion_id)
            self.assertIs(False,inspect_artifact(self.store,changed,self.plan()).execution_authorized)


class DecoderBoundaries(M2Harness):
    def large_data(self, total):
        data=self.candidate_data()
        existing=sum(f['size_bytes'] for f in data['manifest']['files'])
        remaining=total-existing
        for n in range(4):
            size=min(MAX_FILE,remaining); replace_payload(data,'large'+str(n),b'x'*size)
            remaining-=size
        self.assertEqual(0,remaining)
        return data

    def test_decoder_file_minus_exact_plus(self):
        for size in (12288,12289,MAX_FILE-1,MAX_FILE):
            data=self.candidate_data(); replace_payload(data,'data.bin',b'x'*size)
            self.package(data)
        data=self.candidate_data(); replace_payload(data,'data.bin',b'x'*(MAX_FILE+1))
        self.assertArtifactError('LIMIT_EXCEEDED',parse_artifact_candidate,wire(data))

    def test_decoder_encoded_precheck_and_same_length_decoded_overflow(self):
        for value in ('A'*(MAX_ENCODED+1),base64.b64encode(b'x'*(MAX_FILE+1)).decode()):
            data=self.candidate_data(); data['payloads'][0]['content_base64']=value
            with patch('app.artifact_contracts.base64.b64decode',side_effect=AssertionError('must precheck')):
                self.assertArtifactError('LIMIT_EXCEEDED',parse_artifact_candidate,wire(data))

    def test_decoder_aggregate_minus_exact_plus(self):
        for total in (MAX_TOTAL-1,MAX_TOTAL): self.package(self.large_data(total))
        with patch('app.artifact_contracts.base64.b64decode',side_effect=AssertionError('aggregate precheck')):
            self.assertArtifactError('LIMIT_EXCEEDED',parse_artifact_candidate,wire(self.large_data(MAX_TOTAL+1)))

    def test_decoder_wire_and_canonical_limits(self):
        raw=wire(self.candidate_data())
        bounded_artifact_json(raw+b' '*(MAX_INPUT-len(raw)))
        with patch('app.artifact_contracts.json.loads',side_effect=AssertionError('preparse')):
            self.assertArtifactError('LIMIT_EXCEEDED',bounded_artifact_json,raw+b' '*(MAX_INPUT+1-len(raw)))
        data=self.candidate_data(); replace_payload(data,'data.bin',b'x'*MAX_FILE)
        # Direct Python input is subject to canonical byte cap too.
        for n in range(256-len(data['manifest']['files'])):
            replace_payload(data,'data'+str(n),b'')
        self.package(data)
        data['payloads'].append(dict(path='excess',content_base64=''))
        self.assertArtifactError('LIMIT_EXCEEDED',ArtifactCandidateV1.model_validate,data)

    def test_decoder_context_and_ordinary_strings(self):
        data=self.candidate_data(); data['manifest']['scenario_dispositions'][0]['reason']='r'*16384
        # Parser permits ordinary bound; mapping policy separately rejects mapped reason.
        bounded_artifact_json(wire(data))
        data['manifest']['scenario_dispositions'][0]['reason']+='r'
        self.assertArtifactError('LIMIT_EXCEEDED',bounded_artifact_json,wire(data))
        for data in ({'content_base64':'A'*16385}, {'payloads':[{'path':'a','content_base64':'A'*16385,'extra':1}]},
                     {'schema_version':1,'manifest':{},'payloads':[],'other':{'content_base64':'A'*16385}}):
            with self.assertRaises(ArtifactError): bounded_artifact_json(wire(data))
        self.assertArtifactError('LIMIT_EXCEEDED',bounded_artifact_json,wire({'x'*16385:1}))
        bounded_artifact_json(wire({'x'*16384:1}))
        data=self.candidate_data(); data['payloads'][0]['path']='x'*16385
        self.assertArtifactError('LIMIT_EXCEEDED',bounded_artifact_json,wire(data))
        data=self.candidate_data(); data['manifest']['files'][0]['digest']='sha256:'+'0'*65
        self.assertArtifactError('INVALID_INPUT',parse_artifact_candidate,wire(data))

    def test_decoder_depth_node_unicode_and_nonfinite(self):
        # Decoder structure limits are independent of schema validation.
        bounded_artifact_json(b'{"x":'+b'['*31+b'0'+b']'*31+b'}')
        self.assertArtifactError('LIMIT_EXCEEDED',bounded_artifact_json,b'{"x":'+b'['*32+b'0'+b']'*32+b'}')
        bounded_artifact_json(wire({'x':[0]*99998}))
        self.assertArtifactError('LIMIT_EXCEEDED',bounded_artifact_json,wire({'x':[0]*99999}))
        for raw in (b'{"x":Infinity}',b'{"x":1e999}',b'{"x":"\\ud800"}',b'{"\\ud800":0}',b'{"x":1,"x":2}'):
            self.assertArtifactError('INVALID_INPUT',bounded_artifact_json,raw)

    def test_positive_collection_limits_and_independent_node_ceiling(self):
        data=self.candidate_data(); template=data['manifest']['tests'][0]
        data['manifest']['tests']=[]
        for n in range(5000):
            t=copy.deepcopy(template); t.update(test_key='key'+str(n),test_id=independent_id(m0.PROJECT,t['scenario_id'],'key'+str(n)))
            data['manifest']['tests'].append(t)
        candidate=parse_artifact_candidate(wire(data))
        self.assertEqual(5000,len(candidate.manifest.tests))
        data=self.candidate_data(); template=data['manifest']['scenario_dispositions'][0]
        data['manifest']['scenario_dispositions']=[dict(template,scenario_id=str(UUID(int=n+1)),status='unbuilt',reason='Later') for n in range(5000)]
        self.assertEqual(5000,len(parse_artifact_candidate(wire(data)).manifest.scenario_dispositions))
        data=self.candidate_data(); config=data['manifest']['configurations'][0]
        data['manifest']['configurations']=[dict(config,configuration_key='c'+str(n)) for n in range(64)]
        t=data['manifest']['tests'][0]; t['configuration_keys']=['c'+str(n) for n in range(64)]
        t['assertions']=[dict(t['assertions'][0],end_byte=n+1) for n in range(64)]
        replace_payload(data,'suite.spec.ts',b'x'*64)
        package=self.package(data); self.assertEqual(64,len(package.manifest.tests[0].assertions))
        result=inspect_artifact(self.store,package,self.plan())
        self.assertEqual((64,64),(result.configuration_count,result.planned_pair_count))
        # Simultaneous maxima can exceed the independent aggregate node bound.
        data['manifest']['tests']=[dict(t,test_key='key'+str(n),test_id=independent_id(m0.PROJECT,t['scenario_id'],'key'+str(n))) for n in range(5000)]
        self.assertArtifactError('LIMIT_EXCEEDED',ArtifactCandidateV1.model_validate,data)

    def test_canonical_package_exact_limit_and_direct_python_overflow(self):
        # Independent byte sizing avoids relying on the implementation to set its boundary.
        data=self.large_data(MAX_TOTAL)
        dispositions=data['manifest']['scenario_dispositions']
        n=1
        while len(wire(data)) < MAX_INPUT-16384:
            dispositions.append(dict(scenario_id=str(UUID(int=n)),status='unbuilt',reason='r'*16384)); n+=1
        dispositions.append(dict(scenario_id=str(UUID(int=n)),status='unbuilt',reason='r'))
        last=dispositions[-1]
        # Input fixture is ASCII; sorted-key canonical JSON has the same byte length as wire().
        last['reason']='r'*(MAX_INPUT-len(wire(data))+1)
        self.assertEqual(MAX_INPUT,len(wire(data)))
        candidate=ArtifactCandidateV1.model_validate(data)
        self.assertEqual(MAX_INPUT,len(canonical_artifact_bytes(candidate)))
        package_data=dict(data,digest=manifest_digest(candidate.manifest))
        self.assertArtifactError('LIMIT_EXCEEDED',ArtifactPackageV1.model_validate,package_data)
        overhead=len(wire(package_data))-len(wire(data))
        last['reason']=last['reason'][:-overhead]
        package_data=dict(data,digest=manifest_digest(ArtifactManifestV1.model_validate(data['manifest'])))
        package=ArtifactPackageV1.model_validate(package_data)
        self.assertEqual(MAX_INPUT,len(canonical_artifact_bytes(package)))
        last['reason']+='r'
        package_data=dict(data,digest=manifest_digest(ArtifactManifestV1.model_validate(data['manifest'])))
        self.assertArtifactError('LIMIT_EXCEEDED',ArtifactPackageV1.model_validate,package_data)
        last['reason']+='r'*(overhead-1)
        last['reason']+='r'
        self.assertArtifactError('LIMIT_EXCEEDED',ArtifactCandidateV1.model_validate,data)

    def test_python_and_wire_specialization_cannot_be_spoofed(self):
        for transform in (lambda d:d.update(extra='x'),
                          lambda d:d['payloads'][0].update(extra='x'),
                          lambda d:d['manifest'].update(content_base64='A'*20000)):
            data=self.candidate_data(); replace_payload(data,'data.bin',b'x'*20000); transform(data)
            with self.assertRaises(ArtifactError): parse_artifact_candidate(wire(data))
            with self.assertRaises(ArtifactError): ArtifactCandidateV1.model_validate(data)
        for value in ('A'*MAX_ENCODED, 'AA=A', 'A===', 'AB==', 'AAB='):
            data=self.candidate_data(); data['payloads'][0]['content_base64']=value
            with self.assertRaises(ArtifactError): parse_artifact_candidate(wire(data))
        data=self.candidate_data(); data['manifest']['files'][0]['size_bytes']=True
        self.assertArtifactError('INVALID_INPUT',ArtifactCandidateV1.model_validate,data)

    def test_canonical_order_for_nested_sets_and_all_manifest_metadata(self):
        data=self.candidate_data(); t=data['manifest']['tests'][0]
        data['manifest']['configurations'].append(dict(data['manifest']['configurations'][0],configuration_key='other'))
        t['configuration_keys'].append('other'); t['assertions'].append(dict(t['assertions'][0],start_byte=1))
        original=self.package(data); t['assertions'].reverse(); t['configuration_keys'].reverse(); data['manifest']['configurations'].reverse()
        self.assertEqual(canonical_artifact_bytes(original),canonical_artifact_bytes(self.package(data)))
        data['manifest']['configurations'][0]['project_name']='A distinct label'
        self.assertNotEqual(original.digest,self.package(data).digest)
        result=self.assessment()
        self.assertArtifactError('INVALID_INPUT',result.model_copy,update={'test_count':0,'planned_pair_count':0})

    def test_maximum_file_count_and_path_length(self):
        data=self.candidate_data()
        path='x'*240; replace_payload(data,path,b'')
        for n in range(256-len(data['manifest']['files'])): replace_payload(data,'empty'+str(n),b'')
        package=self.package(data)
        self.assertEqual(256,len(package.manifest.files))
        replace_payload(data,'one-more',b'')
        self.assertArtifactError('LIMIT_EXCEEDED',parse_artifact_candidate,wire(data))

    def test_raw_decoded_overflow_and_noncanonical_unused_bits(self):
        # Rechecking actual decoded length remains independent of a projected-size check.
        from app.artifact_contracts import decode_payload
        with patch('app.artifact_contracts.base64.b64decode',return_value=b'x'*(MAX_FILE+1)):
            self.assertArtifactError('LIMIT_EXCEEDED',decode_payload,'eA==')
        with patch('app.artifact_contracts.base64.b64decode',return_value=b'xx'):
            self.assertArtifactError('INVALID_BASE64',decode_payload,'eA==')
        for value in ('AB==','AAB='):
            self.assertArtifactError('INVALID_BASE64',decode_payload,value)
