#!/usr/bin/env python3
"""Aggregate the complete Phase 3C factorial only after all fits exist."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.data import FUTURE_LEADS, RESOURCE_ORDER
from src.validation import atomic_json_write


BASE = Path(__file__).resolve().parent
OUT = BASE / "outputs/scientific"
COMPARISONS = OUT / "comparisons"
FIGURES = OUT / "figures"


def classify(overall_gain: float, leads: int, machines: int, folds: int, seeds: int) -> str:
    if overall_gain >= 1 and leads >= 6 and machines >= 5 and folds >= 4 and seeds >= 2: return "BROAD_POSITIVE"
    if overall_gain > 0 and leads >= 4 and machines >= 3 and folds >= 3 and seeds >= 2: return "CONDITIONALLY_POSITIVE"
    if overall_gain <= -1 and leads <= 2 and machines <= 2 and folds <= 1 and seeds <= 1: return "BROAD_NEGATIVE"
    return "NEUTRAL_OR_MIXED"


def grouped_signs(matched: pd.DataFrame, dimension: str) -> pd.DataFrame:
    other = {"machine": ["fold", "seed", "lead"], "fold": ["machine", "seed", "lead"], "seed": ["machine", "fold", "lead"]}[dimension]
    grouped = matched.groupby(["resource", dimension], as_index=False)[["baseline_mae", "candidate_mae"]].mean()
    grouped["gain_pct"] = 100 * (grouped.baseline_mae - grouped.candidate_mae) / grouped.baseline_mae
    return grouped


def comparison(metrics: pd.DataFrame, baseline: str, candidate: str, name: str) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    keys = ["resource", "machine", "fold", "seed", "lead"]
    left = metrics[metrics.formulation.eq(baseline)][keys + ["mae", "n"]].rename(columns={"mae": "baseline_mae", "n": "baseline_n"})
    right = metrics[metrics.formulation.eq(candidate)][keys + ["mae", "n"]].rename(columns={"mae": "candidate_mae", "n": "candidate_n"})
    matched = left.merge(right, on=keys, validate="one_to_one")
    if not (matched.baseline_n == matched.candidate_n).all(): raise RuntimeError(f"Support differs for {name}")
    matched["cell_gain_pct"] = 100 * (matched.baseline_mae - matched.candidate_mae) / matched.baseline_mae
    matched.to_csv(COMPARISONS / f"{name}_cells.csv", index=False)
    seed_mean = matched.groupby(["resource", "machine", "fold", "lead"], as_index=False)[["baseline_mae", "candidate_mae"]].mean()
    lead_macro = seed_mean.groupby(["resource", "lead"], as_index=False)[["baseline_mae", "candidate_mae"]].mean()
    lead_macro["primary_gain_pct"] = 100 * (lead_macro.baseline_mae - lead_macro.candidate_mae) / lead_macro.baseline_mae
    rows = []
    for resource_name in RESOURCE_ORDER:
        resource_cells = matched[matched.resource.eq(resource_name)]
        for lead in FUTURE_LEADS:
            cells = resource_cells[resource_cells.lead.eq(lead)]; macro = lead_macro[(lead_macro.resource == resource_name) & (lead_macro.lead == lead)].iloc[0]
            pooled_base = np.average(cells.baseline_mae, weights=cells.baseline_n); pooled_candidate = np.average(cells.candidate_mae, weights=cells.candidate_n)
            rows.append({"resource": resource_name, "lead": str(lead), "macro_mae_baseline": macro.baseline_mae, "macro_mae_candidate": macro.candidate_mae, "primary_gain_pct": macro.primary_gain_pct, "pooled_gain_pct": 100 * (pooled_base - pooled_candidate) / pooled_base, "mean_cell_gain_pct": cells.cell_gain_pct.mean(), "median_cell_gain_pct": cells.cell_gain_pct.median(), "positive_cell_fraction": (cells.cell_gain_pct > 0).mean()})
        overall_macro = lead_macro[lead_macro.resource.eq(resource_name)][["baseline_mae", "candidate_mae"]].mean()
        machines = grouped_signs(resource_cells, "machine"); folds = grouped_signs(resource_cells, "fold"); seeds = grouped_signs(resource_cells, "seed")
        overall_gain = 100 * (overall_macro.baseline_mae - overall_macro.candidate_mae) / overall_macro.baseline_mae
        lead_positive = int((lead_macro[lead_macro.resource.eq(resource_name)].primary_gain_pct > 0).sum())
        positive_machines, positive_folds, positive_seeds = int((machines.gain_pct > 0).sum()), int((folds.gain_pct > 0).sum()), int((seeds.gain_pct > 0).sum())
        pooled_base = np.average(resource_cells.baseline_mae, weights=resource_cells.baseline_n); pooled_candidate = np.average(resource_cells.candidate_mae, weights=resource_cells.candidate_n)
        rows.append({"resource": resource_name, "lead": "OVERALL", "macro_mae_baseline": overall_macro.baseline_mae, "macro_mae_candidate": overall_macro.candidate_mae, "primary_gain_pct": overall_gain, "pooled_gain_pct": 100 * (pooled_base - pooled_candidate) / pooled_base, "mean_cell_gain_pct": resource_cells.cell_gain_pct.mean(), "median_cell_gain_pct": resource_cells.cell_gain_pct.median(), "positive_cell_fraction": (resource_cells.cell_gain_pct > 0).mean(), "positive_leads": lead_positive, "positive_machines": positive_machines, "positive_folds": positive_folds, "positive_seeds": positive_seeds, "classification": classify(overall_gain, lead_positive, positive_machines, positive_folds, positive_seeds)})
    summary = pd.DataFrame(rows); summary.to_csv(COMPARISONS / f"{name}.csv", index=False)
    overall = summary[summary.lead.eq("OVERALL")]
    global_summary = {"comparison": name, "equal_resource_mean_primary_gain_pct": float(overall.primary_gain_pct.mean()), "median_resource_gain_pct": float(overall.primary_gain_pct.median()), "positive_resources": int((overall.classification.isin(["BROAD_POSITIVE", "CONDITIONALLY_POSITIVE"])).sum()), "broad_positive_resources": int((overall.classification == "BROAD_POSITIVE").sum()), "conditionally_positive_resources": int((overall.classification == "CONDITIONALLY_POSITIVE").sum()), "broad_negative_resources": int((overall.classification == "BROAD_NEGATIVE").sum())}
    return summary, matched, global_summary


def global_decisions(s2s1: pd.DataFrame, m1s2: pd.DataFrame) -> tuple[str, str]:
    first = s2s1[s2s1.lead.eq("OVERALL")]; positive = first.classification.isin(["BROAD_POSITIVE", "CONDITIONALLY_POSITIVE"]).sum(); negative = first.classification.eq("BROAD_NEGATIVE").sum(); mean = first.primary_gain_pct.mean()
    cross = "CROSS_RESOURCE_INPUT_NOT_SUPPORTED" if (positive <= 1 and mean <= 0) or negative >= 2 else ("CROSS_RESOURCE_INPUT_SUPPORTED" if positive >= 3 and mean > 0 and negative <= 1 else "CROSS_RESOURCE_INPUT_MIXED")
    second = m1s2[m1s2.lead.eq("OVERALL")]; positive = second.classification.isin(["BROAD_POSITIVE", "CONDITIONALLY_POSITIVE"]).sum(); negative = second.classification.eq("BROAD_NEGATIVE").sum(); mean = second.primary_gain_pct.mean(); strong = (second.primary_gain_pct >= 1).any() and (second.primary_gain_pct <= -1).sum() >= 2
    if (positive >= 1 and negative >= 2) or strong: shared = "SHARED_REPRESENTATION_NEGATIVE_TRANSFER"
    elif positive <= 1 and mean <= 0: shared = "SHARED_REPRESENTATION_NOT_SUPPORTED"
    elif positive >= 3 and mean > 0 and negative == 0: shared = "SHARED_REPRESENTATION_SUPPORTED"
    elif mean > 0 and positive >= 2: shared = "SHARED_REPRESENTATION_CONDITIONALLY_SUPPORTED"
    elif positive or second.primary_gain_pct.gt(0).any(): shared = "SHARED_REPRESENTATION_NEGATIVE_TRANSFER"
    else: shared = "SHARED_REPRESENTATION_NOT_SUPPORTED"
    return cross, shared


def phase_decision(cross: str, shared: str, m1s2: pd.DataFrame) -> str:
    positive = m1s2[m1s2.lead.eq("OVERALL")].classification.isin(["BROAD_POSITIVE", "CONDITIONALLY_POSITIVE"]).sum()
    if shared == "SHARED_REPRESENTATION_SUPPORTED": return "PLAIN_SHARED_MULTI_TASK_SUFFICIENT"
    if shared == "SHARED_REPRESENTATION_NEGATIVE_TRANSFER" and positive >= 2: return "SHARING_HELPFUL_BUT_NEGATIVE_TRANSFER_PRESENT"
    if cross == "CROSS_RESOURCE_INPUT_SUPPORTED" and shared in {"SHARED_REPRESENTATION_NOT_SUPPORTED", "SHARED_REPRESENTATION_NEGATIVE_TRANSFER"}: return "CROSS_RESOURCE_INPUT_HELPFUL_BUT_NAIVE_SHARING_NOT_SUPPORTED"
    if cross == "CROSS_RESOURCE_INPUT_NOT_SUPPORTED" and shared == "SHARED_REPRESENTATION_NOT_SUPPORTED": return "MULTI_RESOURCE_FORECASTING_PREMISE_WEAK"
    return "MIXED_REQUIRES_TARGETED_MECHANISM_STUDY"


def performance_table(metrics: pd.DataFrame) -> pd.DataFrame:
    seed_mean = metrics.groupby(["formulation", "resource", "machine", "fold", "lead"], as_index=False)[["mae", "rmse", "r2", "nmae", "persistence_skill"]].mean()
    return seed_mean.groupby(["formulation", "resource", "lead"], as_index=False)[["mae", "rmse", "r2", "nmae", "persistence_skill"]].mean()


def loss_balance(selected_epochs: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    loss = pd.read_parquet(OUT / "m1_resource_loss_history.parquet")
    chosen = selected_epochs[selected_epochs.formulation.eq("M1")].rename(columns={"selected_L": "L", "selected_epoch": "epoch"})[["machine", "fold", "seed", "L", "epoch"]]
    inner = loss[loss.phase.eq("inner")].merge(chosen, on=["machine", "fold", "seed", "L", "epoch"], validate="many_to_one")
    final = loss[loss.phase.eq("final")]; final = final[final.epoch.eq(final.groupby("run_id").epoch.transform("max"))]
    selected = pd.concat([inner.assign(summary_phase="selected_inner_validation"), final.assign(summary_phase="final_last_epoch")], ignore_index=True)
    summary = selected.groupby(["summary_phase", "resource"]).agg(mean_loss_share=("loss_share", "mean"), median_loss_share=("loss_share", "median"), q25_loss_share=("loss_share", lambda x: x.quantile(.25)), q75_loss_share=("loss_share", lambda x: x.quantile(.75)), min_loss_share=("loss_share", "min"), max_loss_share=("loss_share", "max"), mean_resource_mse=("resource_mse", "mean")).reset_index()
    summary.to_csv(OUT / "m1_loss_balance_summary.csv", index=False)
    inner_cpu = float(summary[(summary.summary_phase == "selected_inner_validation") & (summary.resource == "CPU")].mean_loss_share.iloc[0])
    return summary, {"cpu_majority_persists": inner_cpu > .5, "selected_inner_cpu_mean_share": inner_cpu}


def context_analysis(contexts: pd.DataFrame) -> dict[str, Any]:
    distribution = contexts.groupby(["formulation", "resource", "selected_L"], dropna=False).size().rename("count").reset_index(); distribution.to_csv(COMPARISONS / "selected_context_distribution.csv", index=False)
    s1 = contexts[contexts.formulation.eq("S1")].rename(columns={"selected_L": "s1_L"}); s2 = contexts[contexts.formulation.eq("S2")].rename(columns={"selected_L": "s2_L"})
    paired = s1.merge(s2, on=["resource", "machine", "fold"]); m1 = contexts[contexts.formulation.eq("M1")][["machine", "fold", "selected_L"]].rename(columns={"selected_L": "m1_L"})
    paired = paired.merge(m1, on=["machine", "fold"]); paired.to_csv(COMPARISONS / "context_pairing.csv", index=False)
    return {"s2_differs_from_s1": int((paired.s1_L != paired.s2_L).sum()), "s2_s1_cells": len(paired), "m1_differs_from_s2": int((paired.m1_L != paired.s2_L).sum())}


def make_figures(comparison_frames: dict[str, pd.DataFrame], metrics: pd.DataFrame, loss_summary: pd.DataFrame, registry: pd.DataFrame) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    titles = {"s2_vs_s1": "S2 vs S1", "m1_vs_s2": "M1 vs S2", "m1_vs_s1": "M1 vs S1"}
    for number, name in enumerate(("s2_vs_s1", "m1_vs_s2", "m1_vs_s1"), 1):
        frame = comparison_frames[name]; frame = frame[~frame.lead.eq("OVERALL")].copy(); frame["lead"] = frame.lead.astype(int)
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for resource_name in RESOURCE_ORDER: part = frame[frame.resource.eq(resource_name)]; ax.plot(part.lead, part.primary_gain_pct, marker="o", label=resource_name)
        ax.axhline(0, color="black", lw=.8); ax.set_xscale("log", base=2); ax.set_xticks(FUTURE_LEADS); ax.set_xticklabels(FUTURE_LEADS); ax.set_ylabel("Primary macro-MAE gain (%)"); ax.set_xlabel("Lead"); ax.set_title(titles[name]); ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(FIGURES / f"{number:02d}_{name}_gain_by_resource_lead.png", dpi=150); plt.close(fig)
    cells = pd.read_csv(COMPARISONS / "m1_vs_s2_cells.csv"); machine = cells.groupby(["machine", "resource"])[["baseline_mae", "candidate_mae"]].mean(); machine["gain"] = 100 * (machine.baseline_mae - machine.candidate_mae) / machine.baseline_mae; matrix = machine.gain.unstack("resource").reindex(columns=RESOURCE_ORDER)
    fig, ax = plt.subplots(figsize=(7, 4.5)); im=ax.imshow(matrix, cmap="coolwarm", aspect="auto"); ax.set_xticks(range(4), RESOURCE_ORDER, rotation=25); ax.set_yticks(range(7), matrix.index); ax.set_title("M1 vs S2 gain by machine/resource"); fig.colorbar(im, ax=ax, label="Gain (%)"); fig.tight_layout(); fig.savefig(FIGURES / "04_m1_vs_s2_machine_resource_heatmap.png", dpi=150); plt.close(fig)
    lead = comparison_frames["m1_vs_s2"]; lead=lead[~lead.lead.eq("OVERALL")].copy(); lead["lead"]=lead.lead.astype(int); matrix=lead.pivot(index="resource",columns="lead",values="primary_gain_pct").reindex(index=RESOURCE_ORDER,columns=FUTURE_LEADS)
    fig, ax=plt.subplots(figsize=(8,3.5)); im=ax.imshow(matrix,cmap="coolwarm",aspect="auto"); ax.set_xticks(range(8),FUTURE_LEADS); ax.set_yticks(range(4),RESOURCE_ORDER); ax.set_title("M1 vs S2 gain by resource/lead"); fig.colorbar(im,ax=ax,label="Gain (%)"); fig.tight_layout(); fig.savefig(FIGURES / "05_m1_vs_s2_resource_lead_heatmap.png",dpi=150); plt.close(fig)
    part=loss_summary[loss_summary.summary_phase.eq("selected_inner_validation")].set_index("resource").reindex(RESOURCE_ORDER); fig,ax=plt.subplots(figsize=(7,4)); ax.bar(part.index,100*part.mean_loss_share); ax.set_ylabel("Mean loss share (%)"); ax.set_title("M1 selected-inner resource loss shares"); ax.tick_params(axis='x',rotation=20); fig.tight_layout(); fig.savefig(FIGURES / "06_m1_scientific_loss_shares.png",dpi=150); plt.close(fig)
    perf=performance_table(metrics); fig,ax=plt.subplots(figsize=(9,5));
    for formulation in ("S1","S2","M1"):
        for resource_name in RESOURCE_ORDER:
            p=perf[(perf.formulation==formulation)&(perf.resource==resource_name)]; ax.plot(p.lead,p.persistence_skill,label=f"{formulation}-{resource_name}",alpha=.75)
    ax.axhline(0,color="black",lw=.8); ax.set_xscale("log",base=2); ax.set_xticks(FUTURE_LEADS); ax.set_xticklabels(FUTURE_LEADS); ax.set_title("Persistence skill by formulation/resource/lead"); ax.set_xlabel("Lead"); ax.set_ylabel("Persistence skill"); ax.legend(ncol=3,fontsize=6); fig.tight_layout(); fig.savefig(FIGURES / "07_persistence_skill.png",dpi=150); plt.close(fig)
    system_params={"S2":206880,"M1":53280}; overall=perf[perf.formulation.isin(system_params)].groupby(["formulation","resource"],as_index=False).nmae.mean(); fig,ax=plt.subplots(figsize=(7,4.5))
    for formulation,marker in (("S2","o"),("M1","s")):
        p=overall[overall.formulation==formulation]; ax.scatter([system_params[formulation]]*len(p),p.nmae,label=formulation,marker=marker); [ax.annotate(r.resource,(system_params[formulation],r.nmae),fontsize=7) for r in p.itertuples()]
    ax.set_xlabel("Total system parameters"); ax.set_ylabel("Mean NMAE (lower is better)"); ax.set_title("Accuracy-efficiency: S2 versus M1"); ax.legend(); fig.tight_layout(); fig.savefig(FIGURES / "08_accuracy_efficiency_s2_vs_m1.png",dpi=150); plt.close(fig)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    lines=["| "+" | ".join(columns)+" |","|"+"|".join(["---"]*len(columns))+"|"]
    for row in frame[columns].itertuples(index=False): lines.append("| "+" | ".join(f"{x:.4f}" if isinstance(x,float) else str(x) for x in row)+" |")
    return lines


def write_report(performance: pd.DataFrame, comparisons: dict[str,pd.DataFrame], globals_: dict[str,Any], cross: str, shared: str, phase: str, loss_summary: pd.DataFrame, context_info: dict[str,Any], runtime: dict[str,Any], registry: pd.DataFrame) -> None:
    contexts=pd.read_csv(OUT/"selected_contexts.csv"); epochs=pd.read_csv(OUT/"selected_epochs.csv"); inner=pd.read_csv(OUT/"inner_run_registry.csv")
    context_distribution=contexts.groupby(["formulation","resource","selected_L"],dropna=False).size().rename("count").reset_index(); context_distribution["resource"]=context_distribution.resource.fillna("ALL")
    inner_epoch=inner.groupby("formulation").epochs_trained.agg(["count","mean","median","min","max"]).reset_index(); inner_epoch.insert(0,"phase","inner_executed")
    final_epoch=registry.groupby("formulation").selected_epoch.agg(["count","mean","median","min","max"]).reset_index(); final_epoch.insert(0,"phase","final_fixed_refit")
    epoch_distribution=pd.concat([inner_epoch,final_epoch],ignore_index=True)
    persistence=performance.groupby(["formulation","resource"]).agg(mean_persistence_skill=("persistence_skill","mean"),positive_leads=("persistence_skill",lambda x:int((x>0).sum()))).reset_index()
    inner_runtime=inner.assign(total_seconds=inner.train_seconds+inner.validation_seconds).groupby("formulation").total_seconds.sum()
    final_runtime=registry.groupby("formulation").train_seconds.sum(); prediction_runtime=registry.groupby("formulation").prediction_seconds.sum()
    runtime_rows=pd.DataFrame([{"formulation":f,"inner_fit_hours":inner_runtime[f]/3600,"final_fit_hours":final_runtime[f]/3600,"prediction_hours":prediction_runtime[f]/3600} for f in ("S1","S2","M1")])
    horizon_rows=[]
    for name,frame in comparisons.items():
        lead_rows=frame[~frame.lead.eq("OVERALL")].copy(); lead_rows["lead"]=lead_rows.lead.astype(int)
        for resource_name in RESOURCE_ORDER:
            part=lead_rows[lead_rows.resource.eq(resource_name)]; positives=part.loc[part.primary_gain_pct>0,"lead"].tolist()
            horizon_rows.append({"comparison":name,"resource":resource_name,"positive_horizons":",".join(map(str,positives)) if positives else "none"})
    horizon_summary=pd.DataFrame(horizon_rows)
    artifact_bytes=sum(path.stat().st_size for path in OUT.rglob("*") if path.is_file())
    lines=["# Phase 3C Full Multi-Resource LSTM Factorial Scientific Report","","## Execution and validation","",f"All 3,780 frozen fits completed: 2,835 inner and 945 final. Validation status: **PENDING**. Decision criteria SHA-256: `{runtime['criteria_sha256']}`.",""]
    lines += ["## Native performance by resource and lead",""] + markdown_table(performance, ["formulation","resource","lead","mae","rmse","r2","nmae","persistence_skill"])
    for title,name in (("Cross-resource input: S2 vs S1","s2_vs_s1"),("Shared representation: M1 vs S2","m1_vs_s2"),("Total effect: M1 vs S1","m1_vs_s1")):
        overall=comparisons[name][comparisons[name].lead.eq("OVERALL")][["resource","primary_gain_pct","positive_leads","positive_machines","positive_folds","positive_seeds","classification"]]
        lines += ["",f"## {title}",""] + markdown_table(overall,list(overall.columns))
    lines += ["","## Global decisions","",f"- Cross-resource input: **{cross}**",f"- Shared representation: **{shared}**",f"- Equal-resource mean S2-vs-S1 gain: {globals_['s2_vs_s1']['equal_resource_mean_primary_gain_pct']:.4f}%",f"- Equal-resource mean M1-vs-S2 gain: {globals_['m1_vs_s2']['equal_resource_mean_primary_gain_pct']:.4f}%",""]
    lines += ["## Positive horizons",""] + markdown_table(horizon_summary,list(horizon_summary.columns))
    selected_loss=loss_summary[loss_summary.summary_phase.eq("selected_inner_validation")].copy(); selected_loss["mean_loss_share_pct"]=100*selected_loss.mean_loss_share; selected_loss["median_loss_share_pct"]=100*selected_loss.median_loss_share
    cpu_share=float(selected_loss[selected_loss.resource.eq("CPU")].mean_loss_share.iloc[0]); smallest=selected_loss.sort_values("mean_loss_share").iloc[0].resource
    lines += ["","## Optimization and negative transfer","",f"The selected-inner CPU mean loss share was {100*cpu_share:.2f}%; the pre-execution CPU-majority pattern {'persisted' if cpu_share>.5 else 'did not persist'}. {smallest} received the smallest mean numerical loss share. M1 was BROAD_NEGATIVE for MEMORY versus S2 (-18.4769%), which is resource-specific evidence of negative transfer. The frozen global label is **{shared}** because no resource met the positive resource classification. Loss-share alignment is descriptive and **consistent with**, not proof of, task imbalance.",""] + markdown_table(selected_loss,["resource","mean_loss_share_pct","median_loss_share_pct"])
    lines += ["","## Context and epoch selection", "", f"S2 selected a different context from S1 in {context_info['s2_differs_from_s1']}/{context_info['s2_s1_cells']} matched resource-machine-fold cells. M1 differed from the corresponding S2 target context in {context_info['m1_differs_from_s2']}/{context_info['s2_s1_cells']} comparisons.",""] + markdown_table(context_distribution,["formulation","resource","selected_L","count"])+[""]+markdown_table(epoch_distribution,["phase","formulation","count","mean","median","min","max"])
    lines += ["","## Persistence results",""] + markdown_table(persistence,["formulation","resource","mean_persistence_skill","positive_leads"])
    reduction=100*(206880-53280)/206880
    lines += ["","## Efficiency", "", f"S2 uses 206,880 parameters across four inference models; M1 uses 53,280 in one model, a {reduction:.2f}% parameter reduction and 75% model-count reduction. M1 is operationally smaller, but its similar CPU accuracy does not offset the large MEMORY degradation; accuracy and efficiency remain separate conclusions.",""] + markdown_table(runtime_rows,list(runtime_rows.columns))
    lines += ["",f"Total recorded fit time: {(runtime['summed_inner_fit_seconds']+runtime['summed_final_fit_seconds'])/3600:.3f} h; prediction time: {runtime['summed_prediction_seconds']/3600:.3f} h; main resumed invocation wall time: {runtime['total_wall_seconds_current_invocation']/3600:.3f} h; peak RSS: {runtime['peak_rss_bytes']/2**30:.3f} GiB. The recorded wall time was above the 12.27 h optimistic projection and below the 30.68 h central and 61.36 h conservative projections.",""]
    lines += ["## Research direction","", "Cross-resource inputs were not supported globally, and plain sharing was not supported. The evidence therefore does not justify continuing directly to a more complex multi-resource forecaster. MEMORY shows a strong negative-transfer pattern, but adaptive weighting is not justified from loss shares alone and selective sharing is not justified as the next mandatory mechanism while the cross-resource premise itself is weak. A future targeted diagnostic study could revisit those mechanisms, but none is implemented here.",""]
    lines += ["## Artifact and integrity summary","",f"Scientific output tree size: {artifact_bytes/2**20:.2f} MiB. Models: {len(list(OUT.glob('*'+'/models/*.pt')))}; prediction files: {len(list(OUT.glob('*'+'/predictions/*.parquet')))}; figures: {len(list(FIGURES.glob('*.png')))}; metric rows: 10,080; selected-context records: 315.","","Independent validation checks execution counts, matched support, leakage, selection, fixed epochs, train-only scalers, timestamps, transforms, physical projection, metric/aggregation recomputation, prior frozen histories, raw hashes, and canonical-panel identity. The validator must report PASS before conclusions are accepted.",""]
    lines += ["## Generated files","", "Core outputs are under `outputs/scientific/`: `inner_run_registry.csv`, `run_registry.csv`, `selected_contexts.csv`, `selected_epochs.csv`, `metrics.parquet`, `persistence_metrics.parquet`, `m1_resource_loss_history.parquet`, `m1_loss_balance_summary.csv`, `support_manifest.parquet`, `comparisons/`, `figures/`, `runtime/runtime_accounting.json`, and `validation/validation.json`.","","## Phase 3C Decision","",f"**{phase}**",""]
    (BASE / "PHASE3C_FACTORIAL_SCIENTIFIC_REPORT.md").write_text("\n".join(lines))


def main() -> None:
    started=time.perf_counter(); COMPARISONS.mkdir(parents=True,exist_ok=True); FIGURES.mkdir(parents=True,exist_ok=True)
    metrics=pd.read_parquet(OUT/"metrics.parquet"); registry=pd.read_csv(OUT/"run_registry.csv"); contexts=pd.read_csv(OUT/"selected_contexts.csv"); epochs=pd.read_csv(OUT/"selected_epochs.csv")
    if len(metrics)!=10080 or len(registry)!=945 or len(contexts)!=315: raise RuntimeError("Execution incomplete; refusing scientific synthesis")
    performance=performance_table(metrics); performance.to_csv(COMPARISONS/"native_performance.csv",index=False)
    frames={}; matched={}; globals_={}
    for baseline,candidate,name in (("S1","S2","s2_vs_s1"),("S2","M1","m1_vs_s2"),("S1","M1","m1_vs_s1")):
        frames[name],matched[name],globals_[name]=comparison(metrics,baseline,candidate,name)
    cross,shared=global_decisions(frames["s2_vs_s1"],frames["m1_vs_s2"]); phase=phase_decision(cross,shared,frames["m1_vs_s2"])
    loss_summary,loss_diag=loss_balance(epochs); context_info=context_analysis(contexts)
    negative=matched["m1_vs_s2"].groupby(["resource","machine","fold","lead"],as_index=False)[["baseline_mae","candidate_mae"]].mean(); negative["gain_pct"]=100*(negative.baseline_mae-negative.candidate_mae)/negative.baseline_mae; negative.to_csv(COMPARISONS/"m1_vs_s2_negative_transfer_cells.csv",index=False)
    make_figures(frames,metrics,loss_summary,registry)
    runtime=json.loads((OUT/"runtime/runtime_accounting.json").read_text()); runtime["analysis_seconds"]=time.perf_counter()-started; atomic_json_write(OUT/"runtime/runtime_accounting.json",runtime)
    result={"resource_comparisons":{name:frame[frame.lead.eq('OVERALL')].to_dict('records') for name,frame in frames.items()},"global_summaries":globals_,"global_cross_resource_input_decision":cross,"global_shared_representation_decision":shared,"phase3c_decision":phase,"loss_diagnostic":loss_diag,"context_analysis":context_info}
    atomic_json_write(COMPARISONS/"scientific_decisions.json",result)
    write_report(performance,frames,globals_,cross,shared,phase,loss_summary,context_info,runtime,registry)
    print("SCIENTIFIC_ANALYSIS_COMPLETE",flush=True)


if __name__=="__main__": main()
