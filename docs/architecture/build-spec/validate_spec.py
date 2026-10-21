"""Validate source integrity, schema relationships, SQL syntax when parser available."""
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
    schema=json.loads((ROOT/'schema.json').read_text(encoding='utf-8'))
    names={t['name'] for t in schema['tables']}
    assert len(names)==len(schema['tables'])
    fk_count=0
    for t in schema['tables']:
        cols={c['name'] for c in t['columns']}
        assert len(cols)==len(t['columns']),t['name']
        assert {'id','created_at'}<=cols
        assert len(t['name'])<=63
        for c in t['columns']:
            if c.get('references'):
                assert c['references'] in names,(t['name'],c['name'])
                fk_count+=1
    for forbidden in ['account_credentials','password_reset_tokens','decree_validity_events','replacement_decrees']:
        assert forbidden not in names,forbidden
    sql=(ROOT/'schema.sql').read_text(encoding='utf-8')
    assert sql.count('CREATE TABLE ctm.')==len(names)
    assert sql.count('FOREIGN KEY (')==fk_count
    assert 'ON DELETE CASCADE' not in sql
    assert 'GRANT ALL' not in sql
    assert len(re.findall(r'^CREATE (?:UNIQUE )?INDEX (\w+)',sql,re.M)) == len(set(re.findall(r'^CREATE (?:UNIQUE )?INDEX (\w+)',sql,re.M)))
    parse_status='not_run_parser_unavailable'
    if importlib.util.find_spec('pglast'):
        from pglast import parse_sql
        statements=parse_sql(sql)
        parse_status=f'passed_{len(statements)}_statements'
    register=json.loads((ROOT/'source-register.json').read_text(encoding='utf-8'))
    for item in register['sources']:
        assert hashlib.sha256((ROOT.parent/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
    bank=json.loads((ROOT/'accepted-question-seed.json').read_text(encoding='utf-8'))['questions']
    original=json.loads((ROOT.parent/'reference-study'/'interview-current-question-bank.json').read_text(encoding='utf-8'))
    original_questions=original['fixed']+[q for c in original['categories'] for q in c['questions']]
    assert len(bank)==59==len({q['code'] for q in bank})
    assert {q['code']:q['wording_en'] for q in bank}=={q['id']:q['text'] for q in original_questions}
    assert {q['code'] for q in bank if q['foundational']}=={q['id'] for q in original['fixed']}
    types=json.loads((ROOT/'prototype-decision-types.json').read_text(encoding='utf-8'))['types']
    assert len(types)==10
    broken=[]
    for path in ROOT.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if '://' not in target and not target.startswith('#') and not (path.parent/target.split('#')[0]).exists():
                broken.append((path.name,target))
    assert not broken,broken
    result={'status':'passed_structural_checks','date':'2026-10-21','tables':len(names),'foreign_keys':fk_count,
            'accepted_questions_exactly_preserved':len(bank),'prototype_decision_options_reviewed':len(types),
            'source_hashes_verified':len(register['sources']),'local_markdown_links':'passed','postgresql_parse':parse_status,
            'live_postgresql_execution':'not_run_no_postgres_or_running_docker_engine',
            'runtime_permissions_RLS_lifecycle_tests':'not_run_application_not_built',
            'limitations':['Structural DDL is not a deployed Django migration or complete security implementation.',
                           'RLS, cross-case constraints, lifecycle/immutability triggers and transactional mutation tests must be implemented before production runtime grants.',
                           'Provider, media, Arabic/Plenix and restore integration tests require implementation and deployment inputs.']}
    (ROOT/'validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
