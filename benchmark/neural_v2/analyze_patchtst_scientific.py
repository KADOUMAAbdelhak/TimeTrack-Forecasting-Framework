#!/usr/bin/env python3
"""Analyze the completed PatchTST benchmark without fitting models."""
from __future__ import annotations
import json, subprocess, time
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from benchmark.neural_v2.analyze_dlinear_scientific import (
    aggregate_tables, atomic_csv, atomic_parquet, build_seed_summary,
    compatible_lightgbm_comparison, macro_metrics,
)
from benchmark.neural_v2.patchtst_aggregation import aggregation_summary, prospective_decision
from benchmark.neural_v2.src.data import FUTURE_LEADS, sample_set_hash
from benchmark.neural_v2.src.validation import atomic_json_write

ROOT=Path(__file__).resolve().parents[2]; BASE=ROOT/"benchmark/neural_v2"
OUT=BASE/"outputs/patchtst"; FIGURES=OUT/"figures"
FEATURES=("F0_LOCAL","F1_THROUGHPUT"); SEEDS=(0,1,2)

def load_predictions(registry, machine, fold):
    rows=registry[registry.machine.eq(machine)&registry.fold.eq(fold)]
    return {(r.feature_set,int(r.seed)):pd.read_parquet(ROOT/r.prediction_path) for r in rows.itertuples(index=False)}

def macro_rows(cells,names):
    rows=[]
    for lead,part in cells.groupby("lead",sort=True):
        row={"aggregation_level":"lead_macro","machine":"ALL","fold":"ALL","lead":int(lead),
             "support_relation":"EXACT_COMMON_SUBSETS","common_test_n":int(part.common_test_n.sum()),
             "common_test_hash":"per-cell hashes recorded above"}
        for name in names:
            f0=float(part[f"{name}_f0_mae"].mean()); f1=float(part[f"{name}_f1_mae"].mean())
            p0=float(np.average(part[f"{name}_f0_mae"],weights=part.common_test_n))
            p1=float(np.average(part[f"{name}_f1_mae"],weights=part.common_test_n))
            row.update({f"{name}_f0_mae":f0,f"{name}_f1_mae":f1,
                f"{name}_primary_gain_pct":100*(f0-f1)/f0,
                f"{name}_pooled_gain_pct":100*(p0-p1)/p0,
                f"{name}_cell_relative_gain_pct":float(part[f"{name}_cell_relative_gain_pct"].mean())})
        rows.append(row)
    return pd.DataFrame(rows)

def neural_comparison(patch_registry,reference_name):
    reference_registry=pd.read_csv(BASE/"outputs"/reference_name/"run_registry.csv"); rows=[]
    for machine in sorted(patch_registry.machine.unique()):
      for fold in sorted(patch_registry.fold.unique()):
        frames_by_name={"patchtst":load_predictions(patch_registry,machine,int(fold)),
                        reference_name:load_predictions(reference_registry,machine,int(fold))}
        sets=[set(x.origin_index.unique()) for frames in frames_by_name.values() for x in frames.values()]
        common=np.asarray(sorted(set.intersection(*sets)),dtype=np.int64)
        relation="EXACT_IDENTICAL" if all(x==sets[0] for x in sets) else "EXACT_INTERSECTION_NO_RETRAIN"
        for lead in FUTURE_LEADS:
          row={"aggregation_level":"machine_fold","machine":machine,"fold":int(fold),"lead":lead,
               "support_relation":relation,"common_test_n":len(common),"common_test_hash":sample_set_hash(common)}
          truth0=None
          for name,frames in frames_by_name.items():
            maes={f:[] for f in FEATURES}
            for feature in FEATURES:
              for seed in SEEDS:
                part=frames[(feature,seed)]; part=part[part.lead.eq(lead)&part.origin_index.isin(common)].sort_values("origin_index")
                truth=part.y_true.to_numpy()
                if truth0 is None: truth0=truth
                elif not np.array_equal(truth0,truth): raise RuntimeError(f"target mismatch {name}/{machine}/{fold}/{lead}")
                maes[feature].append(float(macro_metrics(truth,part.y_pred.to_numpy())[0]))
            f0=float(np.mean(maes[FEATURES[0]])); f1=float(np.mean(maes[FEATURES[1]]))
            row.update({f"{name}_f0_mae":f0,f"{name}_f1_mae":f1,
                f"{name}_primary_gain_pct":100*(f0-f1)/f0,f"{name}_pooled_gain_pct":100*(f0-f1)/f0,
                f"{name}_cell_relative_gain_pct":float(np.mean([100*(a-b)/a for a,b in zip(maes[FEATURES[0]],maes[FEATURES[1]])]))})
          rows.append(row)
    cells=pd.DataFrame(rows)
    return pd.concat([cells,macro_rows(cells,(reference_name,"patchtst"))],ignore_index=True,sort=False)

def lightgbm_comparison(registry):
    base=compatible_lightgbm_comparison(registry)
    deterministic=pd.read_csv(ROOT/"benchmark/outputs/run_registry.csv")
    cells=base[base.aggregation_level.eq("machine_fold")].rename(columns={
      "dlinear_f0_mean_seed_mae":"patchtst_f0_mae","dlinear_f1_mean_seed_mae":"patchtst_f1_mae",
      "lightgbm_f1_context_gain_pct":"lightgbm_cell_relative_gain_pct"}).copy()
    relative=[]
    for row in cells.itertuples(index=False):
      frames=load_predictions(registry,row.machine,int(row.fold))
      lb_record=deterministic[deterministic.model.eq("LightGBM")&deterministic.feature_set.eq("F1_THROUGHPUT")&deterministic.machine.eq(row.machine)&deterministic.outer_fold.eq(int(row.fold))].iloc[0]
      lb_origins=set(pd.read_parquet(ROOT/lb_record.prediction_path,columns=["origin_index"]).origin_index.unique())
      common=set.intersection(lb_origins,*[set(x.origin_index.unique()) for x in frames.values()])
      if len(common)!=int(row.common_test_n): raise RuntimeError("LightGBM/PatchTST intersection count mismatch")
      ratios=[]
      for seed in SEEDS:
        values={}
        for feature in FEATURES:
          p=frames[(feature,seed)]; p=p[p.lead.eq(row.lead)&p.origin_index.isin(common)]
          values[feature]=float(np.mean(np.abs(p.y_true-p.y_pred)))
        ratios.append(100*(values[FEATURES[0]]-values[FEATURES[1]])/values[FEATURES[0]])
      relative.append(float(np.mean(ratios)))
    cells["patchtst_cell_relative_gain_pct"]=relative
    for name in ("lightgbm","patchtst"):
      cells[f"{name}_primary_gain_pct"]=100*(cells[f"{name}_f0_mae"]-cells[f"{name}_f1_mae"])/cells[f"{name}_f0_mae"]
      cells[f"{name}_pooled_gain_pct"]=cells[f"{name}_primary_gain_pct"]
    keep=["aggregation_level","machine","fold","lead","support_relation","common_test_n","common_test_hash",
      *[f"{n}_{s}" for n in ("lightgbm","patchtst") for s in ("f0_mae","f1_mae","primary_gain_pct","pooled_gain_pct","cell_relative_gain_pct")]]
    cells=cells[keep]
    return pd.concat([cells,macro_rows(cells,("lightgbm","patchtst"))],ignore_index=True,sort=False)

def make_figures(summary,by_machine,comparisons):
    FIGURES.mkdir(parents=True,exist_ok=True)
    for p in FIGURES.glob("*.png"): p.unlink()
    leads=summary[~summary.lead.eq("OVERALL")].copy(); leads["lead"]=leads.lead.astype(int)
    plt.figure(figsize=(8,5)); plt.plot(leads.lead,leads.macro_f0_mae,"o-",label="PatchTST F0"); plt.plot(leads.lead,leads.macro_f1_mae,"o-",label="PatchTST F1"); plt.xscale("log",base=2); plt.xlabel("Real future lead"); plt.ylabel("Macro MAE"); plt.title("PatchTST CPU MAE"); plt.legend(); plt.tight_layout(); plt.savefig(FIGURES/"01_patchtst_f0_f1_mae_by_lead.png",dpi=160); plt.close()
    plt.figure(figsize=(8,5)); plt.axhline(0,color="black",lw=1); plt.plot(leads.lead,leads.primary_gain_pct,"o-"); plt.xscale("log",base=2); plt.xlabel("Real future lead"); plt.ylabel("Primary gain (%)"); plt.title("PatchTST primary macro-MAE gain"); plt.tight_layout(); plt.savefig(FIGURES/"02_patchtst_primary_gain_by_lead.png",dpi=160); plt.close()
    heat=by_machine[by_machine.feature_set.eq(FEATURES[1])].pivot(index="machine",columns="lead",values="mae_gain_pct")
    plt.figure(figsize=(10,5)); im=plt.imshow(heat.to_numpy(),aspect="auto",cmap="RdBu_r"); plt.colorbar(im,label="Mean cell-relative gain (%)"); plt.xticks(range(len(heat.columns)),heat.columns); plt.yticks(range(len(heat.index)),heat.index); plt.xlabel("Lead"); plt.ylabel("Machine"); plt.title("PatchTST context gain"); plt.tight_layout(); plt.savefig(FIGURES/"03_patchtst_machine_lead_gain_heatmap.png",dpi=160); plt.close()
    for number,name,title in ((4,"lightgbm","LightGBM"),(5,"lstm","LSTM")):
      macro=comparisons[name][comparisons[name].aggregation_level.eq("lead_macro")]
      plt.figure(figsize=(9,5))
      for model,label in ((name,title),("patchtst","PatchTST")):
        plt.plot(macro.lead,macro[f"{model}_f0_mae"],"o-",label=f"{label} F0"); plt.plot(macro.lead,macro[f"{model}_f1_mae"],"o--",label=f"{label} F1")
      plt.xscale("log",base=2); plt.xlabel("Real future lead"); plt.ylabel("MAE on compatible support"); plt.title(f"PatchTST versus {title}"); plt.legend(); plt.tight_layout(); plt.savefig(FIGURES/f"0{number}_patchtst_vs_{name}_mae.png",dpi=160); plt.close()
    cross=pd.read_csv(BASE/"CROSS_MODEL_CONTEXT_SUMMARY.csv",dtype={"lead":str}); cross=cross[~cross.lead.eq("OVERALL")]
    plt.figure(figsize=(10,6))
    for model,part in cross.groupby("model",sort=False): plt.plot(part.lead.astype(int),part.primary_ratio_macro_mae_gain_pct,"o-",label=model)
    plt.axhline(0,color="black",lw=1); plt.xscale("log",base=2); plt.xlabel("Real future lead"); plt.ylabel("Primary macro-MAE gain (%)"); plt.title("Standardized context gain across five models"); plt.legend(); plt.tight_layout(); plt.savefig(FIGURES/"06_five_model_primary_context_gain.png",dpi=160); plt.close()

def wins(frame,name):
    p=frame[frame.aggregation_level.eq("lead_macro")]
    return (int((p.patchtst_f0_mae<p[f"{name}_f0_mae"]).sum()),int((p.patchtst_f1_mae<p[f"{name}_f1_mae"]).sum()),int((p.patchtst_primary_gain_pct>p[f"{name}_primary_gain_pct"]).sum()))

def markdown(frame):
    columns=list(frame.columns); lines=["| "+" | ".join(columns)+" |","|"+"|".join("---" for _ in columns)+"|"]
    for row in frame.itertuples(index=False,name=None):
      lines.append("| "+" | ".join(f"{x:.6f}" if isinstance(x,(float,np.floating)) else str(x) for x in row)+" |")
    return "\n".join(lines)

def write_report(summary,selected,comparisons,label,counts,subgroups):
    leads=summary[~summary.lead.eq("OVERALL")].copy(); leads["lead"]=leads.lead.astype(int); leads=leads.sort_values("lead")
    overall=summary[summary.lead.eq("OVERALL")].iloc[0]; sc=selected.groupby(["feature_set","selected_L"]).size(); piv=selected.pivot(index=["machine","fold"],columns="feature_set",values="selected_L")
    w={n:wins(f,n) for n,f in comparisons.items()}; cross=pd.read_csv(BASE/"CROSS_MODEL_CONTEXT_SUMMARY.csv",dtype={"lead":str}); overall_table=cross[cross.lead.eq("OVERALL")][["model","primary_ratio_macro_mae_gain_pct","pooled_gain_pct","mean_cell_relative_gain_pct"]]
    lines=["# Phase 2B-2A3 PatchTST Scientific Report","","Descriptive results only; no significance test was performed.","",
      "## Lead-level aggregation","","| Lead | Macro F0 | Macro F1 | Primary % | Pooled % | Mean cell % | Median cell % | Positive fraction |","|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in leads.itertuples(index=False): lines.append(f"| {r.lead} | {r.macro_f0_mae:.6f} | {r.macro_f1_mae:.6f} | {r.primary_gain_pct:.6f} | {r.pooled_gain_pct:.6f} | {r.mean_cell_relative_gain_pct:.6f} | {r.median_cell_relative_gain_pct:.6f} | {r.positive_cell_fraction:.6f} |")
    long=comparisons["lightgbm"].query("aggregation_level == 'lead_macro' and lead >= 32")
    lines += ["","## Required scientific answers","",
      f"1. PatchTST F0 macro-MAE vector: {leads.macro_f0_mae.tolist()}.",
      f"2. PatchTST F1 macro-MAE vector: {leads.macro_f1_mae.tolist()}.",
      f"3. Primary throughput-gain vector: {leads.primary_gain_pct.tolist()}%.",
      f"4. Pooled throughput-gain vector: {leads.pooled_gain_pct.tolist()}%.",
      f"5. Mean cell-relative gain vector: {leads.mean_cell_relative_gain_pct.tolist()}%.",
      f"6. Positive machines: {subgroups['machine'][subgroups['machine']>0].index.tolist()} ({counts['positive_machines']}/7).",
      f"7. Positive folds: {[int(x) for x in subgroups['fold'][subgroups['fold']>0].index]} ({counts['positive_folds']}/5).",
      f"8. Seed effects: {subgroups['seed'].round(6).to_dict()}; positive seeds {counts['positive_seeds']}/3.",
      f"9. F0 selected-L distribution: {sc.get('F0_LOCAL',pd.Series(dtype=int)).to_dict()}.",
      f"10. F1 selected-L distribution: {sc.get('F1_THROUGHPUT',pd.Series(dtype=int)).to_dict()}.",
      f"11. Throughput changes selected L in {int((piv.F0_LOCAL!=piv.F1_THROUGHPUT).sum())}/35 cells.",
      f"12. Versus LightGBM, PatchTST wins {w['lightgbm'][0]}/8 F0 and {w['lightgbm'][1]}/8 F1 leads.",
      f"13. Versus DLinear, PatchTST wins {w['dlinear'][0]}/8 F0 and {w['dlinear'][1]}/8 F1 leads; larger primary context gain at {w['dlinear'][2]}/8.",
      f"14. Versus LSTM, PatchTST wins {w['lstm'][0]}/8 F0 and {w['lstm'][1]}/8 F1 leads; larger primary context gain at {w['lstm'][2]}/8.",
      f"15. PatchTST uses throughput more effectively than LightGBM at {w['lightgbm'][2]}/8 leads.",
      f"16. PatchTST uses throughput more effectively than LSTM at {w['lstm'][2]}/8 leads.",
      f"17. PatchTST F1 beats LightGBM F1 at {int((long.patchtst_f1_mae<long.lightgbm_f1_mae).sum())}/3 longer horizons (32/64/128).",
      "18. The five-model results show architecture-dependent throughput effects; there is no universal direction across Ridge, LightGBM, DLinear, LSTM, and PatchTST.",
      "","## Five-model standardized overall context table","",markdown(overall_table),
      "","## Prospective PatchTST decision","",f"**{label}**; overall primary macro-MAE gain {float(overall.primary_gain_pct):.6f}%.",f"Consistency counts: `{json.dumps(counts,sort_keys=True)}`.","",
      "Comparisons use exact support/intersections without retraining. DLinear, LSTM, and LightGBM were not rerun. No TCN-v2, B4-v1, or multi-target model was executed."]
    (BASE/"PATCHTST_SCIENTIFIC_REPORT.md").write_text("\n".join(lines)+"\n")

def main():
    started=time.perf_counter(); metrics=pd.read_parquet(OUT/"metrics.parquet"); registry=pd.read_csv(OUT/"run_registry.csv"); selected=pd.read_csv(OUT/"selected_contexts.csv")
    summary,matched=aggregation_summary(metrics,registry); atomic_csv(OUT/"aggregation_summary.csv",summary)
    atomic_parquet(OUT/"f0_f1_matched_metrics.parquet",matched.drop(columns=["test_sample_count"])); atomic_csv(OUT/"seed_summary.csv",build_seed_summary(metrics,matched))
    by_lead,by_machine,by_fold=aggregate_tables(metrics,matched); atomic_csv(OUT/"aggregate_by_lead.csv",by_lead); atomic_csv(OUT/"aggregate_by_machine.csv",by_machine); atomic_csv(OUT/"aggregate_by_fold.csv",by_fold)
    comparisons={"lightgbm":lightgbm_comparison(registry),"dlinear":neural_comparison(registry,"dlinear"),"lstm":neural_comparison(registry,"lstm")}
    for name,frame in comparisons.items(): atomic_csv(OUT/f"patchtst_vs_{name}.csv",frame)
    label,counts,subgroups=prospective_decision(summary,matched)
    subprocess.run(["/private/tmp/timetrack-neural-v2-venv/bin/python","-m","benchmark.neural_v2.build_cross_model_context_summary"],cwd=ROOT,check=True)
    make_figures(summary,by_machine,comparisons); write_report(summary,selected,comparisons,label,counts,subgroups)
    path=OUT/"runtime_accounting.json"; runtime=json.loads(path.read_text()); runtime["analysis_wall_seconds"]=time.perf_counter()-started; runtime["total_recorded_wall_seconds"]=runtime["execution_wall_seconds"]+runtime["analysis_wall_seconds"]; runtime["status"]="ANALYSIS_COMPLETE_VALIDATION_PENDING"; runtime["patchtst_throughput_decision"]=label; runtime["decision_counts"]=counts
    pilot=float(runtime["pilot_central_patchtst_projection_hours"])*3600; runtime["actual_to_pilot_runtime_ratio"]=float(runtime["execution_wall_seconds"])/pilot; runtime["actual_minus_pilot_seconds"]=float(runtime["execution_wall_seconds"])-pilot; atomic_json_write(path,runtime)
    print(json.dumps({"decision":label,**counts},indent=2))
if __name__=="__main__": main()
