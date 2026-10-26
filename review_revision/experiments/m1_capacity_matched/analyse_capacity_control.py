#!/usr/bin/env python3
"""Authorised comparisons, after complete independent audits; no new endpoints."""
from pathlib import Path
import sys
import pandas as pd
import numpy as np
from run_capacity_control import HERE, ROOT, PRIOR, CONFIG, LABEL, RESULT_LABEL, read, write, require, sha, now, parquet, verify_seal, verify_refs
sys.path.insert(0,str(PRIOR))
from analyse_control import original_values


def gain(candidate,reference):
    require(np.isfinite(candidate) and np.isfinite(reference) and reference > 0,"Invalid gain inputs","PRIMARY_NONFINITE_RESULT_CONFLICT")
    return 100*(reference-candidate)/reference


def gap_description(old,new):
    if old == new: return "GAP_UNCHANGED"
    if new == 0: return "GAP_REMOVED"
    if old*new < 0: return "GAP_REVERSED"
    if abs(new) < abs(old): return "GAP_REDUCED"
    return "GAP_WIDENED"


def inventory():
    rows = []
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and p.name not in {"output_sha256_inventory.json","execution.log","runtime.lock"}:
            rows.append({"path":str(p.relative_to(HERE)),"bytes":p.stat().st_size,"sha256":sha(p)})
    write(HERE/"output_sha256_inventory.json",{"label":LABEL,"timestamp":now(),"files":rows,"exclusions":["self-referential inventory","live execution.log","runtime.lock"]})


def main():
    verify_refs(); verify_seal()
    require(read(HERE/"provenance/preservation_after.json")["status"] == "PASS","Full preservation audit required")
    require(not list((HERE/"failures").rglob("*.json")),"Failed units remain")
    common = pd.read_csv(PRIOR/"posthoc_results.csv")
    rows=[]; all_metrics=[]; counts={"inner":0,"final":0,"failed":0}
    for block in read(CONFIG)["blocks"]:
        audit=read(HERE/f"validation/full_audit_{block}.json")
        require(audit["status"] == "PASS" and audit["duplicates"] == 0,"Block audit required")
        counts["inner"]+=audit["inner"]; counts["final"]+=audit["final"]
        metrics=[]
        for path in sorted((HERE/f"completions/final/{block}").glob("*.json")):
            value=read(path); ident=value["identity"]
            for m in value["metrics"]:
                metrics.append({"label":RESULT_LABEL,"block":block,"entity":ident["entity"],"fold":ident["fold"],"seed":ident["seed"],"L":ident["L"],"epoch":ident["epoch"],"run_id":ident["run_id"],**m})
        frame=pd.DataFrame(metrics)
        require(not frame.duplicated(["entity","fold","seed","resource","lead"]).any(),"Duplicate metric identity")
        require(len(frame)==audit["metric_rows"] and np.isfinite(frame.mae).all(),"Metric coverage/finiteness")
        # Frozen aggregation: equal seeds, equal entity/fold cells, equal horizons.
        cells=frame.groupby(["resource","entity","fold","lead"],as_index=False).mae.mean()
        lead=cells.groupby(["resource","lead"],as_index=False).mae.mean()
        macro=lead.groupby("resource").mae.mean()
        parquet(HERE/f"metrics/{block}.parquet",frame); all_metrics.extend(metrics)
        for r in read(CONFIG)["resources"]:
            _,s2,h64,oldgain=original_values(block,r)
            c=common[common.block.eq(block)&common.resource.eq(r)]
            require(len(c)==1,"Common-S2 reference missing/ambiguous")
            c=c.iloc[0]
            require(np.isclose(c.original_S2_MacroMAE,s2,rtol=1e-13) and np.isclose(c.original_M1_MacroMAE,h64,rtol=1e-13),"Frozen reference discrepancy")
            h129=float(macro[r]); g=gain(h129,s2)
            rows.append({"label":RESULT_LABEL,"block":block,"resource":r,"S2_MacroMAE":s2,"common_S2_MacroMAE":float(c.S2_common_context_MacroMAE),"M1_H64_MacroMAE":h64,"M1_H129_MacroMAE":h129,"original_H64_vs_S2_gain_percent":oldgain,"H129_vs_S2_gain_percent":g,"H129_vs_H64_gain_percent":gain(h129,h64),"H129_vs_common_S2_gain_percent":gain(h129,float(c.S2_common_context_MacroMAE)),"gap_description":gap_description(oldgain,g)})
    require(counts=={"inner":8190,"final":2730,"failed":0} and len(all_metrics)==55860 and len(rows)==24,"Combined counts differ")
    pd.DataFrame(rows).to_csv(HERE/"posthoc_results.csv",index=False)
    parquet(HERE/"posthoc_metric_rows.parquet",pd.DataFrame(all_metrics))
    write(HERE/"completion_summary.json",{"status":"COMPLETE_AWAITING_HUMAN_REPORT_AUDIT","label":LABEL,"timestamp":now(),"counts":counts,"metric_rows":len(all_metrics),"block_resource_rows":len(rows),"duplicates":0,"original_results_overwritten":False})
    lines=["# STAGE 18B2 CAPACITY-MATCHED M1 SENSITIVITY REPORT","",LABEL,"","DRAFT: numerical execution/audits complete; human report audit pending. Do not treat this draft as a terminal PASS.","","## Design and capacity","","H64→H129 is the only intended design change. The original M1 inner context/epoch procedure was rerun, followed by one fixed-epoch final refit and one test evaluation. 8,190 inner fits and 2,730 final fits; no frozen fit reuse. External: H129=206,420 versus aggregate S2=206,100 (+0.155264%); TimeTrack: H129=207,980 versus aggregate S2=206,880 (+0.531709%).","","## Results","",RESULT_LABEL,"","| Block / resource | S2 MAE | Common-S2 MAE | H64 MAE | H129 MAE | H64:S2 % | H129:S2 % | H129:H64 % | H129:common-S2 % | Gap |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    keys=["S2_MacroMAE","common_S2_MacroMAE","M1_H64_MacroMAE","M1_H129_MacroMAE","original_H64_vs_S2_gain_percent","H129_vs_S2_gain_percent","H129_vs_H64_gain_percent","H129_vs_common_S2_gain_percent"]
    for r in rows:
        lines.append(f"| {r['block']} / {r['resource']} | "+" | ".join(f"{r[k]:.9g}" for k in keys)+f" | {r['gap_description']} |")
    lines += ["","Descriptions are numerical directions, not formal classes or threshold-based tests. Positive gains favour H129. No block pooling or significance tests were performed.","","## All 24 gap directions",""]
    for r in rows:
        lines.append(f"- {r['block']} {r['resource']}: {r['original_H64_vs_S2_gain_percent']:+.6f}% → {r['H129_vs_S2_gain_percent']:+.6f}%; {r['gap_description']}.")
    lines += ["","## Five priority cases",""]
    priority={("TimeTrack","MEMORY"),("fastStorage","THROUGHPUT"),("Rnd","CPU"),("Materna-T1","DISK_WRITE"),("Materna-T3","DISK_WRITE")}
    for r in rows:
        if (r["block"],r["resource"]) in priority:
            lines.append(f"- {r['block']} {r['resource']}: H64:S2 {r['original_H64_vs_S2_gain_percent']:+.6f}%; H129:S2 {r['H129_vs_S2_gain_percent']:+.6f}%; H129:H64 {r['H129_vs_H64_gain_percent']:+.6f}%; H129:common-S2 {r['H129_vs_common_S2_gain_percent']:+.6f}%. {r['gap_description']}.")
    lines += ["","## Six-block resource checks",""]
    for resource in ("THROUGHPUT","MEMORY","DISK_WRITE"):
        subset=[r for r in rows if r["resource"]==resource]
        lines.append(f"- {resource}: H129 remains adverse versus original S2 in {sum(r['H129_vs_S2_gain_percent']<0 for r in subset)}/6 blocks; versus common-S2 in {sum(r['H129_vs_common_S2_gain_percent']<0 for r in subset)}/6 blocks.")
    lines += ["","## Limitations and preservation","","Aggregate parameter matching does not equalise optimisation geometry, per-target capacity allocation, model count or representation structure. H129 uses its own newly selected context/epoch; those changes are downstream consequences of the unchanged selection policy, not separately isolated interventions. The Stage18B1R common-S2 comparator was aligned to H64's contexts and may not match H129's contexts. Conclusions are post-hoc and limited to the original eligible populations, resources, seeds and conventional shared-LSTM implementation. Runtime is not a clean hardware comparison.","","Full protected-tree SHA256 and refs verified. Manuscript modifications=0; frozen artifacts modified=0; original results modified=0; Stage18B1R modified=0. Commit=NO; push=NO.","","Central capacity interpretation and unexpected findings require human audit of this table before a terminal report.",""]
    (HERE/"STAGE18B2_M1_CAPACITY_MATCHED_REPORT.md").write_text("\n".join(lines))
    inventory()
    print("ALL_SIX_BLOCKS_COMPLETE_HUMAN_REPORT_AUDIT_REQUIRED",flush=True)


if __name__=="__main__":main()
