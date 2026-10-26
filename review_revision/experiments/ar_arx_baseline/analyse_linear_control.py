"""Only authorised block/resource MacroMAE, persistence skill and gain comparisons."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from run_linear_control import HERE, ROOT, CONFIG, LABEL, RESULT_LABEL, read, write, parquet, sha, now, require, frozen, verify_seal, unresolved_failures

def original_gain(block,resource):
    root = ROOT/frozen.FROZEN[block]
    if block == "TimeTrack":
        path = root/"comparisons/s2_vs_s1.csv"; frame = pd.read_csv(path)
        row = frame[frame.resource.eq(resource) & frame.lead.eq("OVERALL")]
        require(len(row)==1,"Frozen comparison not unique")
        return float(row.iloc[0].primary_gain_pct),path
    path = root.parent/"comparisons/secondary_aggregation_diagnostics.csv"
    frame = pd.read_csv(path); key = "trace" if block.startswith("Materna") else "environment"
    row = frame[frame[key].eq(block) & frame.resource.eq(resource) & frame.comparison.eq("S2_vs_S1") & frame.scope.eq("overall")]
    require(len(row)==1,"Frozen comparison not unique")
    return float(row.iloc[0].primary_macro_gain_percent),path

def sign(value): return "positive" if value>0 else "negative" if value<0 else "zero"

def inventory():
    records = [{"path":str(p.relative_to(HERE)),"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(HERE.rglob("*")) if p.is_file() and p.name not in {"output_sha256_inventory.json","execution.log","runtime.lock"}]
    write(HERE/"output_sha256_inventory.json", {"timestamp":now(),"files":records,"exclusions":["self-referential inventory","execution.log (live orchestration output)","runtime.lock (advisory lock)"]})

def main():
    verify_seal(); require(read(HERE/"provenance/preservation_after.json")["status"]=="PASS","Preservation required")
    require(not unresolved_failures(),"Unresolved failures exist")
    all_metrics=[]; rows=[]; audits={}; sources={}
    for b in read(CONFIG)["blocks"]:
        audit = read(HERE/f"validation/full_audit_{b}.json"); require(audit["status"]=="PASS","Block audit required"); audits[b]=audit
        metrics=[]
        for p in sorted((HERE/f"completions/final/{b}").glob("*.json")):
            value=read(p); identity=value["identity"]
            for m in value["metrics"]:
                metrics.append({"label":RESULT_LABEL,"block":b,"entity":identity["entity"],"fold":identity["fold"],"formulation":identity["formulation"],"L":identity["L"],"alpha":identity["alpha"],"run_id":identity["run_id"],**m})
        frame=pd.DataFrame(metrics)
        require(not frame.duplicated(["entity","fold","formulation","resource","lead"]).any(),"Duplicate metric identities")
        require(len(frame)==audit["metric_rows"] and np.isfinite(frame.mae).all(),"Metric coverage/finiteness")
        macro = frame.groupby(["formulation","resource","lead"],as_index=False).agg(mae=("mae","mean"),skill=("persistence_skill","mean"))
        macro = macro.groupby(["formulation","resource"])[["mae","skill"]].mean()
        for r in read(CONFIG)["resources"]:
            ar = float(macro.loc[("AR",r),"mae"]); arx=float(macro.loc[("ARX",r),"mae"])
            require(ar>0,"AR gain denominator zero","PRIMARY_GAIN_DENOMINATOR_CONFLICT")
            gain=100*(ar-arx)/ar; lstm,path=original_gain(b,r); sources[str(path.relative_to(ROOT))]=sha(path)
            subset=frame[frame.resource.eq(r)]
            rows.append({"label":RESULT_LABEL,"block":b,"resource":r,"AR_MacroMAE":ar,"ARX_MacroMAE":arx,"ARX_vs_AR_gain_percent":gain,"AR_persistence_skill":float(macro.loc[("AR",r),"skill"]),"ARX_persistence_skill":float(macro.loc[("ARX",r),"skill"]),"frozen_S2_vs_S1_gain_percent":lstm,"Ridge_direction":sign(gain),"LSTM_direction":sign(lstm),"direction_agrees":sign(gain)==sign(lstm),"gain_difference_percentage_points":gain-lstm,"AR_undefined_skill_cells":int(subset[subset.formulation.eq("AR")].persistence_skill.isna().sum()),"ARX_undefined_skill_cells":int(subset[subset.formulation.eq("ARX")].persistence_skill.isna().sum())})
        parquet(HERE/f"metrics/{b}.parquet",frame); all_metrics.extend(metrics)
    summary=pd.DataFrame(rows); require(len(summary)==24 and np.isfinite(summary.select_dtypes("number").to_numpy()).all(),"Nonfinite primary summary")
    summary.to_csv(HERE/"posthoc_results.csv",index=False)
    parquet(HERE/"posthoc_metric_rows.parquet",pd.DataFrame(all_metrics))
    write(HERE/"provenance/frozen_comparison_sources.json",sources)
    write(HERE/"completion_summary.json", {"status":"COMPLETE_AWAITING_REPORT_AUDIT","label":LABEL,"counts":{"inner":sum(a["inner"] for a in audits.values()),"final":sum(a["final"] for a in audits.values()),"failed":0},"metric_rows":len(all_metrics),"duplicates":0,"block_resource_rows":24,"timestamp":now()})
    lines=["# STAGE 18B3 — MATCHED LINEAR AR/ARX BASELINE","",RESULT_LABEL,"","Numerically complete; report pending interpretation audit. This is a POST-HOC SENSITIVITY CONTROL, not a replacement for frozen results.","","## Verification and counts","","All six block audits pass: 36,400 inner alpha fits + 7,280 final fits = 43,680 deterministic Ridge fits; no seed repetitions, failed units or duplicate identities. There are 7,280 selections, final model-state files and prediction files, and 37,240 per-lead metric rows. No inner model checkpoint is claimed or needed: all five scores/identities are retained for each selection. Support, frozen cohort membership, original H64-M1 contexts, inner/outer source scalers, native targets, persistence and all predictions/primary MAEs are checked. Every final fit has exactly one test prediction call.","","## Results","","Native-unit MAEs; positive gain favours ARX (or frozen S2). Skill is 1−MAE/persistence-MAE per entity/fold/lead, averaged over entity/fold then equally over horizons; it is not 1−MacroMAE/MacroPersistenceMAE. Higher skill is better, zero matches persistence. Undefined zero-denominator skills are omitted by the frozen mean semantics, with explicit counts in the CSV and metric records.","","| Block / resource | AR MAE | ARX MAE | ARX:AR % | AR skill | ARX skill | S2:S1 % | Direction |","|---|---:|---:|---:|---:|---:|---:|---|"]
    for row in rows:
        lines.append(f"| {row['block']} / {row['resource']} | "+" | ".join(f"{row[k]:.9g}" for k in ("AR_MacroMAE","ARX_MacroMAE","ARX_vs_AR_gain_percent","AR_persistence_skill","ARX_persistence_skill","frozen_S2_vs_S1_gain_percent"))+f" | {'agree' if row['direction_agrees'] else 'disagree'} |")
    lines += ["","## Direction and magnitude, without thresholds or significance tests",""]
    for row in rows:
        magnitude="smaller" if abs(row["ARX_vs_AR_gain_percent"])<abs(row["frozen_S2_vs_S1_gain_percent"]) else "larger" if abs(row["ARX_vs_AR_gain_percent"])>abs(row["frozen_S2_vs_S1_gain_percent"]) else "equal"
        lines.append(f"- {row['block']} {row['resource']}: Ridge {row['ARX_vs_AR_gain_percent']:+.6f}% versus frozen LSTM {row['frozen_S2_vs_S1_gain_percent']:+.6f}%; {'agreement' if row['direction_agrees'] else 'disagreement'}, {magnitude} absolute gain magnitude; difference {row['gain_difference_percentage_points']:+.6f} percentage points.")
    lines += ["","## Protocol and limitations","","Original frozen M1-H64 selected context is shared by AR and ARX in each entity/fold. No contexts, seeds, cohorts, horizons, purging or legal origins were tuned. Five alphas (0.01, 0.1, 1, 10, 100) are scored strictly on inner validation by native-unit MAE after frozen inversion/nonnegative projection, equally over horizons; ties choose smaller alpha using the existing selector at fixed L. Each selected alpha is refit once on the frozen outer training partition. Targets use the frozen identity/log1p transforms and training-only median/IQR source scalers. Existing RidgeForecaster adds its own training-only lag-feature StandardScaler, identically for both forms. Direct multi-output horizon prediction, per-entity fits, deterministic Ridge and no artificial repetitions are used.","","This is not a generic architecture-only causal comparison: the shared contexts were chosen by original M1, whereas original S1/S2 selected their own contexts; Ridge's alpha objective and linear regularisation differ from neural optimisation/epoch selection. The five-alpha grid, additive linear specification, frozen eligible populations and finite horizons limit generalisation. A single deterministic fit does not provide sampling uncertainty. Larger or smaller point gains do not establish statistical or practical importance. No thresholds, pooled cross-block statistic, significance tests, capacity retuning or additional experiments were introduced.","","## Preservation and artifacts","","Only review_revision/experiments/ar_arx_baseline was written. Full protected-tree SHA256 membership/content and refs are audited, including the entire original scientific/manuscript trees, both completed post-hoc controls and the Stage18B1R predecessor. Manuscript modifications=0; frozen artifacts modified=0; prior controls modified=0. Commit=no; push=no.","","Configuration/source/plan hashes: provenance/experiment.json. Exact plans: plans/. Fit identities/scores/final metrics/hashes: attempts/, completions/, selections/. Final coefficient/intercept/feature-scaler arrays: models/. Native predictions/support: predictions/. Six-block audits: validation/full_audit_*.json. Detailed results: posthoc_results.csv and posthoc_metric_rows.parquet. Full protected baseline/after audit: provenance/. Output hashes: output_sha256_inventory.json.",""]
    (HERE/"STAGE18B3R_AR_ARX_RECOVERY_REPORT.md").write_text("\n".join(lines))
    inventory(); print("COMPLETE_AWAITING_REPORT_AUDIT",flush=True)

if __name__=="__main__": main()
