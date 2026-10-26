"""Read-only Stage18C1 diagnostics. Never imports a model or executes fit/predict.

Writes only its evidence directory and the explicitly requested synthesis report.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import subprocess
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
REPORT=ROOT/"review_revision/stage18c1_final_robustness_synthesis.md"
EXP=ROOT/"review_revision/experiments"
BLOCKS=["TimeTrack","fastStorage","Rnd","Materna-T1","Materna-T2","Materna-T3"]
RESOURCES=["CPU","THROUGHPUT","MEMORY","DISK_WRITE"]
FROZEN={"TimeTrack":"multiresource/04_lstm_factorial/outputs/scientific",
        **{b:f"independent_validation/05_bitbrains_factorial/outputs/scientific_v2/{b}" for b in BLOCKS[1:3]},
        **{b:f"independent_validation/06_materna_replication/outputs/scientific_v1/{b}" for b in BLOCKS[3:]}}
PROTECTED=["multiresource/04_lstm_factorial","independent_validation/05_bitbrains_factorial",
 "independent_validation/06_materna_replication","manuscript/jss","benchmark/src",
 *[f"review_revision/experiments/{s}" for s in ("s2_common_context","s2_common_context_predecessor_stage18b1r","m1_capacity_matched","ar_arx_baseline","ar_arx_baseline_predecessor_stage18b3")],
 "review_revision/stage18a1_diagnostic_audit.md"]

def need(condition,message):
    if not condition: raise RuntimeError("STAGE_18C1_EVIDENCE_CONFLICT: "+message)
def read(p): return json.loads(Path(p).read_text())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b""):h.update(chunk)
    return h.hexdigest()
def dest(p):
    p=Path(p).resolve();need(p==REPORT or p.is_relative_to(OUT),f"Forbidden write {p}")
    p.parent.mkdir(parents=True,exist_ok=True);return p
def write(p,v):dest(p).write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n")
def csv(name,frame):frame.to_csv(dest(OUT/name),index=False,float_format="%.17g")
def git(*args):return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()
def refs():
    return {k:git("rev-parse",v) for k,v in {"HEAD":"HEAD","main":"refs/heads/main","paper_jss":"refs/heads/paper/jss","scientific_tag_object":"refs/tags/phase4d-materna-final-scientific-freeze-v1","scientific_tag_target":"phase4d-materna-final-scientific-freeze-v1^{}"}.items()}
def verify_git():
    need(git("branch","--show-current")=="paper/jss-review-revision","Branch changed")
    need(git("rev-parse","HEAD")=="f6936cd111d911e40ec2725a18fdfc53768d9ccf","HEAD changed")
    need(not git("diff","--name-only") and not git("diff","--cached","--name-only"),"Tracked modifications")
def protected_files():
    for rel in PROTECTED:
        p=ROOT/rel
        if p.is_file():yield p
        else:
            for base,dirs,files in os.walk(p):
                dirs.sort()
                for name in sorted(files):yield Path(base)/name

def baseline():
    verify_git();need(not (OUT/"preservation_before.jsonl").exists(),"Baseline already exists")
    prior=EXP/"ar_arx_baseline/provenance/preservation_before.jsonl"
    need(sha(prior)==read(EXP/"ar_arx_baseline/provenance/preservation_baseline.json")["inventory_sha256"],"Prior preservation anchor changed")
    with prior.open() as f:expected={v["path"]:v["sha256"] for v in map(json.loads,f)}
    inv=read(EXP/"ar_arx_baseline/output_sha256_inventory.json")
    for v in inv["files"]:expected["review_revision/experiments/ar_arx_baseline/"+v["path"]]=v["sha256"]
    snapshot=read(EXP/"ar_arx_baseline/recovery/predecessor_snapshot.json")
    for v in snapshot["files"]:expected["review_revision/experiments/ar_arx_baseline_predecessor_stage18b3/"+v["path"]]=v["sha256"]
    count=0
    with dest(OUT/"preservation_before.jsonl").open("x") as f:
        for p in protected_files():
            rel=str(p.relative_to(ROOT));h=sha(p)
            if rel in expected:need(expected.pop(rel)==h,"Historical hash mismatch "+rel)
            f.write(json.dumps({"path":rel,"bytes":p.stat().st_size,"sha256":h},sort_keys=True)+"\n");count+=1
            if count%100000==0:print("BASELINE_VERIFIED",count,flush=True)
    need(not expected,"Previously inventoried file missing")
    write(OUT/"preservation_baseline.json",{"files":count,"refs":refs(),"inventory_sha256":sha(OUT/"preservation_before.jsonl"),"historical_inventories_verified":True})
    print("BASELINE_PASS",count,flush=True)

def preserve():
    verify_git();meta=read(OUT/"preservation_baseline.json")
    need(refs()==meta["refs"] and sha(OUT/"preservation_before.jsonl")==meta["inventory_sha256"],"Baseline/refs changed")
    with (OUT/"preservation_before.jsonl").open() as f:expected={v["path"]:v for v in map(json.loads,f)}
    count=0
    for p in protected_files():
        rel=str(p.relative_to(ROOT));v={"path":rel,"bytes":p.stat().st_size,"sha256":sha(p)}
        need(expected.pop(rel,None)==v,"Input modified/added "+rel);count+=1
        if count%100000==0:print("PRESERVATION_VERIFIED",count,flush=True)
    need(not expected,"Input removed")
    write(OUT/"preservation_after.json",{"status":"PASS","files":count,"modified":0,"added":0,"removed":0,"refs":refs(),"training_calls":0,"inference_calls":0,"manuscript_modifications":0,"frozen_posthoc_modifications":0})
    print("PRESERVATION_PASS",count,flush=True)

def provenance():
    checks=[]
    for name,sealrel,handoffrel,status in [
      ("s2_common_context","provenance/recovery_stage18b1r_successor.json","validation/stage18b1r_handoff.json","STAGE_18B1R_PASS"),
      ("m1_capacity_matched","provenance/experiment.json","validation/final_handoff.json","STAGE_18B2_PASS"),
      ("ar_arx_baseline","recovery/successor_audit_reduction_fix.json","recovery/final_handoff.json","STAGE_18B3R_PASS")]:
        root=EXP/name;seal=read(root/sealrel);handoff=read(root/handoffrel)
        need(handoff["status"]==status,"Nonterminal posthoc "+name)
        for rel,h in seal["source_hashes"].items():need(sha(ROOT/rel)==h,"Sealed source differs "+rel)
        original=read(root/"provenance/experiment.json")
        for b,h in original.get("plan_hashes",{}).items():need(sha(root/f"plans/{b}.json")==h,"Plan changed "+b)
        for b in BLOCKS:need(read(root/f"validation/full_audit_{b}.json")["status"]=="PASS","Incomplete block "+b)
        report=Path(handoff.get("report_path",handoff.get("summary",{}).get("report_path","")))
        need(report.is_file() and sha(report)==handoff["report_sha256"],"Final report hash differs "+name)
        summary=read(root/"completion_summary.json")
        if name=="s2_common_context":need(summary["counts"]=={"failed":0,"new":5712,"required":10920,"reused":5208},"B1 counts")
        else:need(summary["counts"]==({"failed":0,"inner":8190,"final":2730} if name=="m1_capacity_matched" else {"failed":0,"inner":36400,"final":7280}),"Posthoc counts")
        result=root/"posthoc_results.csv";f=pd.read_csv(result)
        need(len(f)==24 and not f.duplicated(["block","resource"]).any(),"Posthoc result coverage")
        need(np.isfinite(f.select_dtypes("number").to_numpy()).all(),"Nonfinite posthoc summaries")
        checks.append({"experiment":name,"status":status,"active_seal":str((root/sealrel).relative_to(ROOT)),"active_seal_sha256":sha(root/sealrel),"result_file":str(result.relative_to(ROOT)),"result_sha256":sha(result),"metric_file":str((root/"posthoc_metric_rows.parquet").relative_to(ROOT)),"metric_sha256":sha(root/"posthoc_metric_rows.parquet"),"final_report":str(report.relative_to(ROOT)),"report_sha256":sha(report),"six_block_audits":"PASS","counts":summary["counts"]})
    rec=read(EXP/"ar_arx_baseline/recovery/35_units_recovered.json")
    need(rec["status"]=="PASS" and len(rec["units"])==35,"Unresolved AR recovery")
    for unit in rec["units"]:need(sha(unit["completion_path"])==unit["completion_sha256"],"Recovered completion changed")
    common=read(EXP/"s2_common_context/recovery/four_units_recovered.json")
    need(common["status"]=="PASS" and len(common["units"])==4,"Unresolved common context recovery")
    for unit in common["units"]:need(sha(unit["completion_path"])==unit["completion_sha256"],"Recovered common completion changed")
    write(OUT/"posthoc_provenance.json",{"status":"PASS","experiments":checks,"historical_failure_records":"preserved and evidence-resolved, not current blockers","training_or_inference":0})

def frozen_gain(block,resource,comparison):
    root=ROOT/FROZEN[block]
    if block=="TimeTrack":
        f=pd.read_csv(root/f"comparisons/{comparison.lower()}.csv")
        row=f[f.resource.eq(resource)&f.lead.eq("OVERALL")];need(len(row)==1,"Frozen gain uniqueness")
        return float(row.iloc[0].primary_gain_pct)
    f=pd.read_csv(root.parent/"comparisons/secondary_aggregation_diagnostics.csv")
    key="trace" if block.startswith("Materna") else "environment"
    row=f[f[key].eq(block)&f.resource.eq(resource)&f.comparison.eq(comparison)&f.scope.eq("overall")]
    need(len(row)==1,"Frozen gain uniqueness")
    return float(row.iloc[0].primary_macro_gain_percent)

def robust_values(f,block,resource,comparison,unit):
    c=f.candidate_mae.to_numpy();v=f.reference_mae.to_numpy();need(np.isfinite(c).all() and np.isfinite(v).all() and (c>=0).all() and (v>=0).all(),"Invalid primary errors")
    defined=~((c==0)&(v==0))
    with np.errstate(divide="ignore",invalid="ignore"):
        ratios=c[defined]/v[defined];logs=np.log(ratios)
    # No epsilon or silent dropping: 0/0 is enumerated; +/-infinity retained.
    def median(a):
        result=float(np.median(a));return result if np.isfinite(result) else str(result)
    return {"block":block,"resource":resource,"comparison":comparison,"unit":unit,"matched_cells":len(f),"median_log_ratio":median(logs),"median_MAE_ratio":median(ratios),"candidate_win_rate":float(np.mean(c<v)),"candidate_wins":int((c<v).sum()),"ties":int((c==v).sum()),"ratio_0over0_undefined":int((~defined).sum()),"zero_candidate_positive_reference":int(((c==0)&(v>0)).sum()),"positive_candidate_zero_reference":int(((c>0)&(v==0)).sum()),"frozen_MacroMAE_gain_percent":frozen_gain(block,resource,comparison)}

def matched_summaries():
    robust=[];seeded=[];seedstats=[];cellstats=[];paired=[];gaincrosschecks=0
    for block in BLOCKS:
        root=ROOT/FROZEN[block];f=pd.read_parquet(root/"metrics.parquet");entity="machine" if block=="TimeTrack" else "vm_id"
        f[entity]=f[entity].astype(str)
        need(set(f.seed)=={0,1,2},"Missing original seed")
        keys=["resource",entity,"fold","lead","seed"]
        need(not f.duplicated(keys+["formulation"]).any(),"Duplicate frozen metric identity")
        pivot=f.pivot(index=keys,columns="formulation",values="mae").reset_index()
        n=f.pivot(index=keys,columns="formulation",values="n").reset_index()
        need((n.S1==n.S2).all() and (n.S2==n.M1).all(),"Sample count mismatch")
        for comparison,candidate,reference in [("S2_vs_S1","S2","S1"),("M1_vs_S2","M1","S2")]:
            raw=pivot[keys+[candidate,reference]].rename(columns={candidate:"candidate_mae",reference:"reference_mae",entity:"entity"})
            if block=="TimeTrack":
                old=pd.read_csv(root/f"comparisons/{comparison.lower()}_cells.csv").rename(columns={"machine":"entity","baseline_mae":"reference_check","candidate_mae":"candidate_check"})
                check=raw.merge(old,on=["resource","entity","fold","lead","seed"],validate="one_to_one")
                need(len(check)==len(raw) and np.allclose(check.reference_mae,check.reference_check,rtol=1e-12,atol=0) and np.allclose(check.candidate_mae,check.candidate_check,rtol=1e-12,atol=0),"Frozen TT paired cells disagree")
            cells=raw.groupby(["resource","entity","fold","lead"],as_index=False)[["candidate_mae","reference_mae"]].mean()
            if block!="TimeTrack":
                existing=pd.read_csv(root.parent/"analysis/matched_vm_fold_cells.csv",dtype={"vm_id":str})
                existing=existing[existing.environment_key.eq(block)]
                for form,column in [(candidate,"candidate_mae"),(reference,"reference_mae")]:
                    q=existing[existing.formulation.eq(form)].rename(columns={"vm_id":"entity"})
                    q=cells.merge(q,on=["resource","entity","fold","lead"],validate="one_to_one")
                    need(len(q)==len(cells) and np.allclose(q[column],q.seed_mean_mae,rtol=1e-12,atol=0),"Frozen external paired cells disagree")
            for resource in RESOURCES:
                r=raw[raw.resource.eq(resource)].copy();c=cells[cells.resource.eq(resource)].copy()
                robust.append(robust_values(c,block,resource,comparison,"entity-fold-lead, seed-mean errors"))
                seeded.append(robust_values(r,block,resource,comparison,"entity-fold-lead-seed"))
                c["block"]=block;c["comparison"]=comparison;paired.extend(c.to_dict("records"))
                gains=[]
                for seed,g in r.groupby("seed",sort=True):
                    m=g.groupby("lead")[["candidate_mae","reference_mae"]].mean().mean()
                    gain=100*(m.reference_mae-m.candidate_mae)/m.reference_mae;gains.append(float(gain))
                    if block!="TimeTrack":
                        old=pd.read_csv(root.parent/"analysis/positive_seed_signs.csv")
                        key="trace" if "trace" in old else "environment"
                        row=old[old[key].eq(block)&old.resource.eq(resource)&old.comparison.eq(comparison)&old.seed.eq(seed)]
                        need(len(row)==1 and np.isclose(row.iloc[0].gain_percent,gain,rtol=1e-10,atol=1e-10),"Existing seed gain mismatch");gaincrosschecks+=1
                local_counts={"stable_win_cells":0,"stable_loss_cells":0,"all_tie_cells":0,"strict_sign_variable_cells":0,"tie_mixed_no_strict_flip_cells":0}
                spans=[];sds=[];undefined=0
                for (e,fold,lead),g in r.groupby(["entity","fold","lead"],sort=True):
                    need(len(g)==3,"Missing paired seed");g=g.sort_values("seed");d=g.reference_mae.to_numpy()-g.candidate_mae.to_numpy()
                    if (d>0).all():category="stable_win_cells"
                    elif (d<0).all():category="stable_loss_cells"
                    elif (d==0).all():category="all_tie_cells"
                    elif (d>0).any() and (d<0).any():category="strict_sign_variable_cells"
                    else:category="tie_mixed_no_strict_flip_cells"
                    local_counts[category]+=1
                    denom=g.reference_mae.to_numpy()
                    if (denom>0).all():
                        sg=100*d/denom;span=float(np.ptp(sg));sd=float(np.std(sg,ddof=0));spans.append(span);sds.append(sd)
                    else:sg=None;span=sd=None;undefined+=1
                    cellstats.append({"block":block,"resource":resource,"comparison":comparison,"entity":e,"fold":int(fold),"lead":int(lead),"sign_category":category,"seed_gain_0":float(sg[0]) if sg is not None else None,"seed_gain_1":float(sg[1]) if sg is not None else None,"seed_gain_2":float(sg[2]) if sg is not None else None,"seed_gain_range_pp":span,"seed_gain_SD_pp":sd})
                seedstats.append({"block":block,"resource":resource,"comparison":comparison,"seed0_gain":gains[0],"seed1_gain":gains[1],"seed2_gain":gains[2],"seed_gain_min":min(gains),"seed_gain_max":max(gains),"seed_gain_range_pp":float(np.ptp(gains)),"seed_gain_population_SD_pp":float(np.std(gains,ddof=0)),"aggregate_seed_sign_variable":min(gains)<0<max(gains),"median_cell_seed_range_pp":float(np.median(spans)),"median_cell_seed_SD_pp":float(np.median(sds)),"undefined_cell_gain_spreads":undefined,**local_counts})
    csv("robust_seed_mean_cells.csv",pd.DataFrame(robust));csv("robust_seed_matched_cells.csv",pd.DataFrame(seeded));csv("seed_sensitivity.csv",pd.DataFrame(seedstats));csv("seed_matched_cell_sensitivity.csv",pd.DataFrame(cellstats));csv("matched_seed_mean_errors.csv",pd.DataFrame(paired))
    write(OUT/"matched_checks.json",{"status":"PASS","robust_rows":len(robust),"seed_sensitivity_rows":len(seedstats),"existing_external_seed_gain_crosschecks":gaincrosschecks,"original_MacroMAE_gains_replaced":False,"SD_ddof":0,"training_or_inference":0})

def ridge_diagnosis():
    root=EXP/"ar_arx_baseline";groups=read(root/"plans/TimeTrack.json")["groups"]
    metrics=pd.read_parquet(root/"posthoc_metric_rows.parquet");metrics=metrics[metrics.block.eq("TimeTrack")&metrics.resource.eq("THROUGHPUT")]
    rows=[];ranges=[];frozencontexts=pd.read_csv(ROOT/FROZEN["TimeTrack"]/"selected_contexts.csv")
    for spec in groups:
        oldrecord=read(spec["reference_record"]);need(sha(spec["reference_record"])==spec["reference_record_sha256"],"Frozen scaler source changed")
        need(spec["scalers"]["final"]==oldrecord["scaler_metadata"],"Frozen source scaler differs")
        ctx=frozencontexts[frozencontexts.formulation.eq("M1")&frozencontexts.machine.eq(spec["entity"])&frozencontexts.fold.eq(spec["fold"])]
        need(len(ctx)==1 and int(ctx.iloc[0].selected_L)==spec["L"],"Frozen M1 context differs")
        reference=pd.read_parquet(spec["reference_prediction"]);reference=reference[reference.resource.eq("THROUGHPUT")].sort_values(["origin_index","lead"]).reset_index(drop=True)
        row={"machine":spec["entity"],"fold":spec["fold"],"L":spec["L"]}
        for form in ["AR","ARX"]:
            subset=metrics[metrics.entity.eq(spec["entity"])&metrics.fold.eq(spec["fold"])&metrics.formulation.eq(form)]
            need(len(subset)==8 and subset.alpha.nunique()==1,"TT throughput metric coverage")
            runid=subset.iloc[0].run_id;completion=read(root/f"completions/final/TimeTrack/{runid}.json");identity=completion["identity"]
            need(identity["L"]==spec["L"] and identity["support"]==spec["final_support"] and completion["source_scaler"]==spec["scalers"]["final"],"Support/scaler mismatch")
            need(sha(completion["prediction_path"])==completion["prediction_sha256"] and sha(completion["model_path"])==completion["model_sha256"],"Ridge artifact hash differs")
            selection=read(root/f"selections/TimeTrack/{spec['group_id']}_{form}_THROUGHPUT.json")
            candidates=[]
            for source in selection["candidate_sources"]:
                need(sha(source["path"])==source["sha256"],"Inner source hash differs")
                c=read(source["path"]);need(c["test_evaluations"]==0,"Selection used test")
                candidates.append((c["validation_score"],c["identity"]["alpha"]))
            need(len(candidates)==5 and sorted(candidates)[0][1]==identity["alpha"]==selection["alpha"],"Alpha differs from inner selection")
            p=pd.read_parquet(completion["prediction_path"]).sort_values(["origin_index","lead"]).reset_index(drop=True)
            for col in ["origin_index","lead","target_index","sample_id","origin_timestamp","target_timestamp","support_hash","y_true"]:
                need(np.array_equal(p[col].to_numpy(),reference[col].to_numpy()),"Ridge frozen support/target differs "+col)
            need(np.isfinite(p[["y_true","y_pred","y_pred_scaled","y_pred_unclipped"]].to_numpy()).all(),"Nonfinite Ridge prediction/target")
            sc=spec["scalers"]["final"]["THROUGHPUT"]
            inverse=np.expm1(p.y_pred_scaled.to_numpy().astype(float)*sc["transformed_iqr"]+sc["transformed_median"])
            need(np.array_equal(inverse,p.y_pred_unclipped.to_numpy()) and np.array_equal(np.maximum(0,inverse),p.y_pred.to_numpy()),"Stored inverse transform differs")
            calculated=p.assign(error=np.abs(p.y_true-p.y_pred)).groupby("lead").error.mean()
            need(np.allclose(calculated.to_numpy(),subset.sort_values("lead").mae.to_numpy(),rtol=1e-12,atol=0),"Saved prediction MAE differs")
            with np.load(completion["model_path"],allow_pickle=False) as model:
                need(all(np.isfinite(model[k]).all() for k in model.files),"Nonfinite Ridge coefficient/scaler")
                need(model["coef"].shape==(8,spec["L"]*(1 if form=="AR" else 4)),"Wrong input scope")
                need(int(model["feature_samples"])==oldrecord["outer_train_n"],"Feature scaler training count differs")
            row[form+"_MAE"]=float(subset.mae.mean());row[form+"_alpha"]=float(identity["alpha"])
            ranges.append({"machine":spec["entity"],"fold":spec["fold"],"formulation":form,"run_id":runid,"n_prediction_rows":len(p),"finite":True,"target_min":float(p.y_true.min()),"target_max":float(p.y_true.max()),"prediction_min":float(p.y_pred.min()),"prediction_max":float(p.y_pred.max()),"scaled_prediction_min":float(p.y_pred_scaled.min()),"scaled_prediction_max":float(p.y_pred_scaled.max()),"inverse_and_projection_exact":True,"support_targets_context_scaler_verified":True,"model_predict_calls":0})
        row["ratio"]=row["ARX_MAE"]/row["AR_MAE"];row["excess"]=row["ARX_MAE"]-row["AR_MAE"];rows.append(row)
    f=pd.DataFrame(rows);ordered=f.sort_values("excess",ascending=False);pos=ordered.excess.clip(lower=0).sum();net=ordered.excess.sum()
    summary={"status":"PASS","group_count":len(f),"AR_macro":float(f.AR_MAE.mean()),"ARX_macro":float(f.ARX_MAE.mean()),"worse_groups":int((f.ratio>1).sum()),"better_groups":int((f.ratio<1).sum()),"ties":int((f.ratio==1).sum()),"median_ratio":float(f.ratio.median()),"net_excess_sum":float(net),"positive_excess_sum":float(pos),"top_positive_excess_groups":[]}
    for k in [1,3,5]:
        top=ordered.head(k);summary["top_positive_excess_groups"].append({"k":k,"groups":top[["machine","fold","excess"]].to_dict("records"),"share_positive_excess":float(top.excess.clip(lower=0).sum()/pos),"share_net_excess":float(top.excess.sum()/net)})
    rr=pd.DataFrame(ranges)
    summary["ranges"]={form:{k:float(v) for k,v in rr[rr.formulation.eq(form)].agg({"target_min":"min","target_max":"max","prediction_min":"min","prediction_max":"max","scaled_prediction_min":"min","scaled_prediction_max":"max"}).items()} for form in ["AR","ARX"]}
    summary["alpha_counts"]={form:{str(a):int(n) for a,n in f[form+"_alpha"].value_counts().sort_index().items()} for form in ["AR","ARX"]}
    csv("timetrack_throughput_machine_fold.csv",f);csv("timetrack_throughput_prediction_checks.csv",rr)
    csv("timetrack_throughput_machine_summary.csv",f.groupby("machine",as_index=False).agg(AR_MAE=("AR_MAE","mean"),ARX_MAE=("ARX_MAE","mean"),excess=("excess","sum")))
    write(OUT/"timetrack_throughput_diagnosis.json",summary)

def matrices():
    ridge=pd.read_csv(EXP/"ar_arx_baseline/posthoc_results.csv")
    common=pd.read_csv(EXP/"s2_common_context/posthoc_results.csv")
    capacity=pd.read_csv(EXP/"m1_capacity_matched/posthoc_results.csv")
    contextual=[];sharing=[]
    for b in BLOCKS:
        for res in RESOURCES:
            row=ridge[(ridge.block==b)&(ridge.resource==res)].iloc[0]
            lstm=frozen_gain(b,res,"S2_vs_S1");need(lstm==row.frozen_S2_vs_S1_gain_percent,"Frozen context gain differs")
            contextual.append({"block":b,"resource":res,"LSTM_S2_vs_S1_gain_percent":lstm,"Ridge_ARX_vs_AR_gain_percent":row.ARX_vs_AR_gain_percent,"sign_agrees":np.sign(lstm)==np.sign(row.ARX_vs_AR_gain_percent)})
            co=common[(common.block==b)&(common.resource==res)].iloc[0];ca=capacity[(capacity.block==b)&(capacity.resource==res)].iloc[0]
            original=frozen_gain(b,res,"M1_vs_S2")
            need(np.isclose(original,co.original_M1_vs_S2_gain_percent,rtol=1e-12) and np.isclose(original,ca.original_H64_vs_S2_gain_percent,rtol=1e-12),"Original sharing gain differs")
            sharing.append({"block":b,"resource":res,"H64_vs_S2":original,"H64_vs_common_S2":co.M1_vs_S2_common_gain_percent,"H129_vs_S2":ca.H129_vs_S2_gain_percent,"adverse_in_all_three":original<0 and co.M1_vs_S2_common_gain_percent<0 and ca.H129_vs_S2_gain_percent<0})
    csv("contextual_evidence.csv",pd.DataFrame(contextual));csv("sharing_sensitivity.csv",pd.DataFrame(sharing))

def compute():
    verify_git();provenance();matched_summaries();ridge_diagnosis();matrices()
    write(OUT/"computation_status.json",{"status":"PASS","training":0,"model_inference":0,"posthoc_metrics_replaced":False,"script_sha256":sha(Path(__file__))})
    print("READ_ONLY_COMPUTATIONS_PASS",flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=["baseline","compute","preserve"]);args=parser.parse_args()
    {"baseline":baseline,"compute":compute,"preserve":preserve}[args.action]()
