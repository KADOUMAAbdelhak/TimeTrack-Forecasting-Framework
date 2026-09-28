#!/usr/bin/env python3
"""Independent Phase 3C execution, leakage, metric, and integrity validation."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark.neural_v2.validate_dlinear_scientific import phase2a_hashes, sha256, verify_inventory
from benchmark.src.data import PANEL_PATH, verify_raw_hashes
from src.data import FUTURE_LEADS, RESOURCE_ORDER, load_panel, sample_set_hash, target_columns
from src.metrics import per_lead_metrics
from src.selection import SelectionRow, select_context
from src.splits import build_factorial_folds
from src.transforms import fit_partition_scaler


ROOT=Path(__file__).resolve().parents[2]; BASE=Path(__file__).resolve().parent; OUT=BASE/"outputs/scientific"; REPORT=BASE/"PHASE3C_FACTORIAL_SCIENTIFIC_REPORT.md"
CONFIG_HASH="fe985007ebd72417dcab8e8a1851c358d3d9a3da26f372595ac7ff6b499eedd6"; CRITERIA_HASH="3157a233c3c76b126ff939f7e0588c9c2d21f98bb7d3e6355f13a5d1bc470d57"; PANEL_HASH="c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a"


def digest(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()


def main()->None:
    started=time.perf_counter(); failures=[]; structural={key:0 for key in ("support_hash_mismatch","matched_y_mismatch","segment_history_crossing","segment_target_crossing","inner_target_time_leakage","outer_target_time_leakage","target_timestamp_mismatch","target_value_mismatch","inversion_mismatch","projection_mismatch","metric_mismatch","selection_mismatch","epoch_mismatch","artifact_hash_mismatch")}; maxima={"target_abs":0.0,"inversion_abs":0.0,"metric_abs":0.0,"aggregation_abs":0.0}
    panel=load_panel(); timestamps=panel.timestamp.to_numpy(); segments=panel.segment_id.to_numpy(); values={m:panel.loc[:,list(target_columns(m))].to_numpy(float) for m in [f"machine{i:02d}" for i in range(1,8)]}
    inner_paths=sorted((OUT/"runtime/completions/inner").glob("*.json")); final_paths=sorted((OUT/"runtime/completions/final").glob("*.json")); inner=[json.loads(p.read_text()) for p in inner_paths]; final=[json.loads(p.read_text()) for p in final_paths]
    counts={f:{"inner":sum(r["identity"]["formulation"]==f for r in inner),"final":sum(r["identity"]["formulation"]==f for r in final)} for f in ("S1","S2","M1")}
    expected={"S1":{"inner":1260,"final":420},"S2":{"inner":1260,"final":420},"M1":{"inner":315,"final":105}}
    if counts!=expected: failures.append("execution counts")
    metrics=pd.read_parquet(OUT/"metrics.parquet"); registry=pd.read_csv(OUT/"run_registry.csv"); contexts=pd.read_csv(OUT/"selected_contexts.csv"); epochs=pd.read_csv(OUT/"selected_epochs.csv"); support=pd.read_parquet(OUT/"support_manifest.parquet")
    if len(metrics)!=10080 or len(registry)!=945 or len(contexts)!=315 or len(epochs)!=945 or len(support)!=105: failures.append("summary counts")
    if metrics.groupby("formulation").size().to_dict()!={"M1":3360,"S1":3360,"S2":3360}: failures.append("metric formulation counts")
    # Frozen support, purges, and segment safety.
    for machine in [f"machine{i:02d}" for i in range(1,8)]:
        by_length={length:build_factorial_folds(panel,machine,length) for length in (32,64,128)}
        for fold_index in range(5):
            ref=by_length[128][fold_index]
            for length in (32,64,128):
                observed=by_length[length][fold_index]
                structural["support_hash_mismatch"]+=sum(ref.hashes[k]!=observed.hashes[k] for k in ref.hashes)
            structural["inner_target_time_leakage"]+=int(timestamps[ref.inner_train+128].max()>=timestamps[ref.inner_validation[0]])
            structural["outer_target_time_leakage"]+=int(timestamps[ref.outer_train+128].max()>=timestamps[ref.outer_test[0]])
    # Recompute context and per-seed epoch selection from inner-only records.
    lookup={(r["identity"]["formulation"],r["identity"]["resource"],r["identity"]["machine"],r["identity"]["fold"],r["identity"]["L"],r["identity"]["seed"]):r for r in inner}
    context_index=contexts.set_index(["formulation","resource","machine","fold"],drop=False); epoch_index=epochs.set_index(["formulation","resource","machine","fold","seed"],drop=False)
    for formulation in ("S1","S2","M1"):
        targets=RESOURCE_ORDER if formulation!="M1" else (None,)
        for target in targets:
            target_key=np.nan if target is None else target
            for machine in [f"machine{i:02d}" for i in range(1,8)]:
                for fold in range(1,6):
                    rows=[]
                    for length in (32,64,128):
                        for seed in (0,1,2):
                            record=lookup[(formulation,target,machine,fold,length,seed)]; rows.append(SelectionRow(formulation,length,seed,np.asarray(record["validation_nmae"]),int(record["best_epoch"])))
                    selected=select_context(rows,formulation)
                    stored=contexts[(contexts.formulation==formulation)&(contexts.machine==machine)&(contexts.fold==fold)&(contexts.resource.isna() if target is None else contexts.resource.eq(target))].iloc[0]
                    structural["selection_mismatch"]+=int(int(stored.selected_L)!=selected.context_length)
                    for seed,epoch in selected.best_epoch_by_seed.items():
                        saved=epochs[(epochs.formulation==formulation)&(epochs.machine==machine)&(epochs.fold==fold)&(epochs.seed==seed)&(epochs.resource.isna() if target is None else epochs.resource.eq(target))].iloc[0]
                        structural["epoch_mismatch"]+=int(int(saved.selected_epoch)!=epoch)
    inner_scalers={}
    for record in inner:
        ident=record["identity"]; key=(ident["machine"],ident["fold"],ident["L"])
        if key not in inner_scalers:
            frozen_fold=build_factorial_folds(panel,key[0],int(key[2]))[int(key[1])-1]
            inner_scalers[key]=fit_partition_scaler(panel,key[0],frozen_fold.inner_train,int(key[2])).metadata()
        structural["support_hash_mismatch"]+=int(record["scaler_metadata"]!=inner_scalers[key])
    metric_index=metrics.set_index(["run_id","resource","lead"]); truth_signatures={}; final_scalers={}
    for record in final:
        ident=record["identity"]; model=ROOT/record["model_path"]; prediction=ROOT/record["prediction_path"]
        structural["artifact_hash_mismatch"]+=int(not model.exists() or digest(model)!=record["model_sha256"])+int(not prediction.exists() or digest(prediction)!=record["prediction_sha256"])
        if not prediction.exists(): continue
        frame=pd.read_parquet(prediction); machine=ident["machine"]; length=int(ident["L"]); origin=frame.origin_index.to_numpy(np.int64); lead=frame.lead.to_numpy(np.int64); target_index=frame.target_index.to_numpy(np.int64)
        structural["target_timestamp_mismatch"]+=int(not np.array_equal(target_index,origin+lead))+int(not np.array_equal(frame.target_timestamp.to_numpy(),timestamps[target_index]))
        histories=np.unique(origin)[:,None]-np.arange(length-1,-1,-1); unique_origin=np.unique(origin); target_grid=unique_origin[:,None]+np.asarray(FUTURE_LEADS); structural["segment_history_crossing"]+=int(np.sum(~np.all(segments[histories]==segments[unique_origin,None],axis=1))); structural["segment_target_crossing"]+=int(np.sum(~np.all(segments[target_grid]==segments[unique_origin,None],axis=1))); structural["support_hash_mismatch"]+=int(sample_set_hash(unique_origin)!=record["outer_test_hash"])
        scaler_key=(machine,ident["fold"],length)
        if scaler_key not in final_scalers:
            frozen_fold=build_factorial_folds(panel,machine,length)[int(ident["fold"])-1]; final_scalers[scaler_key]=fit_partition_scaler(panel,machine,frozen_fold.outer_train,length).metadata()
        structural["support_hash_mismatch"]+=int(record["scaler_metadata"]!=final_scalers[scaler_key])
        for resource_name,part in frame.groupby("resource",sort=False):
            index=RESOURCE_ORDER.index(resource_name); expected=values[machine][target_index[part.index],index].astype(np.float32).astype(float); actual=part.y_true.to_numpy(float); maxima["target_abs"]=max(maxima["target_abs"],float(np.max(np.abs(expected-actual)))); structural["target_value_mismatch"]+=int(not np.allclose(expected,actual,rtol=0,atol=0))
            transformed=part.y_pred_scaled.to_numpy(float)*record["scaler_metadata"][resource_name]["transformed_iqr"]+record["scaler_metadata"][resource_name]["transformed_median"]
            unclipped=np.expm1(transformed) if resource_name in {"THROUGHPUT","DISK_WRITE"} else transformed; projected=np.maximum(0,unclipped) if resource_name in {"THROUGHPUT","DISK_WRITE"} else unclipped
            maxima["inversion_abs"]=max(maxima["inversion_abs"],float(np.max(np.abs(unclipped-part.y_pred_unclipped.to_numpy(float)))),float(np.max(np.abs(projected-part.y_pred.to_numpy(float)))))
            structural["projection_mismatch"]+=int(resource_name in {"THROUGHPUT","DISK_WRITE"} and (part.y_pred<0).any())
            pivot_true=part.pivot(index="origin_index",columns="lead",values="y_true").reindex(columns=FUTURE_LEADS); pivot_pred=part.pivot(index="origin_index",columns="lead",values="y_pred").reindex(columns=FUTURE_LEADS)
            calculated=per_lead_metrics(pivot_true.to_numpy(),pivot_pred.to_numpy(),record["scaler_metadata"][resource_name]["native_iqr"])
            for pos,lead_value in enumerate(FUTURE_LEADS):
                saved=metric_index.loc[(ident["run_id"],resource_name,lead_value)]; difference=max(abs(float(saved.mae)-calculated["mae"][pos]),abs(float(saved.rmse)-calculated["rmse"][pos]),abs(float(saved.r2)-calculated["r2"][pos]),abs(float(saved.nmae)-calculated["nmae"][pos])); maxima["metric_abs"]=max(maxima["metric_abs"],difference)
            signature_frame=part.sort_values(["sample_id","lead"])[["sample_id","lead","target_timestamp","y_true"]]; signature=hashlib.sha256(pd.util.hash_pandas_object(signature_frame,index=False).values.tobytes()).hexdigest(); truth_signatures[(ident["formulation"],machine,ident["fold"],ident["seed"],resource_name)]=signature
    for machine in [f"machine{i:02d}" for i in range(1,8)]:
        for fold in range(1,6):
            for seed in (0,1,2):
                for resource_name in RESOURCE_ORDER:
                    signs=[truth_signatures[(formulation,machine,fold,seed,resource_name)] for formulation in ("S1","S2","M1")]
                    structural["matched_y_mismatch"]+=int(len(set(signs))!=1)
    if maxima["target_abs"]!=0 or maxima["inversion_abs"]>1e-6 or maxima["metric_abs"]>1e-6: failures.append("prediction/metric recomputation")
    # Independently recompute the primary lead aggregation.
    for baseline,candidate,name in (("S1","S2","s2_vs_s1"),("S2","M1","m1_vs_s2"),("S1","M1","m1_vs_s1")):
        keys=["resource","machine","fold","seed","lead"]; left=metrics[metrics.formulation.eq(baseline)][keys+["mae"]].rename(columns={"mae":"b"}); right=metrics[metrics.formulation.eq(candidate)][keys+["mae"]].rename(columns={"mae":"c"}); merged=left.merge(right,on=keys); cell=merged.groupby(["resource","machine","fold","lead"],as_index=False)[["b","c"]].mean(); recomputed=cell.groupby(["resource","lead"],as_index=False)[["b","c"]].mean(); recomputed["gain"]=100*(recomputed.b-recomputed.c)/recomputed.b
        saved=pd.read_csv(OUT/f"comparisons/{name}.csv",dtype={"lead":str}); saved=saved[~saved.lead.eq("OVERALL")].copy(); saved["lead"]=saved.lead.astype(int); joined=recomputed.merge(saved,on=["resource","lead"]); maxima["aggregation_abs"]=max(maxima["aggregation_abs"],float(np.max(np.abs(joined.gain-joined.primary_gain_pct))))
    if maxima["aggregation_abs"]>1e-10: failures.append("aggregation recomputation")
    if any(structural.values()): failures.append("structural validation")
    figures=list((OUT/"figures").glob("*.png"));
    if len(figures)!=8 or any(p.stat().st_size==0 for p in figures): failures.append("figure count")
    histories={"phase3a":(ROOT/"multiresource/PHASE3A_ARTIFACT_SHA256.csv",25),"neural_v2":(ROOT/"benchmark/neural_v2/NEURAL_V2_ARTIFACT_SHA256.csv",29),"dlinear":(ROOT/"benchmark/neural_v2/DLINEAR_SCIENTIFIC_ARTIFACT_SHA256.csv",1347),"lstm":(ROOT/"benchmark/neural_v2/LSTM_SCIENTIFIC_ARTIFACT_SHA256.csv",1349),"patchtst":(ROOT/"benchmark/neural_v2/PATCHTST_SCIENTIFIC_ARTIFACT_SHA256.csv",1352),"original":(ROOT/"benchmark/phase2b1_original/HEAVY_ARTIFACT_SHA256.csv",632),"corrected":(ROOT/"benchmark/phase2b1_corrected/CORRECTION_ARTIFACT_SHA256.csv",1070)}
    frozen={};
    for name,(path,expected) in histories.items(): count,bad=verify_inventory(path); frozen[name]={"count":count,"expected":expected,"pass":count==expected and not bad}; failures.extend([f"frozen {name}"] if not frozen[name]["pass"] else [])
    p2count,p2bad=phase2a_hashes(); raw=verify_raw_hashes(); canonical=sha256(PANEL_PATH); phase3b_inventory=digest(BASE/"PHASE3B_ARTIFACT_SHA256.csv")=="7e4d5b7dd858ecb79dab0ea3355fad0b029e34a18cbfb15b25d114e1886ead65"
    if p2count!=33 or p2bad or not raw or canonical!=PANEL_HASH or not phase3b_inventory: failures.append("prior provenance")
    result={"status":"PASS" if not failures else "FAIL","failures":failures,"counts":counts,"metric_rows":len(metrics),"selected_contexts":len(contexts),"support_records":len(support),"structural":structural,"maxima":maxima,"figure_count":len(figures),"frozen_history":frozen,"phase2a_count":p2count,"raw_hashes_unchanged":raw,"canonical_panel_sha256":canonical,"phase3b_inventory_unchanged":phase3b_inventory,"criteria_sha256":CRITERIA_HASH,"validation_seconds":time.perf_counter()-started}
    atomic_path=OUT/"validation/validation.json"; atomic_path.parent.mkdir(parents=True,exist_ok=True); atomic_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    if not failures:
        runtime_path=OUT/"runtime/runtime_accounting.json"; runtime=json.loads(runtime_path.read_text()); runtime["status"]="VALIDATED_PASS"; runtime["validation_seconds"]=result["validation_seconds"]; runtime["validation_path"]=str(atomic_path.relative_to(ROOT)); runtime_path.write_text(json.dumps(runtime,indent=2,sort_keys=True)+"\n")
        report=REPORT.read_text(); report=report.replace("Validation status: **PENDING**.","Validation status: **PASS** (zero structural failures; metrics and aggregation independently reproduced).")
        REPORT.write_text(report)
    print(json.dumps(result,indent=2,sort_keys=True))
    if failures: raise RuntimeError("Phase 3C validation failed")


if __name__=="__main__": main()
