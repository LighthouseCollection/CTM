"""Source replay regression; no Django setup, database or network required."""
import hashlib,importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("schema_builder",ROOT/"scripts/build_applicant_schema_audit.py")
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


class SchemaProvenanceTest(unittest.TestCase):
    def test_replay_uses_contract_from_selected_applicant_ref_despite_local_drift(self):
        contract={"version":"selected-contract","tables":[{"name":"applications","domain":"filings","columns":[{"name":"id","type":"uuid","nullable":False,"primary_key":True}]}]}
        inventory={"contract_table_count":1,"implemented_domain_model_count":1,"models":[{"model":"tribunal.Application","table":"legacy","fields":[{"name":"id","column":"id","type":"UUIDField","nullable":False,"primary_key":True}]}]}
        mapping={"batches":[{"id":"filing","title":"Filing","tables":["applications"]}],"mappings":{"applications":{"model":"tribunal.Application"}}}
        pinned=json.dumps(contract,indent=2).encode()+b"\n"
        contract["tables"][0]["columns"].append({"name":"local_drift","type":"text","nullable":True})
        with tempfile.TemporaryDirectory(prefix="ctm-schema-replay-") as directory:
            root=Path(directory);out=root/"docs/implementation/applicant/schema-reconciliation";out.mkdir(parents=True)
            local=root/builder.CONTRACT;local.parent.mkdir(parents=True);local.write_text(json.dumps(contract,indent=2),encoding="utf-8")
            (root/"scripts").mkdir();shutil.copyfile(ROOT/"scripts/audit_applicant_schema.cjs",root/"scripts/audit_applicant_schema.cjs")
            (root/builder.MAPPING).write_text(json.dumps(mapping),encoding="utf-8")
            (out/"findings-input.json").write_text("[]",encoding="utf-8")
            source={builder.CONTRACT:pinned,builder.INVENTORY:json.dumps(inventory,indent=2).encode(),"tribunal/models.py":b"class Application(Root):\n    pass\n"}
            with patch.object(builder,"ROOT",root),patch.object(builder,"OUT",out),patch.object(builder,"git_bytes",side_effect=lambda ref,path:source[path]),patch.object(builder.subprocess,"check_output",side_effect=lambda args,**kwargs:args[-1]+"\n"):
                builder.build("b"*40,"a"*40)
            report=json.loads((out/"result.json").read_text(encoding="utf-8"))
            self.assertEqual(report["counts"]["contract_columns"],1)
            self.assertEqual(report["provenance"]["sha256"][builder.CONTRACT],hashlib.sha256(pinned).hexdigest())
            self.assertEqual([c["name"] for c in report["tables"][0]["columns"]],["id"])
            self.assertIn("local_drift",local.read_text(encoding="utf-8"))


if __name__=="__main__":unittest.main()
