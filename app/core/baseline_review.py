"""Pure M0 import, validation and approval policy; no runtime imports or I/O."""
from __future__ import annotations
import hashlib
import math
import re
from uuid import UUID, uuid5
from app.baseline_contracts import (
    BaselineDraftV1, BaselineSnapshotV1, ImportResultV1, M0Error,
    ValidationErrorV1, canonical_bytes, digest_content, parse_json, validate_model,
)
def validate_draft(raw_bytes: bytes) -> BaselineDraftV1:
    obj = parse_json(raw_bytes)
    if isinstance(obj, dict) and 'draft' in obj:
        return validate_model(ImportResultV1, obj).draft
    return validate_model(BaselineDraftV1, obj)
def freeze_baseline(validated_draft: BaselineDraftV1) -> BaselineSnapshotV1:
    draft = validate_model(BaselineDraftV1, validated_draft)
    body = parse_json(canonical_bytes(draft))
    return validate_model(BaselineSnapshotV1, {**body, 'digest': digest_content(body)})
def approval_blockers(draft: BaselineDraftV1) -> tuple[ValidationErrorV1, ...]:
    if isinstance(draft, BaselineSnapshotV1):
        draft = draft.model_dump(mode='json', exclude={'digest'})
    draft = validate_model(BaselineDraftV1, draft)
    qualified = {s.evidence_id for s in draft.sources if s.kind in ('document', 'human_decision')}
    blockers = []
    def block(pointer):
        blockers.append(ValidationErrorV1(code='NOT_APPROVABLE', pointer=pointer,
            message='Explicit expectations, support and provenance are required'))
    mapped = {c.requirement_id for c in draft.criteria}
    for i, r in enumerate(draft.requirements):
        if not r.title.strip() or not r.description.strip() or r.requirement_id not in mapped or not set(r.source_ids) & qualified:
            block(f'/requirements/{i}')
    for i, c in enumerate(draft.criteria):
        if c.clarity != 'specified' or c.automation_support == 'unknown' or not set(c.source_ids) & qualified:
            block(f'/criteria/{i}')
    return tuple(blockers)
ROOT_FIELDS = {'requirements','domain_profile','pdf_path','pdf_sha256','run_id','extracted_at','pass_stats'}
REQ_FIELDS = {'req_id','title','description','priority','req_type','feature_area','section_ref','dependencies','gap_analysis','confidence','approved','rejected','human_prompt','source_chunk'}
DOMAIN_STR = {'app_type','auth_type','base_url','inferred_at'}
DOMAIN_LIST = {'feature_areas','likely_routes','framework_hints'}
STATS_INT = {'pass1_count','pass2_enriched','pass3_flagged','pass4_gap_added','pass5_deduped_removed','chunks'}
def _object(value, allowed):
    if not isinstance(value, dict):
        raise M0Error('INVALID_INPUT')
    if set(value) - allowed:
        raise M0Error('UNKNOWN_FIELD')
def _string(value, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str:
        raise M0Error('INVALID_INPUT')
def _strings(value):
    if not isinstance(value, list):
        raise M0Error('INVALID_INPUT')
    for item in value:
        _string(item)
def _integer(value):
    if type(value) is not int or not 0 <= value <= 9007199254740991:
        raise M0Error('INVALID_INPUT')
def import_legacy_bundle(raw_bytes: bytes, project_id: str, source_key: str) -> ImportResultV1:
    obj = parse_json(raw_bytes, limit=4 * 1024 * 1024)
    _object(obj, ROOT_FIELDS)
    try:
        if type(project_id) is not str or str(UUID(project_id)) != project_id:
            raise ValueError()
        if type(source_key) is not str or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,63}', source_key):
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise M0Error('INVALID_INPUT') from None
    reqs = obj.get('requirements')
    if not isinstance(reqs, list) or not reqs:
        raise M0Error('INVALID_INPUT')
    if len(reqs) > 1000:
        raise M0Error('LIMIT_EXCEEDED')
    for key in ('pdf_path','pdf_sha256','extracted_at'):
        if key in obj:
            _string(obj[key], nullable=True)
    if 'run_id' in obj:
        _string(obj['run_id'])
    if obj.get('pdf_sha256') is not None and not re.fullmatch(r'[a-fA-F0-9]{64}', obj['pdf_sha256']):
        raise M0Error('INVALID_INPUT')
    if obj.get('domain_profile') is not None:
        domain = obj['domain_profile']
        _object(domain, DOMAIN_STR | DOMAIN_LIST | {'has_rest_api'})
        for k,v in domain.items():
            if k in DOMAIN_STR:
                _string(v, nullable=k=='inferred_at')
            elif k in DOMAIN_LIST:
                _strings(v)
            elif type(v) is not bool:
                raise M0Error('INVALID_INPUT')
        if 'auth_type' in domain and domain['auth_type'] not in ('none','form_login','bearer_token','api_key'):
            raise M0Error('INVALID_INPUT')
    if 'pass_stats' in obj:
        _object(obj['pass_stats'], STATS_INT | {'total_time_s'})
        for key,v in obj['pass_stats'].items():
            if key in STATS_INT:
                _integer(v)
            elif type(v) not in (int,float) or v < 0 or type(v) is float and not math.isfinite(v):
                raise M0Error('INVALID_INPUT')
    input_digest = 'sha256:' + hashlib.sha256(raw_bytes).hexdigest()
    warnings = []
    def warn(code, pointer):
        warnings.append(dict(code=code, pointer=pointer,
            message=code.replace('_',' ').capitalize()))
    if raw_bytes.startswith(b'\xef\xbb\xbf'):
        warn('BOM_REMOVED','')
    for key in sorted(set(obj) - {'requirements','pdf_sha256'}):
        warn('METADATA_NOT_MIGRATED','/'+key)
    ids = {}
    for r in reqs:
        _object(r, REQ_FIELDS)
        for k in ('req_id','title','description'):
            if k not in r:
                raise M0Error('INVALID_INPUT')
            _string(r[k])
        if not r['req_id'].strip() or len(r['req_id'])>256:
            raise M0Error('INVALID_INPUT')
        if r['req_id'] in ids:
            raise M0Error('DUPLICATE_ID')
        ids[r['req_id']] = str(uuid5(UUID(project_id), canonical_bytes(['legacy-requirement',source_key,r['req_id']]).decode()))
    requirements, criteria, sources = [], [], []
    for i,r in enumerate(reqs):
        for k in ('approved','rejected','gap_analysis'):
            if k in r and type(r[k]) is not bool:
                raise M0Error('INVALID_INPUT')
        for k in ('req_type','priority'):
            if k in r:
                _string(r[k])
        for k in ('feature_area','section_ref','human_prompt'):
            if k in r:
                _string(r[k], nullable=True)
        if 'priority' in r and r['priority'] not in ('high','medium','low'):
            raise M0Error('INVALID_INPUT')
        if r.get('source_chunk') is not None:
            _integer(r['source_chunk'])
        if 'confidence' in r:
            v = r['confidence']
            if type(v) not in (int,float) or not 0<=v<=1 or type(v) is float and not math.isfinite(v):
                raise M0Error('INVALID_INPUT')
        deps = r.get('dependencies',[])
        _strings(deps)
        if any(v not in ids for v in deps):
            raise M0Error('INVALID_REFERENCE')
        pointer = f'/requirements/{i}'
        rid = ids[r['req_id']]
        eid = str(uuid5(UUID(project_id), canonical_bytes(['legacy-evidence',source_key,input_digest,pointer]).decode()))
        legacy = dict(source_key=source_key,original_req_id=r['req_id'],original_title=r['title'],
            original_description=r['description'],approved=r.get('approved'),rejected=r.get('rejected'),
            gap_analysis=r.get('gap_analysis'),section_ref=r.get('section_ref'),source_chunk=r.get('source_chunk'),
            human_prompt=r.get('human_prompt'),claimed_pdf_sha256=obj.get('pdf_sha256'),
            input_digest=input_digest,json_pointer=pointer)
        requirements.append(dict(requirement_id=rid,title=r['title'],description=r['description'],
            source_ids=[eid],dependency_ids=[ids[v] for v in deps],legacy=legacy))
        sources.append(dict(evidence_id=eid,kind='legacy_import',reference=input_digest+'#'+pointer,
            content_digest=input_digest,excerpt=r['description'] if r['description'].strip() else r['title'] if r['title'].strip() else 'Legacy record has no requirement text'))
        criteria.append(dict(criterion_id=str(uuid5(UUID(rid),'legacy-criterion-1')),requirement_id=rid,
            preconditions=[],action=None,expected_outcome=None,origin='inferred' if r.get('gap_analysis') is True else 'legacy_extracted',
            clarity='unresolved',unresolved_reason='Legacy expectation requires explicit review',
            automation_support='unknown',support_reason=None,source_ids=[eid]))
        warn('MISSING_PROVENANCE',pointer)
        warn('CRITERION_REVIEW_REQUIRED',pointer)
        if 'approved' in r or 'rejected' in r:
            warn('LEGACY_APPROVAL_UNTRUSTED',pointer)
        for key in sorted(set(r)&{'priority','req_type','feature_area','confidence'}):
            warn('METADATA_NOT_MIGRATED',pointer+'/'+key)
    return validate_model(ImportResultV1,dict(schema_version=1,input_digest=input_digest,warnings=warnings,
        draft=dict(schema_version=1,project_id=project_id,parent_digest=None,
            requirements=requirements,criteria=criteria,sources=sources)))
