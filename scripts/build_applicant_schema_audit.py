"""Rebuild a source-only applicant reconciliation; never edits schema/migrations."""
import argparse,ast,csv,hashlib,io,json,re,subprocess,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONTRACT="docs/architecture/build-spec/schema.json"
INVENTORY="docs/implementation/model-inventory.json"
MAPPING="docs/implementation/applicant/schema-reconciliation/mapping.json"
OUT=ROOT/"docs/implementation/applicant/schema-reconciliation"


def git_bytes(ref,path):
    return subprocess.check_output(["git","show",f"{ref}:{path}"],cwd=ROOT)


def line_of(text,pattern,start=0):
    lines=text.splitlines()
    for i in range(start,len(lines)):
        if re.search(pattern,lines[i]):return i+1
    raise ValueError(f"Missing source anchor: {pattern}")


def source(path,text,pattern,ref=None,start=0,target=None):
    return {"file":path,"line":line_of(text,pattern,start),"ref":ref,"target":target or pattern}


def build(backend_ref,applicant_ref):
    backend=subprocess.check_output(["git","rev-parse",backend_ref],cwd=ROOT,text=True).strip()
    applicant=subprocess.check_output(["git","rev-parse",applicant_ref],cwd=ROOT,text=True).strip()
    contract_bytes=git_bytes(applicant,CONTRACT)
    contract_text=contract_bytes.decode()
    inventory_text=git_bytes(backend,INVENTORY).decode()
    models_text=git_bytes(backend,"tribunal/models.py").decode()
    inventory=json.loads(inventory_text)
    declared={n.name for n in ast.parse(models_text).body if isinstance(n,ast.ClassDef)}
    assert all(m["model"].split(".")[-1] in declared for m in inventory["models"]),"Inventory model missing from source"
    with tempfile.TemporaryDirectory(prefix="ctm-schema-audit-") as temporary:
        contract=Path(temporary)/"contract.json";contract.write_bytes(contract_bytes)
        inv=Path(temporary)/"inventory.json";inv.write_text(inventory_text,encoding="utf-8")
        output=Path(temporary)/"result.json"
        subprocess.run(["node",str(ROOT/"scripts/audit_applicant_schema.cjs"),str(contract),str(inv),str(ROOT/MAPPING),str(output)],cwd=ROOT,check=True)
        report=json.loads(output.read_text(encoding="utf-8"))
    hashes={CONTRACT:hashlib.sha256(contract_bytes).hexdigest(),INVENTORY:hashlib.sha256(inventory_text.encode()).hexdigest(),
        MAPPING:hashlib.sha256((ROOT/MAPPING).read_bytes()).hexdigest(),"tribunal/models.py":hashlib.sha256(models_text.encode()).hexdigest()}
    report["provenance"]={"date":"2026-10-21","backend_sha":backend,"applicant_sha":applicant,"sha256":hashes,
        "inventory_model_names_checked_against_source":True}
    for table in report["tables"]:
        anchor=line_of(contract_text,r'^      "name": "'+re.escape(table["name"])+r'",')
        table["contract_location"]={"file":CONTRACT,"line":anchor,"target":table["name"]}
        model_anchor=line_of(inventory_text,r'^      "model": "'+re.escape(table["model"])+r'",') if table["model"] else None
        for field in table["columns"]:
            field["contract_location"]=source(CONTRACT,contract_text,r'^          "name": "'+re.escape(field["name"])+r'",',start=anchor,
                target=table["name"]+"."+field["name"])
            if field["backend_column"]:
                field["backend_location"]=source(INVENTORY,inventory_text,r'^          "column": "'+re.escape(field["backend_column"])+r'",',backend,model_anchor,
                    table["model"]+"."+field["backend_column"])
        for candidate in table["storage_candidates"]:
            model_anchor=line_of(inventory_text,r'^      "model": "'+re.escape(candidate["model"])+r'",')
            candidate["location"]=source(INVENTORY,inventory_text,r'^          "column": "'+re.escape(candidate["column"])+r'",',backend,model_anchor,
                candidate["model"]+"."+candidate["column"])
    findings=json.loads((OUT/"findings-input.json").read_text(encoding="utf-8"))
    hashes["docs/implementation/applicant/schema-reconciliation/findings-input.json"]=hashlib.sha256((OUT/"findings-input.json").read_bytes()).hexdigest()
    for finding in findings:
        finding["locations"]=[]
        for target in finding["contract_targets"]:
            table=next(t for t in report["tables"] if t["name"]==target["table"])
            field=next(f for f in table["columns"] if f["name"]==target["column"])
            finding["locations"].append({**field["contract_location"],"ref":applicant})
        for target in finding["implementation_targets"]:
            ref=backend if target["owner"]=="backend" else applicant
            text=git_bytes(ref,target["file"]).decode()
            finding["locations"].append(source(target["file"],text,target["pattern"],ref,target=target["target"]))
    report["findings"]=findings
    report["limits"]=["Named/renamed columns are candidates, never parity or completion percentages.",
        "No standalone model mapping is a domain-inventory observation, not proof a business capability is absent.",
        "Framework authentication/session tables are outside the 63-domain-model inventory.",
        "Storage candidates do not establish normalized typed relations or field-level content coverage.",
        "Defaults, lengths, checks, unique constraints, indexes, RLS, migration execution and live database state are not compared.",
        "Source-reported PostgreSQL results are not independently rerun here; previous local browser evidence retains its recorded scope."]
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    buffer=io.StringIO(newline="");writer=csv.writer(buffer,lineterminator="\n")
    writer.writerow(["batch","contract_table","contract_column","status","backend_model","backend_column","differences","contract_file","contract_line","backend_inventory_line","parity_verified"])
    for table in report["tables"]:
        for field in table["columns"]:
            writer.writerow([table["batch"],table["name"],field["name"],field["status"],field["model"],field["backend_column"],
                ";".join(field["differences"]),CONTRACT,field["contract_location"]["line"],field.get("backend_location",{}).get("line",""),False])
    (OUT/"field-mapping.csv").write_text(buffer.getvalue(),encoding="utf-8")
    for batch in report["batches"]:
        tables=[t for t in report["tables"] if t["batch"]==batch["id"]]
        content=f"# {batch['title']}\n\nSource-only candidates at backend `{backend}` and applicant `{applicant}`.\n"
        content+="No row proves physical schema parity, production readiness or a security failure.\n\n| Contract table | Adapter candidate | Columns without direct mapping | Storage candidate |\n| --- | --- | --- | --- |\n"
        for table in tables:
            missing=[f["name"] for f in table["columns"] if f["status"]=="unmapped_column"]
            stores=", ".join(x["model"]+"."+x["column"] for x in table["storage_candidates"]) or "None mapped"
            content+=f"| `{table['name']}` | `{table['model'] or 'No standalone mapping'}` | {', '.join('`'+n+'`' for n in missing) or 'None; semantics still unverified'} | {stores} |\n"
        content+="\n[All field targets and source locations](field-mapping.csv) · [Full JSON](result.json) · [Findings and limits](README.md)\n"
        (OUT/(batch["id"]+".md")).write_text(content,encoding="utf-8")
    def link(location):
        ref=location.get("ref") or applicant
        label=location["file"]+":"+str(location["line"])
        return f"[{label}](https://github.com/LighthouseCollection/CTM/blob/{ref}/{location['file']}#L{location['line']})"
    counts=report["counts"]
    content=f"# Applicant schema reconciliation: ten batches\n\nSource comparison at backend `{backend}` and applicant `{applicant}`. Approved contract: `{report['contract_version']}`.\n\n"
    content+=f"Reviewed **{counts['in_scope_tables']} contract tables / {counts['contract_columns']} columns** across ten applicant workflows and their shared dependencies. The remaining {len(report['outside_scope'])} contract tables are explicitly listed outside scope in JSON. All {counts['inventory_models']} domain model names were checked against backend source.\n\n"
    content+=f"**{counts['mapped_tables']} tables have explicit adapter model candidates; {counts['no_standalone_model_mapping']} have no standalone model mapping.** Of {counts['contract_columns']} columns, {counts['column_candidate']} have column candidates and {counts['unmapped_column']} have no direct column mapping. {counts['candidate_columns_with_differences']} mapped candidates have type, nullability, primary-key or relation-target differences. These are source reconciliation counts, not missing-feature counts or a completion percentage.\n\n"
    content+="JSON, consolidated roots and framework models may implement behavior without the required physical structure. No column is marked parity verified. The report does not recommend duplicating tables or replacing working services without an owner-reviewed migration plan.\n\n"
    content+="[Download full JSON](result.json) · [Download field CSV](field-mapping.csv) · [Explicit mappings](mapping.json) · [Validation snapshot](validation.json)\n\n"
    content+="| Batch | Workflow | Tables | Columns |\n| --- | --- | --- | --- |\n"
    for index,batch in enumerate(report["batches"],1):
        selected=[t for t in report["tables"] if t["batch"]==batch["id"]]
        content+=f"| {index} | [{batch['title']}]({batch['id']}.md) | {len(selected)} | {sum(len(t['columns']) for t in selected)} |\n"
    content+="\n## Prioritized findings\n\nPriorities describe blockers to full contract/integration acceptance; they are not vulnerability severity ratings. Only AS09 is identified here as a currently blocked frontend integration. Other findings require schema/content reconciliation and preserve the scope of passing behavior tests.\n\n"
    for finding in findings:
        content+=f"### {finding['id']} — {finding['priority']} — {finding['title']}\n\nClassification: `{finding['classification']}`.\n\n{finding['evidence']}\n\nTargets: "+", ".join('`'+x['table']+'.'+x['column']+'`' for x in finding['contract_targets'])+".\n\n"
        content+="Evidence: "+", ".join(link(x) for x in finding["locations"])+".\n\nNext action: "+finding["next_action"]+"\n\n"
    content+="## Clean observations and remaining boundaries\n\nThe prior 68 frontend tests / 54 real API-browser groups remain recorded at applicant `72ee829`. This audit changes no product behavior and does not rerun live services. Existing own privacy, exact response replay, retained checkout and revoked decree-byte tests are not invalidated by structural differences. Seven new reconciliation unit tests and a selected-ref replay regression verify count validation, alias safety, JSON non-parity, FK/nullability/type/PK differences, scope and shared adapters.\n\n"
    content+="Review reproduced a selected-ref replay bug: local schema drift could mix source identities. The generator now reads the contract from the selected applicant Git ref; the failing drift regression passes without changing local contract files.\n\nThe exact shared adapter is surfaced in JSON: CheckoutIntent is proposed for both filing_candidates and payment_attempts; this is an unresolved entity mapping, not two completed contract roots.\n\n"
    content+="The governance council prototype audit at `7586214` covers a different source/page scope; this applicant field-level comparison does not claim to reproduce its 33-page review.\n\n"
    content+="\n".join('- '+limit for limit in report["limits"])+"\n\n## Reproduce\n\n```powershell\nuv run python scripts/build_applicant_schema_audit.py --backend-ref "+backend+" --applicant-ref "+applicant+"\nnode --test tests/frontend/applicant-schema-audit.test.cjs\nuv run python tests/test_applicant_schema_provenance.py\n```\n\nThe generator only writes this report directory. It never applies SQL, edits protected schema/backend sources or deploys. Mapping and findings inputs are reviewable JSON; resolved source hashes are retained in result.json.\n"
    (OUT/"README.md").write_text(content,encoding="utf-8")
    print(json.dumps({"backend_sha":backend,**report["counts"]},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--backend-ref",required=True);parser.add_argument("--applicant-ref",required=True)
    args=parser.parse_args();build(args.backend_ref,args.applicant_ref)
