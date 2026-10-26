"""Seal the expressly authorised 35-unit same-identity recovery, without fits."""
import ast
import difflib
from pathlib import Path
import run_linear_control as r

def main():
    r.verify_refs()
    r.require(not (r.HERE/"recovery/successor.json").exists(),"Successor already sealed")
    r.require(r.read(r.HERE/"recovery/tests.json")["status"]=="PASS","Regression tests required")
    manifest=r.read(r.HERE/"recovery/predecessor_snapshot.json"); snapshot=Path(manifest["snapshot_path"])
    old=r.read(r.HERE/"provenance/experiment.json")
    r.require(r.sha(r.CONFIG)==old["configuration_sha256"],"Scientific config changed")
    permitted={str((r.HERE/n).relative_to(r.ROOT)) for n in ("run_linear_control.py","analyse_linear_control.py")}
    for rel,h in old["source_hashes"].items():
        if rel not in permitted: r.require(r.sha(r.ROOT/rel)==h,f"Unapproved source change {rel}")
    for b,h in old["plan_hashes"].items(): r.require(r.sha(r.HERE/f"plans/{b}.json")==h,"Plan changed")
    r.verify_predecessor()
    failures=list((r.HERE/"failures").rglob("*.json")); r.require(len(failures)==35,"Expected exactly35 failed identities")
    units={}
    specs=r.read(r.HERE/"plans/TimeTrack.json")["groups"]
    for p in failures:
        value=r.read(p); identity=value["identity"]
        r.require(identity["phase"]=="final" and identity["block"]=="TimeTrack" and identity["resource"]=="CPU" and identity["formulation"]=="AR","Failure outside approved scope")
        r.require(value["error"]=="Conflict('PROVENANCE_CONFLICT: Frozen persistence MAE differs')","Different failure")
        spec=next(s for s in specs if s["group_id"]==identity["group_id"])
        selected=r.read(r.selection_path(spec,"AR","CPU"))
        exact=r.ident(spec,"final","AR","CPU",selected["alpha"],r.sha(r.selection_path(spec,"AR","CPU")))
        r.require(exact==identity,"Selected identity changed")
        r.require(not r.completion_path(identity).exists(),"Failed identity already completed")
        # No complete or partial final artifacts were written before the guard.
        mp=r.HERE/f"models/TimeTrack/{p.stem}.npz"; pp=r.HERE/f"predictions/TimeTrack/{p.stem}.parquet"
        r.require(not mp.exists() and not pp.exists(),"Unexpected reusable artifact: must verify before inference")
        units[p.stem]={"identity":identity,"failure_path":str(p),"failure_sha256":r.sha(p),"attempt_sha256":r.sha(r.HERE/f"attempts/final/TimeTrack/{p.name}"),"reusable_artifacts":False,"authorised_recovery_final_fits":1,"authorised_recovery_test_evaluations":1}
    inner=list((r.HERE/"completions/inner").rglob("*.json")); r.require(len(inner)==1400,"Inner coverage changed")
    for p in inner:
        value=r.read(p); r.validate_completion(value["identity"],value)
    r.write(r.HERE/"recovery/authorisation.json", {"stage":"18B3R","user_authorised":"one same-identity final fit/inference/test evaluation for each of the35 failed finals if no complete verified artifacts; reuse all1400 valid inner completions; no scientific config changes","units":units,"failed_units":35,"artifact_reuse":0,"authorised_reruns":35,"valid_inner_reused":1400,"scientific_configuration_sha256":r.sha(r.CONFIG),"timestamp":r.now()})
    diffs=[]
    for name in ("run_linear_control.py","analyse_linear_control.py"):
        diffs.extend(difflib.unified_diff((snapshot/name).read_text().splitlines(True),(r.HERE/name).read_text().splitlines(True),fromfile="predecessor/"+name,tofile="successor/"+name))
    r.output(r.HERE/"recovery/exact_adapter_diff.patch").write_text("".join(diffs))
    successor={"stage":"18B3R","label":r.LABEL,"configuration_sha256":r.sha(r.CONFIG),"scientific_config_changes":0,"predecessor_seal_sha256":r.sha(r.HERE/"provenance/experiment.json"),"predecessor_runner_sha256":r.sha(snapshot/"run_linear_control.py"),"successor_runner_sha256":r.sha(r.HERE/"run_linear_control.py"),"source_hashes":r.source_hashes(),"plan_hashes":old["plan_hashes"],"authorisation_sha256":r.sha(r.HERE/"recovery/authorisation.json"),"snapshot_manifest_sha256":r.sha(r.HERE/"recovery/predecessor_snapshot.json"),"exact_diff_sha256":r.sha(r.HERE/"recovery/exact_adapter_diff.patch"),"tests_sha256":r.sha(r.HERE/"recovery/tests.json"),"timestamp":r.now()}
    r.write(r.HERE/"recovery/successor.json",successor)
    r.verify_seal()
    print("RECOVERY_SEALED",successor["predecessor_runner_sha256"],successor["successor_runner_sha256"],flush=True)

if __name__=="__main__": main()
