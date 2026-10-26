#!/usr/bin/env python3
"""Post-hoc aggregation only after all planned completions and preservation pass."""
from pathlib import Path
import json
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_control import HERE, ROOT, FROZEN, CONFIG, LABEL, RESULT_LABEL, read, write, sha, require, now, parquet, unresolved_failures


def gain(candidate, reference):
    require(reference > 0, "Gain denominator must be positive")
    return 100 * (reference - candidate) / reference


def category(old, new):
    if new == 0: return "GAP_REMOVED"
    if old * new < 0: return "GAP_REVERSED"
    if abs(new) < abs(old): return "GAP_REDUCED"
    return "GAP_LARGELY_UNCHANGED"


def original_values(block, resource):
    root = ROOT / FROZEN[block]
    if block == "TimeTrack":
        s2s1 = pd.read_csv(root / "comparisons/s2_vs_s1.csv")
        m1s2 = pd.read_csv(root / "comparisons/m1_vs_s2.csv")
        a = s2s1[s2s1.resource.eq(resource) & s2s1.lead.eq("OVERALL")].iloc[0]
        b = m1s2[m1s2.resource.eq(resource) & m1s2.lead.eq("OVERALL")].iloc[0]
        require(np.isclose(a.macro_mae_candidate,b.macro_mae_baseline, rtol=1e-13), "Frozen shared S2 macro differs")
        return float(a.macro_mae_baseline), float(b.macro_mae_baseline), float(b.macro_mae_candidate), float(b.primary_gain_pct)
    base = root.parent
    primary = pd.read_csv(base / "analysis/primary_macro_mae.csv")
    selected = primary[primary.environment_key.eq(block) & primary.resource.eq(resource) & primary.scope.eq("overall_equal_horizon")]
    values = selected.set_index("formulation").macro_mae
    comparisons = pd.read_csv(base / "comparisons/secondary_aggregation_diagnostics.csv")
    key = "trace" if block.startswith("Materna") else "environment"
    row = comparisons[comparisons[key].eq(block) & comparisons.resource.eq(resource) & comparisons.comparison.eq("M1_vs_S2") & comparisons.scope.eq("overall")].iloc[0]
    return float(values.S1),float(values.S2),float(values.M1),float(row.primary_macro_gain_percent)


def main():
    require(read(HERE / "provenance/preservation_after.json")["status"] == "PASS", "Final preservation verification required")
    cfg=read(CONFIG); rows=[]; all_metrics=[]; totals={"required":0,"reused":0,"new":0,"failed":0}
    failures=unresolved_failures()
    require(not failures, f"Unresolved failures: {failures}")
    for block in cfg["blocks"]:
        plan=read(HERE/f"plans/{block}.json"); metrics=[]
        require(read(HERE/f"validation/{block}.json")["status"] == "PASS", f"Block not passed: {block}")
        require(read(HERE/f"validation/full_audit_{block}.json")["status"] == "PASS", f"Full provenance/numerical audit not passed: {block}")
        completions=list((HERE/f"completions/{block}").glob("*.json"))
        require(len(completions)==plan["required"],f"Completion count {block}")
        for spec in plan["tasks"]:
            item=read(HERE/f"completions/{block}/{spec['control_run_id']}.json")
            require(item["spec"]==spec and item["status"]=="complete",f"Identity mismatch {spec['control_run_id']}")
            require(item["test_evaluations"]==(0 if spec["reuse"] else 1),"Evaluation count")
            for kind in ("model","prediction"):
                require(sha(item[f"{kind}_path"])==item[f"{kind}_sha256"],f"Final {kind} integrity")
            for m in item["metrics"]:
                metrics.append({"label":RESULT_LABEL,"block":block,"resource":spec["resource"],"entity":spec["entity"],"fold":spec["fold"],"seed":spec["seed"],"lead":int(m["lead"]),"mae":float(m["mae"]),"n":int(m["n"]),"forced_L":spec["L"],"epoch":spec["epoch"],"reused":spec["reuse"],"control_run_id":spec["control_run_id"]})
        frame=pd.DataFrame(metrics)
        require(not frame.duplicated(["resource","entity","fold","seed","lead"]).any(),"Duplicate metrics")
        expected=plan["required"]*(8 if block=="TimeTrack" else 5)
        require(len(frame)==expected and np.isfinite(frame.mae).all(),"Metric coverage or finiteness")
        parquet(HERE/f"metrics/{block}.parquet",frame);all_metrics.extend(metrics)
        cells=frame.groupby(["resource","entity","fold","lead"],as_index=False).mae.mean()
        lead_macro=cells.groupby(["resource","lead"],as_index=False).mae.mean()
        macro=lead_macro.groupby("resource").mae.mean()
        for resource in cfg["resources"]:
            s1,s2,m1,old_gain=original_values(block,resource); common=float(macro[resource])
            new_gain=gain(m1,common)
            specs=[s for s in plan["tasks"] if s["resource"]==resource]
            matched=sum(s["original_selected_L"]==s["L"] for s in specs)//3
            rows.append({"label":RESULT_LABEL,"block":block,"resource":resource,"original_S1_MacroMAE":s1,"original_S2_MacroMAE":s2,"S2_common_context_MacroMAE":common,"original_M1_MacroMAE":m1,"original_M1_vs_S2_gain_percent":old_gain,"S2_common_vs_S2_gain_percent":gain(common,s2),"M1_vs_S2_common_gain_percent":new_gain,"S2_common_vs_S1_gain_percent":gain(common,s1),"change_in_M1_gap_percentage_points":new_gain-old_gain,"original_context_matches":matched,"entity_fold_units":len(specs)//3,"category":category(old_gain,new_gain)})
        for key in ("required","reused","new"):totals[key]+=plan[key]
    summary=pd.DataFrame(rows)
    summary.to_csv(HERE/"posthoc_results.csv",index=False)
    parquet(HERE/"posthoc_metric_rows.parquet",pd.DataFrame(all_metrics))
    write(HERE/"completion_summary.json",{"status":"COMPLETE", "label":LABEL,"timestamp":now(),"counts":totals,"metric_rows":len(all_metrics),"block_resource_rows":len(rows),"original_results_overwritten":False})
    lines=["# STAGE 18B1 S2 COMMON-CONTEXT SENSITIVITY REPORT","",LABEL,"","## Status and provenance","","All six blocks completed. This control is post-hoc, not a replacement for frozen S2 or a prospective primary result.","",f"Scientific parent: `{cfg['parent_scientific_checkpoint']}`. Manuscript parent/source commit: `{cfg['parent_manuscript_checkpoint']}`.","",f"Required final units: {totals['required']}; exact frozen reuse: {totals['reused']}; newly trained models: {totals['new']}; failed fits: {totals['failed']}.","","## Full results", "",RESULT_LABEL,"","| Block/resource | S1 MAE | S2 MAE | Common S2 MAE | M1 MAE | Original M1:S2 % | Common:S2 % | M1:Common % | Common:S1 % | Context matched | Category |","|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        keys=["original_S1_MacroMAE","original_S2_MacroMAE","S2_common_context_MacroMAE","original_M1_MacroMAE","original_M1_vs_S2_gain_percent","S2_common_vs_S2_gain_percent","M1_vs_S2_common_gain_percent","S2_common_vs_S1_gain_percent"]
        lines.append("| "+f"{r['block']} / {r['resource']} | "+" | ".join(f"{r[k]:.9g}" for k in keys)+f" | {r['original_context_matches']}/{r['entity_fold_units']} | {r['category']} |")
    lines += ["","Categories are descriptive, not hypothesis tests. No percentage cut-off is introduced. Reversal means the signed comparison changes direction; removal requires zero; reduction means a smaller absolute gap. The provided GAP_LARGELY_UNCHANGED label covers a gap that is not reduced, and any actual widening is stated numerically below rather than hidden by that label.","","## Numerical interpretation for all block/resource cells",""]
    for r in rows:
        old=r["original_M1_vs_S2_gain_percent"];new=r["M1_vs_S2_common_gain_percent"]
        direction="narrows" if abs(new)<abs(old) else "widens" if abs(new)>abs(old) else "is unchanged"
        lines.append(f"- {r['block']} {r['resource']}: {r['category']}; M1 gap {old:.6f}% → {new:.6f}% ({new-old:+.6f} percentage points); absolute gap {direction}. Common-S2 versus original S2: {r['S2_common_vs_S2_gain_percent']:+.6f}%.")
    lines += ["","## Five priority cases",""]
    priority={( "TimeTrack","MEMORY"),("fastStorage","THROUGHPUT"),("Rnd","CPU"),("Materna-T1","DISK_WRITE"),("Materna-T3","DISK_WRITE")}
    for r in rows:
        if (r["block"],r["resource"]) in priority:
            lines.append(f"- {r['block']} {r['resource']}: M1:original-S2 {r['original_M1_vs_S2_gain_percent']:.6f}%; M1:common-S2 {r['M1_vs_S2_common_gain_percent']:.6f}%; common-S2 MAE {r['S2_common_context_MacroMAE']:.9g} versus original-S2 {r['original_S2_MacroMAE']:.9g}; context matches {r['original_context_matches']}/{r['entity_fold_units']}.")
    lines += ["","## Protocol, interpretation and limitations","","Four independent H64/two-layer S2 networks remain per entity/fold/seed. Each forced L comes directly from frozen M1; each epoch comes from existing S2 inner best_epoch at that exact L. Source-specific support/scalers, transforms and horizons are preserved. Exact frozen reuse is reference-based, not copied/retrained. New final refits use one test forward pass only. No inner fit, new selection, bootstrap, global pooled statistic or capacity-matched M1 was run.","","The numerical consequence of restricting S2 context selection is estimated within this implemented pipeline. This does not completely isolate representation sharing, capacity, optimisation geometry or model-count differences. Scaler training-row sets and refit epochs can change as protocol-prescribed consequences of changing L. Three seeds and the original eligible populations remain the scope. Concurrent unrelated workload was observed, so recorded runtime is not a clean hardware-efficiency experiment.","","## Preservation","","Full protected-file SHA-256 inventory and unchanged Git refs were verified after fitting. Manuscript modifications=0; frozen scientific artifact modifications=0; original frozen result modifications=0. New model count is the new-fit count above. Commit=NO; push=NO.","","Detailed fit identities, source paths/hashes, equality checks, support/scaler hashes, new model/prediction hashes and timestamps are in plans/, completions/ and provenance/. Every output belongs to this new post-hoc namespace.","","STAGE_18B1_PASS",""]
    # Preserve the blocked-run report; successor reporting has a separate path.
    (HERE/"STAGE18B1R_S2_COMMON_CONTEXT_REPORT.md").write_text("\n".join(lines))
    inventory=[]
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and p.name not in {"output_sha256_inventory.json","execution.log"}:
            inventory.append({"path":str(p.relative_to(HERE)),"bytes":p.stat().st_size,"sha256":sha(p)})
    write(HERE/"output_sha256_inventory.json",{"label":LABEL,"timestamp":now(),"files":inventory,"exclusions":["self-referential inventory","live execution.log"]})
    print("STAGE_18B1_PASS",flush=True)


if __name__=="__main__":main()
