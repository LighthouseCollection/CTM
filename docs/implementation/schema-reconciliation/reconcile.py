"""Read-only schema reconciliation: approved 151-table contract vs Django adapter.

Static analysis only. Reads files from pinned git refs with `git show`; never
imports Django, runs migrations or connects to a database.

Usage (from the repository root):
    python docs/implementation/schema-reconciliation/reconcile.py \
        --backend-ref <sha> [--main-ref <sha>]

Inputs:
  docs/architecture/build-spec/schema.json            (approved contract, at backend ref)
  tribunal/models.py, tribunal/migrations/*            (implementation, at backend ref)
  docs/implementation/schema-reconciliation.json       (backend's candidate map, at backend ref)
  curation.json (next to this script)                  (reviewer judgment per approved table)

Outputs (next to this script): matrix.json, matrix.csv, evidence.json
"""

import argparse
import ast
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = "docs/architecture/build-spec/schema.json"
MODELS = "tribunal/models.py"
MIGRATIONS = "tribunal/migrations"
BACKEND_MAP = "docs/implementation/schema-reconciliation.json"

# Columns supplied by abstract bases / Django mixins.
INHERITED = {
    "Root": [("id", "UUIDField", False, None), ("created_at", "DateTimeField", False, None)],
    "AbstractBaseUser": [("password", "CharField", False, None), ("last_login", "DateTimeField", True, None)],
    "PermissionsMixin": [("is_superuser", "BooleanField", False, None)],
}


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True, encoding="utf-8").stdout


def show(ref, path):
    return git("show", f"{ref}:{path}")


def parse_models(src):
    """Return {ModelName: {table, bases, immutable_orm, fields:{column:{...}}, constraints:[...]}}."""
    tree = ast.parse(src)
    classes = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        bases = [ast.unparse(b).split(".")[-1] for b in node.bases]
        fields, meta = {}, {}
        for item in node.body:
            if isinstance(item, ast.Assign) and isinstance(item.value, ast.Call):
                fn = ast.unparse(item.value.func)
                if not fn.startswith("models.") or len(item.targets) != 1:
                    continue
                name = ast.unparse(item.targets[0])
                ftype = fn.split(".")[-1]
                if ftype in ("Manager",):
                    continue
                kw = {k.arg: ast.unparse(k.value) for k in item.value.keywords if k.arg}
                target = None
                if ftype in ("ForeignKey", "OneToOneField"):
                    target = ast.unparse(item.value.args[0]).strip("'\"") if item.value.args else kw.get("to")
                column = name + "_id" if target else name
                fields[column] = {
                    "field": name,
                    "type": ftype,
                    "nullable": kw.get("null") == "True",
                    "references": target,
                    "unique": kw.get("unique") == "True" or ftype == "OneToOneField",
                    "definition": ast.unparse(item.value),
                    "line": item.lineno,
                }
            if isinstance(item, ast.ClassDef) and item.name == "Meta":
                for m in item.body:
                    if isinstance(m, ast.Assign):
                        meta[ast.unparse(m.targets[0])] = m.value
        classes[node.name] = {"bases": bases, "fields": fields, "meta": meta, "line": node.lineno}

    def resolve(name, seen=()):
        cls = classes.get(name)
        out = {}
        if cls is None:
            for col, t, n, r in INHERITED.get(name, []):
                out[col] = {"field": col, "type": t, "nullable": n, "references": r, "unique": col == "id",
                            "definition": f"inherited from {name}", "line": None}
            return out
        for b in cls["bases"]:
            if b not in seen:
                out.update(resolve(b, seen + (name,)))
        out.update(cls["fields"])
        return out

    def is_abstract(cls):
        m = cls["meta"].get("abstract")
        return m is not None and ast.unparse(m) == "True"

    def immutable(name):
        cls = classes.get(name)
        return bool(cls) and ("Immutable" in cls["bases"] or any(immutable(b) for b in cls["bases"] if b in classes))

    models = {}
    for name, cls in classes.items():
        if name.endswith("Manager") or is_abstract(cls):
            continue
        if not any(b in ("Root", "Immutable", "Model", "AbstractBaseUser") for b in cls["bases"]):
            continue
        table = cls["meta"].get("db_table")
        table = ast.literal_eval(table) if table is not None else "tribunal_" + name.lower()
        constraints = []
        if "constraints" in cls["meta"]:
            for c in cls["meta"]["constraints"].elts:
                constraints.append(ast.unparse(c))
        models[name] = {
            "table": table,
            "line": cls["line"],
            "immutable_orm": immutable(name),
            "fields": resolve(name),
            "constraints": constraints,
        }
    return models


def parse_migrations(ref, models):
    files = [p for p in git("ls-tree", "--name-only", f"{ref}:{MIGRATIONS}").split() if p.endswith((".py", ".sql"))]
    table_to_model = {m["table"]: n for n, m in models.items()}
    forced, triggers, immutable_trigger = {}, {}, {}
    worker = {"SELECT": set(), "INSERT": set(), "UPDATE": set()}
    for f in sorted(files):
        src = show(ref, f"{MIGRATIONS}/{f}")
        if f.endswith(".py"):
            tree = ast.parse(src)
            consts = {}
            for node in tree.body:
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    try:
                        consts[node.targets[0].id] = ast.literal_eval(node.value)
                    except ValueError:
                        pass
            forward = re.sub(r"NO FORCE ROW LEVEL SECURITY", "", src)
            if "FORCE ROW LEVEL SECURITY" in forward:
                names = list(consts.get("MODELS", []))
                names += [table_to_model.get(t, t) for t in re.findall(r"table\s*=\s*[\"'](tribunal_\w+)[\"']", src)]
                for n in names:
                    forced.setdefault(n, f)
            # Loop-installed triggers (f-string table names) need the list they iterate.
            for key in ("IMMUTABLE_MODELS", "ADDITIONAL"):
                if "immutable_update" in src:
                    for n in consts.get(key, []):
                        immutable_trigger.setdefault(n, []).append(f"{f}:immutable_update")
            for names in re.findall(r"if name in \{([^}]*)\}:\s*\n\s*schema_editor\.execute\(f\"CREATE TRIGGER immutable_update", src):
                for n in re.findall(r"\"(\w+)\"", names):
                    immutable_trigger.setdefault(n, []).append(f"{f}:immutable_update")
            if "HISTORY = import_module" in src:
                base = consts.get("IMMUTABLE_MODELS", [])
                history = re.search(r"IMMUTABLE_MODELS \+ (\[[^\]]*\])", src)
                extra = ast.literal_eval(history.group(1)) if history else []
                loop = re.search(r"for name in HISTORY \+ (\[[^\]]*\])", src)
                for n in ast.literal_eval(show(ref, f"{MIGRATIONS}/0002_immutable_history.py").split("IMMUTABLE_MODELS = ", 1)[1].split("]", 1)[0] + "]") + extra + (ast.literal_eval(loop.group(1)) if loop else []):
                    immutable_trigger.setdefault(n, []).append(f"{f}:preserve_history(delete)")
            if f.startswith("0038"):
                for key, priv in (("WORKER_READ", "SELECT"), ("WORKER_INSERT", "INSERT"), ("WORKER_UPDATE", "UPDATE")):
                    worker[priv].update(consts.get(key, []))
        for name, table in re.findall(r"CREATE TRIGGER (\w+) [A-Z ]+? ON (?:public\.)?\"?(tribunal_\w+|[a-z_]+)\"?", src):
            model = table_to_model.get(table)
            if model:
                triggers.setdefault(model, set()).add(f"{f}:{name}")
    return forced, {k: sorted(v) for k, v in triggers.items()}, immutable_trigger, worker


def column_status(approved_col, model_fields, aliases):
    name = approved_col["name"]
    for model, fields in model_fields.items():
        target = aliases.get(name)
        cands = [target] if target else [name]
        for c in cands:
            if c and "." in c:
                m, c2 = c.split(".", 1)
                if m != model:
                    continue
                c = c2
            if c in fields:
                return {"column": name, "match": "alias" if target else "exact", "model": model, "adapter_column": c,
                        "adapter_type": fields[c]["type"], "adapter_definition": fields[c]["definition"]}
    return {"column": name, "match": "none"}


def claim_verdict(text):
    """Classify the reviewer's check of the backend's schema-reconciliation.json row."""
    if re.search(r"WRONG adapter|PARTLY WRONG", text):
        return "wrong_adapter"
    if "INCOMPLETE" in text:
        return "incomplete"
    if "WRONG" in text or "STALE" in text:
        return "false_gap_name_only"
    if "UNVERIFIED" in text:
        return "unverified"
    if "alias" in text or "name-only" in text:
        return "confirmed_with_name_only_noise"
    return "confirmed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-ref", required=True)
    ap.add_argument("--main-ref", default="origin/main")
    args = ap.parse_args()

    schema_src = show(args.backend_ref, SCHEMA)
    main_schema_src = show(args.main_ref, SCHEMA)
    schema = json.loads(schema_src)
    models = parse_models(show(args.backend_ref, MODELS))
    forced, triggers, imm_trig, worker = parse_migrations(args.backend_ref, models)
    backend_map = {t["approved_table"]: t for t in json.loads(show(args.backend_ref, BACKEND_MAP))["tables"]}
    curation = json.loads((HERE / "curation.json").read_text(encoding="utf-8"))
    cur_tables = curation["tables"]

    approved = [t["name"] for t in schema["tables"]]
    missing_cur = sorted(set(approved) - set(cur_tables))
    extra_cur = sorted(set(cur_tables) - set(approved))
    if missing_cur or extra_cur:
        raise SystemExit(f"curation mismatch: missing={missing_cur} extra={extra_cur}")
    unknown_models = sorted({m for t in cur_tables.values() for m in t.get("adapters", [])} - set(models))
    if unknown_models:
        raise SystemExit(f"curation names unknown models: {unknown_models}")

    rows, evidence = [], {}
    for t in schema["tables"]:
        c = cur_tables[t["name"]]
        adapters = c.get("adapters", [])
        mf = {m: models[m]["fields"] for m in adapters}
        cols = [column_status(col, mf, c.get("aliases", {})) for col in t["columns"]]
        missing_cols = [x["column"] for x in cols if x["match"] == "none"]
        perms = []
        for m in adapters:
            perms.append({
                "model": m,
                "table": models[m]["table"],
                "forced_rls_migration": forced.get(m),
                "immutable_orm": models[m]["immutable_orm"],
                "db_triggers": sorted(set(triggers.get(m, []) + imm_trig.get(m, []))),
                "ctm_app_grant": "SELECT,INSERT,UPDATE,DELETE (0038, RLS-gated)",
                "ctm_worker_grant": ",".join(p for p in ("SELECT", "INSERT", "UPDATE") if m in worker[p]) or "none",
            })
        bm = backend_map.get(t["name"], {})
        row = {
            "table": t["name"],
            "domain": t["domain"],
            "retention": t["retention"],
            "status": c["status"],
            "priority": c["priority"],
            "approved_source": f"{SCHEMA}#{t['name']}",
            "adapters": adapters,
            "adapter_paths": [f"{MODELS}:{models[m]['line']} ({models[m]['table']})" for m in adapters],
            "approved_columns": len(t["columns"]),
            "columns_matched_exact": sum(x["match"] == "exact" for x in cols),
            "columns_matched_alias": sum(x["match"] == "alias" for x in cols),
            "columns_missing": missing_cols,
            "approved_constraints": t["constraints"] + t["indexes"],
            "constraint_gaps": c.get("constraint_gaps", []),
            "history_gap": c.get("history_gap", ""),
            "permission_gap": c.get("permission_gap", ""),
            "forced_rls_all_adapters": bool(adapters) and all(p["forced_rls_migration"] for p in perms),
            "gap": c["gap"],
            "backend_inventory_claim": {
                "candidate_adapters": bm.get("candidate_adapters", []),
                "columns_without_same_named_adapter_column": bm.get("columns_without_same_named_adapter_column", []),
            },
            "backend_claim_check": c.get("backend_claim_check", ""),
            "backend_claim_verdict": claim_verdict(c.get("backend_claim_check", "")),
            "evidence_basis": c.get("basis", "verified_in_code"),
        }
        rows.append(row)
        evidence[t["name"]] = {"columns": cols, "permissions": perms}

    out = {
        "contract_version": schema["version"],
        "backend_ref": git("rev-parse", args.backend_ref).strip(),
        "main_ref": git("rev-parse", args.main_ref).strip(),
        "schema_sha256_backend": hashlib.sha256(schema_src.encode()).hexdigest(),
        "schema_identical_on_main": schema_src == main_schema_src,
        "django_models": len(models),
        "forced_rls_models": sorted(forced),
        "models_without_forced_rls": sorted(set(models) - set(forced)),
        "status_counts": {},
        "priority_counts": {},
        "backend_claim_verdict_counts": {},
        "column_match_totals": {
            "approved_columns": sum(r["approved_columns"] for r in rows),
            "exact": sum(r["columns_matched_exact"] for r in rows),
            "alias": sum(r["columns_matched_alias"] for r in rows),
            "missing": sum(len(r["columns_missing"]) for r in rows),
        },
        "tables": rows,
    }
    for r in rows:
        out["status_counts"][r["status"]] = out["status_counts"].get(r["status"], 0) + 1
        out["priority_counts"][r["priority"]] = out["priority_counts"].get(r["priority"], 0) + 1
        v = r["backend_claim_verdict"]
        out["backend_claim_verdict_counts"][v] = out["backend_claim_verdict_counts"].get(v, 0) + 1
    (HERE / "matrix.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (HERE / "evidence.json").write_text(json.dumps(evidence, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    with open(HERE / "matrix.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["table", "domain", "status", "priority", "adapters", "adapter_paths", "approved_columns",
                    "exact", "alias", "missing_columns", "forced_rls_all_adapters", "gap", "constraint_gaps",
                    "history_gap", "permission_gap", "backend_claim_verdict", "backend_claim_check", "evidence_basis"])
        for r in rows:
            w.writerow([r["table"], r["domain"], r["status"], r["priority"], ";".join(r["adapters"]),
                        ";".join(r["adapter_paths"]), r["approved_columns"], r["columns_matched_exact"],
                        r["columns_matched_alias"], ";".join(r["columns_missing"]), r["forced_rls_all_adapters"],
                        r["gap"], " | ".join(r["constraint_gaps"]), r["history_gap"], r["permission_gap"],
                        r["backend_claim_verdict"], r["backend_claim_check"], r["evidence_basis"]])
    print(json.dumps({k: out[k] for k in ("backend_ref", "main_ref", "schema_identical_on_main", "django_models",
                                            "models_without_forced_rls", "status_counts", "priority_counts",
                                            "backend_claim_verdict_counts", "column_match_totals")}, indent=1))


if __name__ == "__main__":
    main()
