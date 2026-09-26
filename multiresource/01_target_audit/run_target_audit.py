#!/usr/bin/env python3
"""Phase 3A target/dynamics audit. No learned model is fit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from benchmark.src.splits import build_outer_folds
from benchmark.src.windows import FUTURE_LEADS, joint_eligible_origins


ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "multiresource/01_target_audit"
DEP = ROOT / "multiresource/02_dependency_design"
FIG = HERE / "figures"
PANEL_PATH = ROOT / "discovery/02_dependency_analysis/outputs/canonical_panel.parquet"
REGISTRY_PATH = ROOT / "discovery/02_dependency_analysis/outputs/canonical_signal_registry.csv"
MACHINES = tuple(f"machine{i:02d}" for i in range(1, 8))
LEADS = tuple(FUTURE_LEADS)
LAGS = (0, 1, 2, 4, 8, 16, 32, 64, 128)
RESOURCE_ORDER = ("CPU", "throughput", "memory", "disk")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_specs(machine: str) -> list[dict[str, str]]:
    return [
        {"resource_family":"CPU","candidate_name":"cpu_utilization","column":f"{machine}__cpu_utilization","transform":"identity","status":"PRIMARY_TARGET_CANDIDATE"},
        {"resource_family":"throughput","candidate_name":"network_tx","column":f"{machine}__network_tx","transform":"identity","status":"AUXILIARY_ONLY"},
        {"resource_family":"throughput","candidate_name":"network_rx","column":f"{machine}__network_rx","transform":"identity","status":"AUXILIARY_ONLY"},
        {"resource_family":"throughput","candidate_name":"throughput_total_raw","column":f"{machine}__throughput_total","transform":"identity","status":"SECONDARY_TARGET_CANDIDATE"},
        {"resource_family":"throughput","candidate_name":"throughput_total_log1p","column":f"{machine}__throughput_total","transform":"log1p","status":"PRIMARY_TARGET_CANDIDATE"},
        {"resource_family":"memory","candidate_name":"memory_used_level","column":f"{machine}__memory_used","transform":"identity","status":"PRIMARY_TARGET_CANDIDATE"},
        {"resource_family":"memory","candidate_name":"memory_used_change","column":f"{machine}__memory_used","transform":"difference","status":"SECONDARY_TARGET_CANDIDATE"},
        {"resource_family":"disk","candidate_name":"disk_used_level","column":f"{machine}__disk_used","transform":"identity","status":"AUXILIARY_ONLY"},
        {"resource_family":"disk","candidate_name":"disk_used_change","column":f"{machine}__disk_used","transform":"difference","status":"SECONDARY_TARGET_CANDIDATE"},
        {"resource_family":"disk","candidate_name":"disk_read_raw","column":f"{machine}__disk_read","transform":"identity","status":"REJECT_FOR_MULTI_TARGET"},
        {"resource_family":"disk","candidate_name":"disk_read_log1p","column":f"{machine}__disk_read","transform":"log1p","status":"REJECT_FOR_MULTI_TARGET"},
        {"resource_family":"disk","candidate_name":"disk_write_raw","column":f"{machine}__disk_write","transform":"identity","status":"SECONDARY_TARGET_CANDIDATE"},
        {"resource_family":"disk","candidate_name":"disk_write_log1p","column":f"{machine}__disk_write","transform":"log1p","status":"PRIMARY_TARGET_CANDIDATE"},
    ]


def represented(panel: pd.DataFrame, spec: dict[str, str]) -> pd.Series:
    values = panel[spec["column"]].astype(float)
    if spec["transform"] == "log1p":
        if (values.dropna() < 0).any():
            raise RuntimeError(f"negative value blocks log1p: {spec['column']}")
        return np.log1p(values)
    if spec["transform"] == "difference":
        result = values.diff()
        result[panel.segment_id.ne(panel.segment_id.shift())] = np.nan
        return result
    return values


def safe_skew(values: pd.Series) -> float:
    values = values.dropna()
    return float(values.skew()) if len(values) > 2 and values.nunique() > 1 else float("nan")


def design_region(panel: pd.DataFrame) -> tuple[np.ndarray, dict[str, object]]:
    first_tests = []
    per_machine = {}
    for machine in MACHINES:
        eligible = joint_eligible_origins(panel, machine, max_context=128, require_common_feature_intersection=True)
        fold = build_outer_folds(panel, eligible)[0]
        first = int(fold.test_indices[0]); first_tests.append(first)
        per_machine[machine] = {"first_test_origin_index": first, "first_test_origin_timestamp": str(panel.timestamp.iloc[first])}
    cutoff = min(first_tests)
    indices = np.arange(cutoff, dtype="<i8")
    timestamps = panel.timestamp.iloc[indices].astype("int64").to_numpy(dtype="<i8")
    segments = panel.segment_id.iloc[indices].to_numpy(dtype="<i8")
    digest = hashlib.sha256(indices.tobytes() + timestamps.tobytes() + segments.tobytes()).hexdigest()
    meta = {
        "name":"MULTIRESOURCE_DESIGN_REGION",
        "definition":"all canonical rows strictly before the earliest first outer-test origin across the seven frozen CPU benchmark machine splits",
        "start_index":0,"end_index_inclusive":cutoff-1,"row_count":cutoff,
        "start_timestamp":str(panel.timestamp.iloc[0]),"end_timestamp":str(panel.timestamp.iloc[cutoff-1]),
        "excluded_first_test_or_later_start_index":cutoff,
        "earliest_first_test_timestamp":str(panel.timestamp.iloc[cutoff]),
        "membership_sha256":digest,"hash_encoding":"little-endian int64 row indices + timestamp nanoseconds + segment ids",
        "frozen_machine_first_test_boundaries":per_machine,
        "canonical_panel_sha256":sha256(PANEL_PATH),
    }
    return indices, meta


def legal_origins(panel: pd.DataFrame, columns: list[str], limit: int | None = None) -> np.ndarray:
    n = len(panel) if limit is None else limit
    idx = np.arange(n)
    valid = (idx >= 127) & (idx + max(LEADS) < n)
    seg = panel.segment_id.to_numpy()
    valid &= seg[np.maximum(idx - 127, 0)] == seg[idx]
    valid &= seg[np.minimum(idx + max(LEADS), len(panel)-1)] == seg[idx]
    for column in columns:
        finite = np.isfinite(panel[column].to_numpy(dtype=float))
        history_ok = pd.Series(finite).rolling(128, min_periods=128).sum().to_numpy() == 128
        valid &= history_ok[:n]
        for lead in LEADS:
            future = np.zeros(n, dtype=bool)
            available = idx + lead < len(panel)
            future[available] = finite[idx[available] + lead]
            valid &= future
    return np.flatnonzero(valid)


def structural_registry(panel: pd.DataFrame, registry: pd.DataFrame) -> pd.DataFrame:
    by_name = registry.set_index("canonical_name")
    rows = []
    for machine in MACHINES:
        for spec in candidate_specs(machine):
            values = represented(panel, spec); finite = values[np.isfinite(values)]; source = by_name.loc[spec["column"]]
            q = finite.quantile([.01,.05,.25,.5,.75,.95,.99]) if len(finite) else pd.Series(dtype=float)
            rows.append({
                "resource_family":spec["resource_family"],"candidate_name":spec["candidate_name"],"machine":machine,
                "canonical_column":spec["column"],"raw_source_file":source.raw_dataset,
                "raw_source_columns":source.raw_column if pd.notna(source.raw_column) else source.component_columns,
                "units_if_known":source.unit_if_inferable,"semantic_description":source.metric,
                "aggregation_formula_if_any":source.transformation if spec["transform"]=="identity" else spec["transform"]+"("+spec["column"]+")",
                "representation":spec["transform"],"recommendation_status":spec["status"],
                "finite_count":int(len(finite)),"missing_count":int(values.isna().sum()),
                "zero_fraction":float((finite==0).mean()) if len(finite) else np.nan,
                "constant_flag":bool(finite.nunique()<=1),"near_constant_flag":bool(source.near_constant),
                "negative_value_count":int((finite<0).sum()),"min":float(finite.min()),"max":float(finite.max()),
                "median":float(q.get(.5,np.nan)),"mean":float(finite.mean()),"std":float(finite.std()),
                "q01":float(q.get(.01,np.nan)),"q05":float(q.get(.05,np.nan)),"q25":float(q.get(.25,np.nan)),
                "q75":float(q.get(.75,np.nan)),"q95":float(q.get(.95,np.nan)),"q99":float(q.get(.99,np.nan)),
                "duplicate_or_identity_notes":source.known_redundancy_relationship,
                "prior_quality_notes":source.quality_warnings,
            })
    return pd.DataFrame(rows)


def dynamics(panel: pd.DataFrame, design_n: int) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    rows=[]; changes=[]; persistence=[]
    sub=panel.iloc[:design_n]
    for machine in MACHINES:
      for spec in candidate_specs(machine):
        values=represented(sub,spec); finite=values.dropna(); diff=values.diff(); diff[sub.segment_id.ne(sub.segment_id.shift())]=np.nan; d=diff.dropna()
        q25,q75=finite.quantile([.25,.75]); mean=float(finite.mean()); std=float(finite.std())
        row={"resource_family":spec["resource_family"],"candidate_name":spec["candidate_name"],"machine":machine,"representation":spec["transform"],
          "mean":mean,"median":float(finite.median()),"std":std,"coefficient_of_variation":std/abs(mean) if mean else np.nan,
          "iqr":float(q75-q25),"skewness":safe_skew(finite),"zero_fraction":float((finite==0).mean()),"unique_value_count":int(finite.nunique()),
          "first_difference_std":float(d.std()),"first_difference_median_abs":float(d.abs().median()),"unchanged_fraction":float((d==0).mean())}
        for lag in LAGS[1:]:
          same=sub.segment_id.eq(sub.segment_id.shift(lag)); row[f"autocorrelation_lag_{lag}"]=float(values[same].corr(values.shift(lag)[same]))
        rows.append(row)
        origins=legal_origins(sub,[spec["column"]],design_n)
        rep_full=represented(sub,spec).to_numpy(dtype=float)
        iqr=float(q75-q25)
        for lead in LEADS:
          delta=rep_full[origins+lead]-rep_full[origins]; absd=np.abs(delta)
          changes.append({"resource_family":spec["resource_family"],"candidate_name":spec["candidate_name"],"machine":machine,"lead":lead,"n":len(delta),
            "change_mean":float(np.mean(delta)),"change_variance":float(np.var(delta)),"change_skewness":float(pd.Series(delta).skew()),
            "absolute_change_mean":float(np.mean(absd)),"absolute_change_median":float(np.median(absd)),"absolute_change_q90":float(np.quantile(absd,.9)),"absolute_change_q95":float(np.quantile(absd,.95)),"absolute_change_q99":float(np.quantile(absd,.99)),"zero_change_fraction":float(np.mean(delta==0))})
          truth=rep_full[origins+lead]; pred=rep_full[origins]; err=truth-pred; mae=float(np.mean(np.abs(err))); rmse=float(np.sqrt(np.mean(err**2))); denom=float(np.sum((truth-truth.mean())**2)); r2=1-float(np.sum(err**2))/denom if denom else np.nan
          persistence.append({"resource_family":spec["resource_family"],"candidate_name":spec["candidate_name"],"machine":machine,"lead":lead,"n":len(err),"mae":mae,"rmse":rmse,"r2":r2,"training_region_iqr":iqr,"mae_over_iqr":mae/iqr if iqr else np.nan})
    return pd.DataFrame(rows),pd.DataFrame(changes),pd.DataFrame(persistence)


def support_audit(panel: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    combinations={
      "CPU-only":lambda m:[f"{m}__cpu_utilization"],
      "CPU+throughput":lambda m:[f"{m}__cpu_utilization",f"{m}__throughput_total"],
      "CPU+throughput+memory":lambda m:[f"{m}__cpu_utilization",f"{m}__throughput_total",f"{m}__memory_used"],
      "four-resource+disk-used":lambda m:[f"{m}__cpu_utilization",f"{m}__throughput_total",f"{m}__memory_used",f"{m}__disk_used"],
      "four-resource+disk-read":lambda m:[f"{m}__cpu_utilization",f"{m}__throughput_total",f"{m}__memory_used",f"{m}__disk_read"],
      "four-resource+disk-write":lambda m:[f"{m}__cpu_utilization",f"{m}__throughput_total",f"{m}__memory_used",f"{m}__disk_write"],
    }
    for machine in MACHINES:
      frozen_folds=build_outer_folds(panel,joint_eligible_origins(panel,machine,max_context=128,require_common_feature_intersection=True))
      for name,builder in combinations.items():
        origins=legal_origins(panel,builder(machine)); rows.append({"combination":name,"machine":machine,"scope":"overall","scope_id":"ALL","legal_origin_count":len(origins)})
        for segment in sorted(panel.segment_id.unique()): rows.append({"combination":name,"machine":machine,"scope":"segment","scope_id":str(segment),"legal_origin_count":int(np.sum(panel.segment_id.iloc[origins].to_numpy()==segment))})
        origin_set=set(origins.tolist())
        for fold in frozen_folds: rows.append({"combination":name,"machine":machine,"scope":"existing_outer_fold","scope_id":str(fold.fold),"legal_origin_count":len(origin_set.intersection(fold.test_indices.tolist()))})
    return pd.DataFrame(rows)


def dependency_audit(panel: pd.DataFrame, design_n: int) -> pd.DataFrame:
    rows=[]; sub=panel.iloc[:design_n].copy()
    for machine in MACHINES:
      level={"CPU":sub[f"{machine}__cpu_utilization"].astype(float),"throughput":np.log1p(sub[f"{machine}__throughput_total"].astype(float)),"memory":sub[f"{machine}__memory_used"].astype(float),"disk":np.log1p(sub[f"{machine}__disk_write"].astype(float))}
      modes={"level":level,"difference":{k:v.diff().where(sub.segment_id.eq(sub.segment_id.shift())) for k,v in level.items()}}
      for mode,data in modes.items():
       for target in RESOURCE_ORDER:
        for predictor in RESOURCE_ORDER:
         if target==predictor: continue
         for lag in LAGS:
          same=sub.segment_id.eq(sub.segment_id.shift(lag)); frame=pd.concat([data[target],data[predictor].shift(lag)],axis=1); frame=frame[same].dropna()
          rho=float(frame.iloc[:,0].rank().corr(frame.iloc[:,1].rank())) if len(frame)>2 else np.nan
          rows.append({"machine":machine,"mode":mode,"target_resource":target,"predictor_resource":predictor,"predictor_lag":lag,"n":len(frame),"spearman_rho":rho})
    return pd.DataFrame(rows)


def scale_audit(panel: pd.DataFrame, design_n: int) -> pd.DataFrame:
    rows=[]; sub=panel.iloc[:design_n]
    definitions={"CPU":("cpu_utilization","identity"),"throughput":("throughput_total","log1p"),"memory":("memory_used","identity"),"disk":("disk_write","log1p")}
    for machine in MACHINES:
      for resource,(suffix,transform) in definitions.items():
        raw=sub[f"{machine}__{suffix}"].astype(float).dropna(); represented_values=np.log1p(raw) if transform=="log1p" else raw
        med=float(represented_values.median()); iqr=float(represented_values.quantile(.75)-represented_values.quantile(.25)); std=float(represented_values.std())
        rows.append({"machine":machine,"resource_family":resource,"selected_representation":transform,"raw_median":float(raw.median()),"raw_iqr":float(raw.quantile(.75)-raw.quantile(.25)),"raw_std":float(raw.std()),"represented_median":med,"represented_iqr":iqr,"represented_std":std,"raw_mse_scale_proxy_variance":float(raw.var()),"recommended_training_scaling":"train-only robust median/IQR after resource transform"})
    return pd.DataFrame(rows)


def figures(panel,dynamics_frame,persistence,support,dependencies,design_n):
    FIG.mkdir(parents=True,exist_ok=True); machine="machine01"; sample=panel.iloc[:min(design_n,1600)]
    series={"CPU":sample[f"{machine}__cpu_utilization"],"throughput log1p":np.log1p(sample[f"{machine}__throughput_total"]),"memory":sample[f"{machine}__memory_used"],"disk-write log1p":np.log1p(sample[f"{machine}__disk_write"])}
    plt.figure(figsize=(11,6))
    for name,v in series.items(): plt.plot((v-v.median())/(v.quantile(.75)-v.quantile(.25)),label=name,alpha=.8)
    plt.xlabel("Design-region row");plt.ylabel("Robust normalized value");plt.title("Machine01 selected-resource histories");plt.legend();plt.tight_layout();plt.savefig(FIG/"01_normalized_time_series_machine01.png",dpi=150);plt.close()
    chosen=dynamics_frame[dynamics_frame.candidate_name.isin(["cpu_utilization","throughput_total_raw","throughput_total_log1p","memory_used_level","disk_used_level","disk_read_log1p","disk_write_log1p"])]
    pivot=chosen.pivot(index="machine",columns="candidate_name",values="skewness");plt.figure(figsize=(11,5));plt.imshow(pivot.to_numpy(),aspect="auto",cmap="coolwarm");plt.colorbar(label="skewness");plt.xticks(range(len(pivot.columns)),pivot.columns,rotation=35,ha="right");plt.yticks(range(len(pivot.index)),pivot.index);plt.title("Design-region distribution skewness");plt.tight_layout();plt.savefig(FIG/"02_distribution_skewness.png",dpi=150);plt.close()
    selected={"CPU":"cpu_utilization","throughput":"throughput_total_log1p","memory":"memory_used_level","disk":"disk_write_log1p"};plt.figure(figsize=(9,5))
    for resource,candidate in selected.items():
      p=persistence[persistence.candidate_name.eq(candidate)].groupby("lead").mae_over_iqr.median();plt.plot(p.index,p.values,"o-",label=resource)
    plt.xscale("log",base=2);plt.xlabel("Real future lead");plt.ylabel("Median persistence MAE / design IQR");plt.title("Scale-normalized persistence difficulty");plt.legend();plt.tight_layout();plt.savefig(FIG/"03_persistence_difficulty.png",dpi=150);plt.close()
    d=dependencies[dependencies["mode"].eq("level")]; matrix=d.groupby(["target_resource","predictor_resource"]).spearman_rho.apply(lambda x: x.abs().max()).unstack().reindex(index=RESOURCE_ORDER,columns=RESOURCE_ORDER);plt.figure(figsize=(7,6));plt.imshow(matrix.to_numpy(dtype=float),vmin=0,vmax=1,cmap="viridis");plt.colorbar(label="max |Spearman| over machines/lags");plt.xticks(range(4),RESOURCE_ORDER,rotation=30);plt.yticks(range(4),RESOURCE_ORDER);plt.title("Lagged cross-resource dependency envelope");plt.tight_layout();plt.savefig(FIG/"04_lagged_dependency_matrix.png",dpi=150);plt.close()
    s=support[support.scope.eq("overall")].pivot(index="machine",columns="combination",values="legal_origin_count");s.plot(kind="bar",figsize=(12,6));plt.ylabel("Legal origins");plt.title("Joint common support by machine");plt.tight_layout();plt.savefig(FIG/"05_joint_support_by_machine.png",dpi=150);plt.close()
    lc=dynamics_frame[dynamics_frame.candidate_name.isin(["memory_used_level","disk_used_level"])].copy();lc["diff_std_over_iqr"]=lc.first_difference_std/lc.iqr; p=lc.pivot(index="machine",columns="candidate_name",values="diff_std_over_iqr");p.plot(kind="bar",figsize=(10,5));plt.ylabel("First-difference std / level IQR");plt.title("Level/change variability for persistent targets");plt.tight_layout();plt.savefig(FIG/"06_level_change_variability.png",dpi=150);plt.close()


def main():
    HERE.mkdir(parents=True,exist_ok=True);DEP.mkdir(parents=True,exist_ok=True);FIG.mkdir(parents=True,exist_ok=True)
    panel=pd.read_parquet(PANEL_PATH);panel["timestamp"]=pd.to_datetime(panel.timestamp);registry=pd.read_csv(REGISTRY_PATH)
    indices,meta=design_region(panel); region_path=HERE/"MULTIRESOURCE_DESIGN_REGION.json";region_path.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n");(HERE/"MULTIRESOURCE_DESIGN_REGION_SHA256.txt").write_text(sha256(region_path)+"  MULTIRESOURCE_DESIGN_REGION.json\n")
    candidates=structural_registry(panel,registry);candidates.to_csv(HERE/"TARGET_CANDIDATE_REGISTRY.csv",index=False)
    dyn,changes,persistence=dynamics(panel,len(indices));dyn.to_csv(HERE/"TARGET_DYNAMICS.csv",index=False);changes.to_csv(HERE/"FUTURE_CHANGE_DISTRIBUTIONS.csv",index=False);persistence.to_csv(HERE/"PERSISTENCE_DIFFICULTY.csv",index=False)
    persistence.groupby(["resource_family","candidate_name","lead"],as_index=False).agg(machine_median_mae_over_iqr=("mae_over_iqr","median"),machine_min_mae_over_iqr=("mae_over_iqr","min"),machine_max_mae_over_iqr=("mae_over_iqr","max"),machine_median_r2=("r2","median"),total_n=("n","sum")).to_csv(HERE/"PERSISTENCE_DIFFICULTY_SUMMARY.csv",index=False)
    level_change=dyn[dyn.candidate_name.isin(["memory_used_level","memory_used_change","disk_used_level","disk_used_change","disk_read_log1p","disk_write_log1p"])];level_change.to_csv(HERE/"LEVEL_CHANGE_AUDIT.csv",index=False)
    support=support_audit(panel);support.to_csv(HERE/"JOINT_SUPPORT_AUDIT.csv",index=False)
    support[support.scope.eq("overall")].groupby("combination",as_index=False).agg(machine_min_legal_origins=("legal_origin_count","min"),machine_median_legal_origins=("legal_origin_count","median"),machine_max_legal_origins=("legal_origin_count","max"),total_legal_origins=("legal_origin_count","sum")).to_csv(HERE/"JOINT_SUPPORT_SUMMARY.csv",index=False)
    dependencies=dependency_audit(panel,len(indices));dependencies.to_csv(DEP/"LAGGED_SPEARMAN_DEPENDENCIES.csv",index=False)
    dependencies.groupby(["mode","target_resource","predictor_resource","predictor_lag"],as_index=False).agg(machine_median_spearman=("spearman_rho","median"),machine_min_spearman=("spearman_rho","min"),machine_max_spearman=("spearman_rho","max"),positive_machine_fraction=("spearman_rho",lambda x:float((x>0).mean())),total_n=("n","sum")).to_csv(DEP/"DEPENDENCY_SUMMARY.csv",index=False)
    scale=scale_audit(panel,len(indices));scale.to_csv(HERE/"TARGET_SCALE_AUDIT.csv",index=False)
    figures(panel,dyn,persistence,support,dependencies,len(indices))
    print(json.dumps({"design_region":meta,"candidate_rows":len(candidates),"dynamics_rows":len(dyn),"persistence_rows":len(persistence),"support_rows":len(support),"dependency_rows":len(dependencies)},indent=2))

if __name__=="__main__": main()
