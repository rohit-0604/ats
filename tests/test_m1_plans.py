"""Offline contracts/policy evidence for M1-SPEC-2026-10-25-v2."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest
from uuid import uuid4

import test_m0_acceptance as m0
from app.baseline_contracts import canonical_bytes
from app.core.baseline_review import freeze_baseline, validate_draft
from app.plan_contracts import (
    PlanError, ScenarioPlanDraftV1, ScenarioPlanV1, canonical_plan_bytes,
    parse_plan, parse_plan_draft, scenario_id, validate_plan_model,
)
from app.core.plan_policy import assess_plan, freeze_plan, validate_plan_references
from app.core.plan_service import inspect_plan

FIXTURES = Path(__file__).parent / 'fixtures' / 'plans'


class M1Harness(unittest.TestCase):
    tearDown = m0.Acceptance.tearDown

    def setUp(self):
        m0.Acceptance.setUp(self)
        self.vector = json.loads((FIXTURES / 'golden.json').read_text(encoding='utf-8'))
        self.snapshot = self.put(self.vector['baseline_draft'])
        self.review(self.snapshot)

    def put(self, data):
        snapshot = freeze_baseline(validate_draft(json.dumps(data).encode('utf-8')))
        self.store.store_snapshot(snapshot)
        return snapshot

    def review(self, subject, decision='approve'):
        sequence = self.store.inspect(m0.PROJECT, subject.digest).review.project_sequence
        command = m0.command(subject, decision, sequence)
        return self.store.record_review(command, self.store.local_context(m0.PROJECT))

    def successor(self, edit=None, approve=True):
        active = self.store.inspect(m0.PROJECT, self.snapshot.digest).review.head_digest
        data = self.store.inspect(m0.PROJECT, active).snapshot.model_dump(mode='json')
        data.pop('digest')
        data['parent_digest'] = active
        if edit:
            edit(data)
        else:
            data['criteria'][0]['expected_outcome'] += ' Again.'
        subject = self.put(data)
        if approve:
            self.review(subject)
        return subject

    def plan_data(self, snapshot=None):
        snapshot = snapshot or self.snapshot
        data = copy.deepcopy(self.vector['plan_draft'])
        data['baseline_digest'] = snapshot.digest
        data['scenarios'] = []
        data['dispositions'] = []
        for criterion in snapshot.criteria:
            if criterion.automation_support == 'unsupported':
                state, reason = 'unsupported', criterion.support_reason
            elif criterion.clarity != 'specified' or criterion.automation_support == 'unknown':
                state, reason = 'unplanned', 'Awaiting explicit specification.'
            else:
                state, reason = 'planned', None
                template = copy.deepcopy(self.vector['plan_draft']['scenarios'][0])
                template.update(criterion_id=criterion.criterion_id,
                    scenario_id=scenario_id(snapshot.project_id, criterion.criterion_id, template['scenario_key']))
                data['scenarios'].append(template)
            data['dispositions'].append(dict(criterion_id=criterion.criterion_id, status=state, reason=reason))
        return data

    def draft(self, data=None):
        return parse_plan_draft(json.dumps(self.plan_data() if data is None else data, ensure_ascii=True).encode('utf-8'))

    def plan(self, data=None, snapshot=None):
        return freeze_plan(self.draft(data), snapshot or self.snapshot)

    def assertPlanError(self, code, function, *args, **kwargs):
        with self.assertRaises(PlanError) as caught:
            function(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)
        return caught.exception


class PlanContracts(M1Harness):
    def test_m1_ac_07_multiple_criteria_and_scenarios(self):
        second = str(uuid4())
        subject = self.successor(lambda data: data['criteria'].append(dict(data['criteria'][0], criterion_id=second)))
        data = self.plan_data(subject)
        for scenario in list(data['scenarios']):
            key = 'boundary'
            data['scenarios'].append(dict(scenario, scenario_key=key,
                scenario_id=scenario_id(m0.PROJECT, scenario['criterion_id'], key)))
        plan = self.plan(data, subject)
        self.assertEqual(4, len(plan.scenarios))
        assessment = inspect_plan(self.store, plan)
        self.assertEqual((2, 4), (assessment.planned_criteria, assessment.scenario_count))
        self.assertEqual(1, len({s.title for s in plan.scenarios}))

    def test_m1_ac_08_independent_golden_and_collection_order(self):
        data = copy.deepcopy(self.vector['plan_draft'])
        self.assertEqual(self.snapshot.digest, data['baseline_digest'])
        plan = self.plan(data)
        self.assertEqual(self.vector['canonical'].encode('utf-8'), canonical_plan_bytes(plan))
        self.assertEqual(self.vector['digest'], plan.digest)
        data['scenarios'].reverse()
        data = dict(reversed(list(data.items())))
        self.assertEqual(canonical_plan_bytes(plan), canonical_plan_bytes(self.plan(data)))
        self.assertFalse(canonical_plan_bytes(plan).endswith(b'\n'))
        subject = self.successor(lambda value: value['criteria'].append(
            dict(value['criteria'][0], criterion_id=str(uuid4()))))
        data = self.plan_data(subject)
        ordered = self.plan(data, subject)
        data['scenarios'].reverse(); data['dispositions'].reverse()
        self.assertEqual(canonical_plan_bytes(ordered), canonical_plan_bytes(self.plan(data, subject)))

    def test_m1_ac_09_revision_and_order_sensitivity(self):
        original = self.plan(self.vector['plan_draft'])
        for field, value in [('title', 'Other title'), ('preconditions', ['one', 'two']),
                             ('steps', ['Second', 'First'])]:
            with self.subTest(field=field):
                data = copy.deepcopy(self.vector['plan_draft'])
                data['scenarios'][0][field] = value
                changed = self.plan(data)
                self.assertNotEqual(original.digest, changed.digest)
                self.assertEqual(original.scenarios[0].scenario_id, changed.scenarios[0].scenario_id)
        data = self.plan_data()
        data['scenarios'] = []
        data['dispositions'][0].update(status='unplanned', reason='First reason')
        first = self.plan(data)
        data['dispositions'][0]['reason'] = 'Second reason'
        self.assertNotEqual(first.digest, self.plan(data).digest)
        child = self.successor()
        self.assertNotEqual(self.plan().digest, self.plan(self.plan_data(child), child).digest)
        one = self.draft().scenarios[0]
        self.assertNotEqual(one.scenario_id, scenario_id(m0.PROJECT, one.criterion_id, 'new-business-scenario'))
        for field in ('steps', 'preconditions'):
            data = copy.deepcopy(self.vector['plan_draft'])
            first = self.plan(data)
            data['scenarios'][0][field].reverse()
            self.assertNotEqual(first.digest, self.plan(data).digest)
        data = self.plan_data(); data['scenarios'][0]['title'] = 'caf\u00e9'
        first = self.plan(data)
        data['scenarios'][0]['title'] = 'cafe\u0301'
        self.assertNotEqual(first.digest, self.plan(data).digest)

    def test_m1_ac_10_namespaced_identity_and_forgery(self):
        for vector in self.vector['scenario_vectors']:
            self.assertEqual(vector['id'], scenario_id(vector['project'], vector['criterion'], vector['key']))
        data = self.plan_data()
        data['scenarios'][0]['scenario_id'] = str(uuid4())
        self.assertPlanError('SCENARIO_ID_MISMATCH', self.draft, data)
        data = self.plan_data()
        data['scenarios'][0]['criterion_id'] = str(uuid4())
        self.assertPlanError('SCENARIO_ID_MISMATCH', self.draft, data)

    def test_m1_ac_11_complete_set_and_reference_integrity(self):
        for kind in ('duplicate-scenario', 'duplicate-disposition', 'missing', 'foreign'):
            data = self.plan_data()
            if kind == 'duplicate-scenario':
                data['scenarios'] *= 2
                expected = 'DUPLICATE_ID'
            elif kind == 'duplicate-disposition':
                data['dispositions'] *= 2
                expected = 'DUPLICATE_ID'
            else:
                data['dispositions'][0]['criterion_id'] = str(uuid4())
                expected = 'INVALID_REFERENCE'
            with self.subTest(kind=kind):
                self.assertPlanError(expected, self.plan, data)
        no_criteria = self.snapshot.model_dump(mode='json', exclude={'digest'})
        no_criteria.update(parent_digest=None, criteria=[])
        empty = freeze_baseline(validate_draft(json.dumps(no_criteria).encode()))
        self.assertPlanError('INVALID_REFERENCE', validate_plan_references, self.draft(), empty)
        subject = self.successor(lambda value: value['criteria'].append(
            dict(value['criteria'][0], criterion_id=str(uuid4()))))
        data = self.plan_data(subject); data['dispositions'].pop()
        self.assertPlanError('INVALID_REFERENCE', self.plan, data, subject)
        data = self.plan_data(); foreign = str(uuid4())
        data['scenarios'][0].update(criterion_id=foreign,
            scenario_id=scenario_id(m0.PROJECT, foreign, data['scenarios'][0]['scenario_key']))
        self.assertPlanError('INVALID_REFERENCE', self.plan, data)

    def test_m1_ac_12_unfinished_plan_is_blocked_not_rejected(self):
        data = self.plan_data()
        data['scenarios'] = []
        data['dispositions'][0].update(status='unplanned', reason='Need a negative case.')
        plan = self.plan(data)
        assessment = inspect_plan(self.store, plan)
        self.assertEqual('blocked', assessment.disposition)
        self.assertEqual(1, assessment.unplanned_criteria)
        self.assertEqual({'CRITERION_UNPLANNED', 'NO_AUTOMATABLE_SCENARIOS'}, {v.code for v in assessment.issues})

    def test_m1_ac_13_mixed_unsupported_stays_visible(self):
        def add(data):
            data['criteria'].append(dict(data['criteria'][0], criterion_id=str(uuid4()),
                automation_support='unsupported', support_reason='Requires manual observation.'))
        subject = self.successor(add)
        assessment = inspect_plan(self.store, self.plan(self.plan_data(subject), subject))
        self.assertEqual((2, 1, 1), (assessment.total_criteria, assessment.planned_criteria, assessment.unsupported_criteria))
        self.assertEqual('ready_for_artifact_design', assessment.disposition)
        self.assertNotIn('coverage', assessment.model_dump_json())

    def test_m1_ac_14_all_unsupported_is_not_vacuous_ready(self):
        subject = self.successor(lambda data: data['criteria'][0].update(
            automation_support='unsupported', support_reason='Manual fixture.'))
        assessment = inspect_plan(self.store, self.plan(self.plan_data(subject), subject))
        self.assertEqual('blocked', assessment.disposition)
        self.assertEqual(['NO_AUTOMATABLE_SCENARIOS'], [v.code for v in assessment.issues])
        self.assertEqual(1, assessment.unsupported_criteria)

    def test_m1_ac_15_unresolved_unknown_baseline(self):
        subject = self.successor(lambda data: data['criteria'][0].update(
            clarity='unresolved', unresolved_reason='Need clarification.', automation_support='unknown'), approve=False)
        data = self.plan_data(subject)
        assessment = inspect_plan(self.store, self.plan(data, subject))
        self.assertEqual('pending', assessment.baseline_status)
        self.assertEqual('blocked', assessment.disposition)
        data['dispositions'][0].update(status='planned', reason=None)
        self.assertPlanError('DISPOSITION_CONFLICT', self.plan, data, subject)
        for clarity, support in [('specified','unknown'),('unresolved','supported'),('unresolved','unsupported')]:
            def edit(value):
                value['criteria'][0].update(clarity=clarity, automation_support=support,
                    unresolved_reason='Need clarification.' if clarity=='unresolved' else None,
                    support_reason='Manual only.' if support=='unsupported' else None)
            subject = self.successor(edit, approve=False)
            self.assertEqual('blocked', inspect_plan(self.store, self.plan(self.plan_data(subject),subject)).disposition)

    def test_m1_ac_16_support_cannot_be_overridden(self):
        before = self.db.read_bytes()
        for status, reason in [('unsupported', 'Pretend it is unsupported'), ('planned', 'Not null')]:
            data = self.plan_data()
            data['dispositions'][0].update(status=status, reason=reason)
            self.assertPlanError('DISPOSITION_CONFLICT', self.plan, data)
        subject = self.successor(lambda data: data['criteria'][0].update(
            automation_support='unsupported', support_reason='Manual fixture.'))
        for change in ('reason', 'scenario'):
            data = self.plan_data(subject)
            if change == 'reason':
                data['dispositions'][0]['reason'] = 'Changed classification'
            else:
                data['scenarios'] = self.plan_data()['scenarios']
            self.assertPlanError('DISPOSITION_CONFLICT', self.plan, data, subject)
        self.assertEqual(self.snapshot, self.store.inspect(m0.PROJECT, self.snapshot.digest).snapshot)
        self.assertNotEqual(before, self.db.read_bytes())  # Only explicit test-owned successor/review changed authority.

    def test_m1_ac_17_strict_wire_and_python_boundaries(self):
        for key, value, code in [('schema_version', True, 'INVALID_INPUT'), ('schema_version', 2, 'UNSUPPORTED_VERSION'),
                                 ('project_id', 'bad', 'INVALID_INPUT'), ('baseline_digest', 'latest', 'INVALID_INPUT'),
                                 ('approved', True, 'UNKNOWN_FIELD')]:
            data = self.plan_data(); data[key] = value
            self.assertPlanError(code, self.draft, data)
            self.assertPlanError(code, validate_plan_model, ScenarioPlanDraftV1, data)
        raw = json.dumps(self.plan_data()).encode()
        self.assertPlanError('INVALID_INPUT', parse_plan_draft, raw[:-1] + b',"schema_version":1}')
        self.assertPlanError('INVALID_INPUT', parse_plan_draft, b'{"schema_version":NaN}')

    def test_m1_ac_18_aggregate_and_field_limits(self):
        from app.plan_contracts import MAX_INPUT, bounded_json
        raw = json.dumps(self.plan_data(), ensure_ascii=False).encode('utf-8')
        self.assertEqual(self.draft(), parse_plan_draft(b'\xef\xbb\xbf' + raw))
        self.assertIsNotNone(bounded_json(b'['*32+b'0'+b']'*32))
        self.assertPlanError('LIMIT_EXCEEDED', bounded_json, b'['*33+b'0'+b']'*33)
        self.assertEqual(99999, len(bounded_json(json.dumps([None]*99999).encode())))
        self.assertPlanError('LIMIT_EXCEEDED', bounded_json, json.dumps([None]*100000).encode())
        self.assertEqual({}, bounded_json(b'{}'+b' '*(MAX_INPUT-2)))
        self.assertPlanError('LIMIT_EXCEEDED', bounded_json, b' '*(MAX_INPUT+1))
        for field, good, bad in [('title', 'x'*512, 'x'*513), ('steps', ['x']*64, ['x']*65),
                                  ('preconditions', ['x']*64, ['x']*65)]:
            data=self.plan_data(); data['scenarios'][0][field]=good; self.draft(data)
            data['scenarios'][0][field]=bad
            self.assertPlanError('LIMIT_EXCEEDED', self.draft, data)
        for invalid in ['\x00', '\x1b', '\ud800', '   ']:
            data=self.plan_data(); data['scenarios'][0]['title']=invalid
            self.assertPlanError('INVALID_INPUT', self.draft, data)
        self.assertPlanError('INVALID_INPUT', bounded_json, b'\xff')
        data=self.plan_data(); data['scenarios'][0]['steps']=['x'*16384]*64
        self.draft(data)
        data['scenarios']=[dict(data['scenarios'][0],scenario_key=f'case-{i}',
            scenario_id=scenario_id(m0.PROJECT,m0.CRITERION,f'case-{i}')) for i in range(9)]
        self.assertPlanError('LIMIT_EXCEEDED', validate_plan_model, ScenarioPlanDraftV1, data)
        for field in ('scenarios', 'dispositions'):
            data=self.plan_data(); data[field]=data[field]*5001
            self.assertPlanError('LIMIT_EXCEEDED', validate_plan_model, ScenarioPlanDraftV1, data)
        data=self.plan_data()
        data['scenarios']=[dict(data['scenarios'][0],scenario_key=f'case-{i}',
            scenario_id=scenario_id(m0.PROJECT,m0.CRITERION,f'case-{i}')) for i in range(5000)]
        self.assertEqual(5000,len(validate_plan_model(ScenarioPlanDraftV1,data).scenarios))
        for item in data['scenarios']:
            item['steps']=['x']*64
        self.assertLess(len(json.dumps(data).encode()),MAX_INPUT)
        self.assertPlanError('LIMIT_EXCEEDED',validate_plan_model,ScenarioPlanDraftV1,data)
        data=self.plan_data()
        data['dispositions']=[dict(data['dispositions'][0],criterion_id=str(uuid4())) for _ in range(5000)]
        self.assertEqual(5000,len(validate_plan_model(ScenarioPlanDraftV1,data).dispositions))

    def test_m1_ac_19_nested_immutability_and_copy(self):
        plan = self.plan()
        with self.assertRaises(TypeError):
            plan.scenarios[0].steps[0] = 'overwrite'
        self.assertPlanError('INVALID_INPUT', plan.model_copy, update={'schema_version': True})
        self.assertPlanError('PLAN_DIGEST_MISMATCH', plan.copy, update={'baseline_digest':'sha256:'+'0'*64})
        self.assertEqual(plan, plan.model_copy(deep=True))

    def test_m1_ac_20_tampering_and_noncanonical_input(self):
        plan=self.plan()
        body=plan.model_dump(mode='json')
        body['scenarios'][0]['steps'][0]='Tampered'
        self.assertPlanError('PLAN_DIGEST_MISMATCH', parse_plan, json.dumps(body).encode())
        pretty=json.dumps(plan.model_dump(mode='json'),indent=2).encode()
        self.assertEqual(plan.digest,parse_plan(pretty).digest)
        self.assertEqual(pretty,json.dumps(plan.model_dump(mode='json'),indent=2).encode())

    def test_m1_ac_29_m0_golden_and_contracts_preserved(self):
        import hashlib
        from app.core.review_store import SCHEMA
        self.assertEqual(self.vector['m0_schema_sha256'], hashlib.sha256('\n'.join(SCHEMA).encode()).hexdigest())
        self.assertEqual(self.vector['m0_snapshot_canonical'].encode('utf-8'), canonical_bytes(self.snapshot))
        self.assertEqual(self.snapshot, self.store.inspect(m0.PROJECT,self.snapshot.digest).snapshot)

    def test_m1_ac_30_complete_deterministic_assessment(self):
        def edit(data):
            data['criteria'].append(dict(data['criteria'][0],criterion_id=str(uuid4())))
        subject=self.successor(edit)
        data=self.plan_data(subject)
        data['scenarios']=[]
        for disposition in data['dispositions']:
            disposition.update(status='unplanned',reason='Not planned yet.')
        plan=self.plan(data,subject)
        self.review(subject,'revoke')
        result=inspect_plan(self.store,plan)
        self.assertEqual(4,len(result.issues))
        self.assertEqual(2,result.total_criteria)
        self.assertEqual(result.total_criteria,result.planned_criteria+result.unplanned_criteria+result.unsupported_criteria)
        self.assertEqual(sorted((v.code,v.criterion_id or '',v.scenario_id or '') for v in result.issues),
                         [(v.code,v.criterion_id or '',v.scenario_id or '') for v in result.issues])
        for key in ('passed','coverage_pct','results','success'):
            self.assertNotIn(key,result.model_dump())
        for field in ('plan_approved','execution_authorized'):
            self.assertIs(False,getattr(result,field))
            self.assertPlanError('INVALID_INPUT',result.model_copy,update={field:0})
