#!/usr/bin/env python3
"""Stage18B2: read-only frozen primitives, H129 factory only, isolated writers.

Never calls a frozen driver main/writer or the previous control's writers.
All scientific training/selection primitives are imported unchanged.
"""
from __future__ import annotations
import argparse
import fcntl
import importlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIOR = ROOT / "review_revision/experiments/s2_common_context"
sys.path.insert(0, str(PRIOR))
import run_control as frozen

CONFIG = HERE / "control_config.json"
LABEL = "POST-HOC SENSITIVITY CONTROL"
RESULT_LABEL = "POST-HOC SENSITIVITY RESULT"
sha, canonical, read, now, require = frozen.sha, frozen.canonical, frozen.read, frozen.now, frozen.require
PROTECTED = (*frozen.PROTECTED, str(PRIOR.relative_to(ROOT)),
             "review_revision/experiments/s2_common_context_predecessor_stage18b1r")
ENGINE = None


def output(path):
    path = Path(path).resolve()
    require(path.is_relative_to(HERE), f"Forbidden write {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write(path, value):
    path = output(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")
    os.replace(tmp, path)


def parquet(path, frame):
    path = output(path); tmp = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(tmp, index=False, compression="zstd"); os.replace(tmp, path)


def verify_refs():
    c = read(CONFIG)
    require(frozen.git("branch", "--show-current") == c["branch"], "Branch mismatch")
    require(frozen.git("rev-parse", "HEAD") == c["parent_manuscript_checkpoint"], "HEAD mismatch")
    require(frozen.git("rev-parse", "HEAD^") == c["parent_scientific_checkpoint"], "Parent mismatch")
    require(frozen.refs()["scientific_tag_target"] == c["parent_scientific_checkpoint"], "Scientific tag mismatch")
    require(not frozen.git("diff", "--name-only") and not frozen.git("diff", "--cached", "--name-only"), "Tracked changes exist")


def inventory():
    for rel in PROTECTED:
        for path in sorted((ROOT / rel).rglob("*")):
            if path.is_file():
                yield {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path)}


def preserve(capture=False):
    path = output(HERE / "provenance/preservation_before.jsonl")
    if capture:
        require(not path.exists(), "Preservation baseline exists")
        # Check original scientific bytes against the pre-18B1 baseline, not just now.
        old = PRIOR/"provenance/preservation_before.jsonl"
        old_meta = read(PRIOR/"provenance/preservation_baseline.json")
        require(sha(old) == old_meta["inventory_sha256"], "Original protected baseline differs")
        with old.open() as stream:
            original = {r["path"]:r for r in map(json.loads,stream)}
        count = 0
        with path.open("x") as stream:
            for row in inventory():
                if row["path"] in original:
                    require(row["sha256"] == original[row["path"]]["sha256"], f"Original frozen artifact changed {row['path']}")
                    original.pop(row["path"])
                stream.write(json.dumps(row, sort_keys=True) + "\n"); count += 1
        require(not original, "Original protected file missing")
        write(HERE / "provenance/preservation_baseline.json", {"files": count, "refs": frozen.refs(), "inventory_sha256": sha(path), "timestamp": now()})
        return
    baseline = read(HERE / "provenance/preservation_baseline.json")
    require(sha(path) == baseline["inventory_sha256"], "Preservation inventory changed")
    require(frozen.refs() == baseline["refs"], "Protected refs changed")
    with path.open() as stream:
        expected = {r["path"]: r for r in map(json.loads, stream)}
    count = 0
    for actual in inventory():
        require(expected.get(actual["path"]) == actual, f"Protected file changed/added {actual['path']}")
        count += 1
    require(count == len(expected), "Protected files missing")
    write(HERE / "provenance/preservation_after.json", {"status": "PASS", "files": count, "timestamp": now(), "refs": frozen.refs(), "modified": 0})


def source_hashes():
    paths = list(HERE.glob("*.py")) + [CONFIG, PRIOR / "run_control.py", PRIOR / "analyse_control.py"]
    for rel in frozen.PROTECTED[:3]:
        base = ROOT / rel
        paths += list(base.glob("*.py")) + list((base / "src").rglob("*.py"))
    paths += list((ROOT / "benchmark/src").rglob("*.py"))
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(paths))}


def verify_seal():
    sealed = read(HERE / "provenance/experiment.json")
    require(sha(CONFIG) == sealed["configuration_sha256"], "Configuration changed")
    for rel, digest in sealed["source_hashes"].items():
        require(sha(ROOT / rel) == digest, f"Sealed source changed {rel}")
    require(read(HERE / "validation/tests.json")["status"] == "PASS", "Safety tests not passed")


def parameter_formula(channels, hidden, outputs):
    return 12 * hidden * hidden + (4 * channels + 16 + outputs) * hidden + outputs


def configure_engine(block):
    engine = frozen.Engine(block)
    training = importlib.import_module("src.training")
    model_class = importlib.import_module("src.models").MultiTargetLSTM
    cfg = read(CONFIG)
    for name, value in (("LEARNING_RATE", .001), ("BATCH_SIZE", 256), ("MAX_EPOCHS", 50), ("PATIENCE", 7), ("GRADIENT_CLIP", 1.0)):
        require(getattr(training, name) == value, f"Frozen optimisation {name}")
    def factory(formulation, channels):
        require(formulation == "M1" and channels == 4, "Only four-channel M1 is authorised")
        model = model_class(channels, hidden_size=cfg["hidden_size"])
        verify_model(engine, model)
        return model
    training.build_model = factory
    engine.core.build_model = factory
    original_loss = training.resource_losses
    def loss(*args, **kwargs):
        values = original_loss(*args, **kwargs)
        require(bool(engine.torch.isfinite(values[0])), "Nonfinite loss", "PRIMARY_NONFINITE_RESULT_CONFLICT")
        return values
    training.resource_losses = loss
    engine.core.resource_losses = loss
    clip = engine.torch.nn.utils.clip_grad_norm_
    def safe_clip(*args, **kwargs):
        kwargs["error_if_nonfinite"] = True
        return clip(*args, **kwargs)
    engine.torch.nn.utils.clip_grad_norm_ = safe_clip
    return engine


def verify_model(engine, model):
    enc = model.encoder
    require((enc.input_size, enc.hidden_size, enc.num_layers, enc.dropout, enc.bidirectional, enc.bias) == (4,129,2,.1,False,True), "Architecture differs")
    require(len(model.heads) == 4 and all((h.in_features,h.out_features) == (129,len(engine.leads)) and h.bias is not None for h in model.heads), "Head dimensions differ")
    count = sum(p.numel() for p in model.parameters())
    require(count == parameter_formula(4,129,4*len(engine.leads)) == (207980 if engine.tt else 206420), "Parameter count differs")
    return count


def init_worker(block):
    global ENGINE
    ENGINE = configure_engine(block)


def lengths(engine):
    return read(CONFIG)["contexts_TimeTrack" if engine.tt else "contexts_external"]


def plan_block(block):
    e = configure_engine(block); tasks = []; sources = {}
    expected = e.core.FROZEN_CONFIG_HASH if e.tt else (e.materna.CONFIG_SHA256 if block.startswith("Materna") else e.core.CONFIG_HASH)
    require(sha(e.config_path) == expected, "Frozen configuration differs")
    entities = e.entities()
    require(len(entities) == (7 if e.tt else 35), "Cohort count differs")
    m1 = e.contexts[e.contexts.formulation.eq("M1")]
    require(set(m1[e.entity_key]) == set(entities) and len(m1) == 5*len(entities), "Executed cohort differs")
    for p in [e.config_path,e.support_path,*e.cohort_paths,e.root/"run_registry.csv",e.root/"inner_run_registry.csv"]:
        sources[str(p.relative_to(ROOT))] = sha(p)
    for entity in entities:
        for fold_number in range(1,6):
            contexts = {}
            originals = {}
            for seed in (0,1,2):
                row = e.unique(e.registry, **{e.entity_key:entity,"fold":fold_number,"seed":seed,"formulation":"M1"})
                path, record = e.record(row,"final")
                path = e.root/f"runtime/completions/final/{row.run_id}.json"
                originals[str(seed)] = {"path":str(path.relative_to(ROOT)),"sha256":sha(path),"prediction_path":str(e.artifact(record,"prediction")),"prediction_sha256":record["prediction_sha256"]}
                require(sha(e.artifact(record,"prediction")) == record["prediction_sha256"], "Frozen prediction hash mismatch")
            for L in lengths(e):
                frame, folds = e.data(entity,L); fold = folds[fold_number-1]
                manifest = e.support
                if "environment" in manifest:
                    env = block if block.startswith("Materna") else e.core.ENVIRONMENTS[block]
                    manifest = manifest[manifest.environment.eq(env)]
                row = e.unique(manifest, **{e.entity_key:entity,"fold":fold_number,"context_length" if e.tt else "L":L})
                require(all(row[f"{k}_hash"] == v for k,v in fold.hashes.items()), "Support manifest mismatch", "SCIENTIFIC_SUPPORT_CONFLICT")
                inner = e.scaler_payload(e.scaler(frame,entity,fold.inner_train,L))
                outer = e.scaler_payload(e.scaler(frame,entity,fold.outer_train,L))
                frozen.finite_primary(inner); frozen.finite_primary(outer)
                # At an already-used L the reconstructed outer scaler must be byte-semantic equal too.
                for source in originals.values():
                    record = read(ROOT/source["path"])
                    if int(record["identity"]["L"]) == L:
                        require(e.scaler_from_record(record) == outer, "Frozen outer scaler mismatch", "SCIENTIFIC_SUPPORT_CONFLICT")
                    require(all(record[f"{name}_hash"] == fold.hashes[name] for name in ("outer_train","outer_test")), "Frozen outer support mismatch", "SCIENTIFIC_SUPPORT_CONFLICT")
                # Existing H64 inner artifacts authenticate scaler/support only, never choices/epochs/scores.
                for seed in (0,1,2):
                    original = e.unique(e.inner_registry, **{e.entity_key:entity,"fold":fold_number,"L":L,"seed":seed,"formulation":"M1"})
                    _, record = e.record(original,"inner")
                    require(e.scaler_from_record(record) == inner, "Inner scaler mismatch", "SCIENTIFIC_SUPPORT_CONFLICT")
                contexts[str(L)] = {"split_hashes":fold.hashes,"inner_scaler":inner,"outer_scaler":outer,"inner_support":e.support_hash(fold,"inner"),"outer_support":e.support_hash(fold,"final")}
            spec = {"namespace":read(CONFIG)["namespace"],"configuration_sha256":sha(CONFIG),"block":block,"entity":entity,"fold":fold_number,"hidden_size":129,"contexts":contexts,"originals":originals}
            spec["group_id"] = canonical(spec); tasks.append(spec)
        print(f"PLAN {block} entity={entity} groups={len(tasks)}",flush=True)
    write(HERE/f"plans/{block}.json",{"block":block,"entities":entities,"groups":tasks,"source_hashes":sources,"expected_inner":9*len(tasks),"expected_final":3*len(tasks),"timestamp":now()})


def identity(spec, phase, L, seed, epoch=None, selection_sha=None):
    value = {"namespace":spec["namespace"],"configuration_sha256":spec["configuration_sha256"],"group_id":spec["group_id"],"block":spec["block"],"entity":spec["entity"],"fold":spec["fold"],"phase":phase,"L":L,"seed":seed,"hidden_size":129,"support":spec["contexts"][str(L)]["inner_support" if phase=="inner" else "outer_support"],"scaler_sha256":canonical(spec["contexts"][str(L)]["inner_scaler" if phase=="inner" else "outer_scaler"])}
    if phase == "final":
        require(epoch is not None and selection_sha is not None, "Final selection absent")
        value.update(epoch=epoch,selection_sha256=selection_sha)
    value["run_id"] = canonical(value)
    return value


def completion_path(ident):
    return HERE/f"completions/{ident['phase']}/{ident['block']}/{ident['run_id']}.json"


def validate_completion(e, ident, value):
    require(value["identity"] == ident and value["status"] == "complete", "Completion identity differs")
    require(value["parameter_count"] == (207980 if e.tt else 206420), "Completion parameters")
    require(value["test_evaluations"] == int(ident["phase"] == "final"), "Test evaluation count differs")
    for kind in ("model", "prediction") if ident["phase"] == "final" else ("model",):
        path = Path(value[f"{kind}_path"])
        require(path.resolve().is_relative_to(HERE) and sha(path) == value[f"{kind}_sha256"], f"Artifact hash/path differs {path}")
    frozen.finite_primary(value["metrics"] if ident["phase"] == "final" else value["validation_score"])


def attempt(ident):
    path = HERE/f"attempts/{ident['phase']}/{ident['block']}/{ident['run_id']}.json"
    require(not path.exists(), f"Started-only unit requires explicit recovery {ident}", "UNRESOLVED_ATTEMPT_CONFLICT")
    write(path,{"identity":ident,"started":now(),"source_sha256":sha(Path(__file__))})


def checked_data(e, spec, L, phase):
    frame, folds = e.data(spec["entity"],L); fold = folds[spec["fold"]-1]
    expected = spec["contexts"][str(L)]
    require(fold.hashes == expected["split_hashes"], "Split support differs", "SCIENTIFIC_SUPPORT_CONFLICT")
    scaler = e.scaler(frame,spec["entity"],getattr(fold,"inner_train" if phase=="inner" else "outer_train"),L)
    require(e.scaler_payload(scaler) == expected["inner_scaler" if phase=="inner" else "outer_scaler"], "Scaler differs", "SCIENTIFIC_SUPPORT_CONFLICT")
    return frame,fold,scaler


def check_state(e, model):
    require(all(bool(e.torch.isfinite(v).all()) for v in model.state_dict().values()), "Nonfinite model parameters", "PRIMARY_NONFINITE_RESULT_CONFLICT")
    return verify_model(e,model)


def save_model(e, ident, model):
    path = output(HERE/f"models/{ident['phase']}/{ident['block']}/{ident['run_id']}.pt")
    tmp = path.with_suffix(".pt.tmp"); e.torch.save(model.state_dict(),tmp); os.replace(tmp,path)
    return {"model_path":str(path),"model_sha256":sha(path),"parameter_count":check_state(e,model)}


def choose(e, spec, candidates):
    rows = [e.core.SelectionRow("M1",c["identity"]["L"],c["identity"]["seed"],e.np.asarray(c["validation_score"]),c["best_epoch"]) for c in candidates]
    result = e.core.select_context(rows,"M1")
    return {"group_id":spec["group_id"],"label":LABEL,"L":int(result.context_length),"score":float(result.score),"best_epoch_by_seed":{str(k):int(v) for k,v in result.best_epoch_by_seed.items()},"inner_sources":[{"path":str(completion_path(c["identity"])),"sha256":sha(completion_path(c["identity"]))} for c in candidates]}


def support_check(e, spec, seed, predicted):
    original = spec["originals"][str(seed)]
    require(sha(ROOT/original["path"]) == original["sha256"] and sha(original["prediction_path"]) == original["prediction_sha256"], "Frozen reference changed")
    old = e.pd.read_parquet(original["prediction_path"])
    keys = ["resource","origin_index","lead","target_index","support_hash","y_true"]
    keys += ["sample_id","origin_timestamp","target_timestamp"] if e.tt else ["origin_timestamp_seconds","target_timestamp_seconds"]
    require(len(old) == len(predicted), "Prediction support count differs", "SCIENTIFIC_SUPPORT_CONFLICT")
    # Canonical row ordering avoids dependence on filesystem or resource output order.
    order = ["resource","origin_index","lead"]
    old = old.sort_values(order); new = predicted.sort_values(order)
    require(not new.duplicated(order).any(), "Duplicate prediction support")
    for key in keys:
        require(e.np.array_equal(old[key].to_numpy(),new[key].to_numpy()), f"Prediction support column differs {key}", "SCIENTIFIC_SUPPORT_CONFLICT")


def run_group(spec):
    e = ENGINE; np,core,torch = e.np,e.core,e.torch
    candidates = []; current = None
    try:
        for L in lengths(e):
            frame,fold,scaler = checked_data(e,spec,L,"inner")
            X,y,_ = e.windows(frame,spec["entity"],L,fold.inner_train)
            Xt,yt = core.scale_windows(X,y,scaler)
            X,y,_ = e.windows(frame,spec["entity"],L,fold.inner_validation)
            Xv,yv = core.scale_windows(X,y,scaler)
            require(all(np.isfinite(a).all() for a in (Xt,yt,Xv,yv)), "Nonfinite inner data", "PRIMARY_NONFINITE_RESULT_CONFLICT")
            for seed in (0,1,2):
                current = identity(spec,"inner",L,seed); path = completion_path(current)
                if path.exists():
                    value = read(path); validate_completion(e,current,value); candidates.append(value); continue
                attempt(current); started = now(); tick = time.perf_counter()
                result = core.fit_inner("M1",None,seed,Xt,yt,Xv,yv,device="cpu")
                require(np.isfinite(result.validation_prediction).all(), "Nonfinite validation prediction", "PRIMARY_NONFINITE_RESULT_CONFLICT")
                score = np.mean(np.abs(yv-result.validation_prediction),axis=0).tolist()
                frozen.finite_primary(score); frozen.finite_primary(result.epoch_logs)
                require(1 <= result.best_epoch <= result.epochs_trained <= 50, "Inner epoch invalid")
                value = {"status":"complete","label":LABEL,"identity":current,"started":started,"completed":now(),"elapsed_seconds":time.perf_counter()-tick,"test_evaluations":0,"best_epoch":int(result.best_epoch),"epochs_trained":int(result.epochs_trained),"validation_score":score,"epoch_logs":result.epoch_logs,**save_model(e,current,result.model)}
                write(path,value); candidates.append(value)
                print(f"FIT_COMPLETE inner {e.block} {spec['entity']} fold={spec['fold']} L={L} seed={seed}",flush=True)
        selection = choose(e,spec,candidates); selection_path = HERE/f"selections/{e.block}/{spec['group_id']}.json"
        if selection_path.exists(): require(read(selection_path) == selection, "Selection changed")
        else: write(selection_path,selection)
        L = selection["L"]; frame,fold,scaler = checked_data(e,spec,L,"final")
        X,y,_ = e.windows(frame,spec["entity"],L,fold.outer_train)
        Xt,yt = core.scale_windows(X,y,scaler)
        require(np.isfinite(Xt).all() and np.isfinite(yt).all(), "Nonfinite final training data", "PRIMARY_NONFINITE_RESULT_CONFLICT")
        for seed in (0,1,2):
            epoch = selection["best_epoch_by_seed"][str(seed)]
            current = identity(spec,"final",L,seed,epoch,sha(selection_path)); path = completion_path(current)
            if path.exists(): validate_completion(e,current,read(path)); continue
            attempt(current); started = now()
            model,logs,seconds,rss = core.fit_final_model("M1",None,seed,Xt,yt,epoch)
            require(len(logs) == epoch, "Final epoch count differs"); frozen.finite_primary(logs)
            artifact = save_model(e,current,model)
            # Exactly one outer-test evaluation, only after fixed-epoch refit.
            X,y,raw = e.windows(frame,spec["entity"],L,fold.outer_test)
            test_x,_ = core.scale_windows(X,y,scaler)
            require(np.isfinite(test_x).all() and np.isfinite(y).all(), "Nonfinite outer-test inputs", "PRIMARY_NONFINITE_RESULT_CONFLICT")
            with torch.no_grad(): scaled = model(torch.from_numpy(test_x.astype(np.float32))).numpy()
            require(np.isfinite(scaled).all(), "Nonfinite prediction", "PRIMARY_NONFINITE_RESULT_CONFLICT")
            pieces = []; metrics = []
            legacy = {"run_id":current["run_id"],"formulation":"M1-H129","machine":spec["entity"],"vm_id":spec["entity"],"fold":spec["fold"],"seed":seed,"L":L,"selected_epoch":epoch,"environment":e.block if e.tt or e.block.startswith("Materna") else core.ENVIRONMENTS[e.block],"support_hash":e.support_hash(fold,"final")}
            for i,r in enumerate(e.resources):
                inverse = core.inverse_one(scaled[:,i,:],scaler,r,project=True) if e.tt else scaler.inverse_one(scaled[:,i,:],r,project=True)
                native,negative,unclipped = inverse
                require(np.isfinite(native).all() and np.isfinite(unclipped).all(), "Nonfinite inverse prediction", "PRIMARY_NONFINITE_RESULT_CONFLICT")
                p = core.prediction_frame(legacy,r,raw,scaled[:,i,:],native,unclipped) if e.tt else core.prediction_frame(legacy,r,e.clean,fold.outer_test,epoch,y[:,i,:],scaled[:,i,:],native,unclipped)
                pieces.append(p)
                mae = np.mean(np.abs(y[:,i,:]-native),axis=0)
                require(np.isfinite(mae).all(), "Nonfinite MAE", "PRIMARY_NONFINITE_RESULT_CONFLICT")
                metrics.extend({"resource":r,"lead":int(lead),"mae":float(mae[j]),"n":len(y)} for j,lead in enumerate(e.leads))
            predicted = e.pd.concat(pieces,ignore_index=True); predicted["control_label"] = LABEL
            frozen.validate_prediction_primary(predicted); support_check(e,spec,seed,predicted)
            pred_path = HERE/f"predictions/{e.block}/{current['run_id']}.parquet"; parquet(pred_path,predicted)
            write(path,{"status":"complete","label":LABEL,"identity":current,"started":started,"completed":now(),"train_seconds":seconds,"peak_rss_bytes":rss,"test_evaluations":1,"epoch_logs":logs,"metrics":metrics,"prediction_path":str(pred_path),"prediction_sha256":sha(pred_path),**artifact})
            print(f"FIT_COMPLETE final {e.block} {spec['entity']} fold={spec['fold']} L={L} seed={seed} epoch={epoch}",flush=True)
        return {"inner":9,"final":3}
    except BaseException as exc:
        write(HERE/f"failures/{e.block}/{current['run_id'] if current else spec['group_id']}.json",{"timestamp":now(),"identity":current,"group_id":spec["group_id"],"error":repr(exc),"traceback":traceback.format_exc()})
        raise


def run_block(block, workers):
    verify_seal(); plan = read(HERE/f"plans/{block}.json")
    for rel,digest in plan["source_hashes"].items(): require(sha(ROOT/rel) == digest, f"Plan source changed {rel}")
    done = 0
    with mp.get_context("spawn").Pool(workers,initializer=init_worker,initargs=(block,)) as pool:
        for result in pool.imap_unordered(run_group,plan["groups"],chunksize=1):
            done += 1
            write(HERE/f"progress/{block}.json",{"completed_groups":done,"required_groups":len(plan["groups"]),"timestamp":now()})
            print(f"PROGRESS {block} groups={done}/{len(plan['groups'])}",flush=True)


def audit_block(block):
    e = configure_engine(block); plan = read(HERE/f"plans/{block}.json")
    expected = {"inner":set(),"final":set()}; metric_rows = 0
    for spec in plan["groups"]:
        candidates = []
        for L in lengths(e):
            checked_data(e,spec,L,"inner")
            for seed in (0,1,2):
                ident = identity(spec,"inner",L,seed); value = read(completion_path(ident))
                validate_completion(e,ident,value); candidates.append(value); expected["inner"].add(ident["run_id"])
        selection = choose(e,spec,candidates); path = HERE/f"selections/{block}/{spec['group_id']}.json"
        require(read(path) == selection, "Fresh selection audit differs")
        checked_data(e,spec,selection["L"],"final")
        for seed in (0,1,2):
            ident = identity(spec,"final",selection["L"],seed,selection["best_epoch_by_seed"][str(seed)],sha(path))
            value = read(completion_path(ident)); validate_completion(e,ident,value)
            pred = e.pd.read_parquet(value["prediction_path"])
            frozen.validate_prediction_primary(pred); support_check(e,spec,seed,pred)
            require(pred.selected_L.eq(ident["L"]).all() and pred.selected_epoch.eq(ident["epoch"]).all(), "Prediction L/epoch differs")
            state = e.torch.load(value["model_path"],map_location="cpu",weights_only=True)
            require(all(bool(e.torch.isfinite(v).all()) for v in state.values()), "Nonfinite checkpoint", "PRIMARY_NONFINITE_RESULT_CONFLICT")
            require(sum(v.numel() for v in state.values()) == value["parameter_count"], "Checkpoint parameters differ")
            require(len(value["metrics"]) == 4*len(e.leads), "Metric count differs")
            for m in value["metrics"]:
                p = pred[pred.resource.eq(m["resource"]) & pred.lead.eq(m["lead"])]
                require(len(p) == m["n"] and e.np.isclose(e.np.mean(e.np.abs(p.y_true-p.y_pred)),m["mae"],rtol=1e-12,atol=0), "Persisted MAE differs")
            expected["final"].add(ident["run_id"]); metric_rows += len(value["metrics"])
    for phase in expected:
        files = list((HERE/f"completions/{phase}/{block}").glob("*.json"))
        require({p.stem for p in files} == expected[phase] and len(files) == len(expected[phase]), "Duplicate/missing completion identity", "CONTROL_COMPLETION_DUPLICATION_CONFLICT")
    write(HERE/f"validation/full_audit_{block}.json",{"status":"PASS","inner":len(expected["inner"]),"final":len(expected["final"]),"metric_rows":metric_rows,"duplicates":0,"timestamp":now()})


def child(action,block=None,workers=4):
    args = [sys.executable,"-B",str(Path(__file__)),action]
    if block: args += ["--block",block]
    if action == "run-block": args += ["--workers",str(workers)]
    subprocess.run(args,cwd=ROOT,check=True)


def prepare():
    verify_refs()
    require(not (HERE/"provenance/experiment.json").exists(), "Already sealed; do not overwrite")
    require(read(HERE/"validation/tests.json")["status"] == "PASS", "Tests required")
    require(read(PRIOR/"completion_summary.json")["counts"] == {"required":10920,"reused":5208,"new":5712,"failed":0}, "Stage18B1R not complete")
    if not (HERE/"provenance/preservation_before.jsonl").exists(): preserve(capture=True)
    else: preserve()
    for block in read(CONFIG)["blocks"]: child("plan-block",block)
    plans = [read(HERE/f"plans/{b}.json") for b in read(CONFIG)["blocks"]]
    require(sum(p["expected_inner"] for p in plans) == 8190 and sum(p["expected_final"] for p in plans) == 2730, "Plan count differs")
    write(HERE/"provenance/experiment.json",{"namespace":read(CONFIG)["namespace"],"label":LABEL,"timestamp":now(),"configuration_sha256":sha(CONFIG),"source_hashes":source_hashes(),"plan_hashes":{p["block"]:sha(HERE/f"plans/{p['block']}.json") for p in plans},"parent_scientific_checkpoint":read(CONFIG)["parent_scientific_checkpoint"],"parent_manuscript_checkpoint":read(CONFIG)["parent_manuscript_checkpoint"],"source_commit":frozen.git("rev-parse","HEAD"),"prior_control_summary_sha256":sha(PRIOR/"completion_summary.json"),"inner":8190,"final":2730,"reused_H64_fits":0})
    write(HERE/"validation/preflight.json",{"status":"PASS","inner":8190,"final":2730,"timestamp":now()})
    print("PREFLIGHT_PASS inner=8190 final=2730",flush=True)


def run_all(workers):
    verify_refs(); verify_seal()
    require(not list((HERE/"failures").rglob("*.json")), "Unresolved failed unit; do not retry")
    for phase in ("inner","final"):
        for path in (HERE/f"attempts/{phase}").rglob("*.json"):
            require((HERE/f"completions/{phase}/{path.parent.name}/{path.name}").exists(), f"Interrupted attempt {path}", "UNRESOLVED_ATTEMPT_CONFLICT")
    for block in read(CONFIG)["blocks"]:
        require(sha(HERE/f"plans/{block}.json") == read(HERE/"provenance/experiment.json")["plan_hashes"][block], "Plan changed")
        child("run-block",block,workers); child("audit-block",block)
    preserve()
    subprocess.run([sys.executable,"-B",str(HERE/"analyse_capacity_control.py")],cwd=ROOT,check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action",choices=["prepare","plan-block","run","run-block","audit-block","verify"])
    parser.add_argument("--block",choices=list(frozen.FROZEN)); parser.add_argument("--workers",type=int,default=4)
    a = parser.parse_args(); lock = None
    if a.action in ("prepare","run"):
        lock = output(HERE/"runtime.lock").open("a")
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise frozen.Conflict("ACTIVE_PROCESS_CONFLICT","Do not launch duplicate work")
    try:
        if a.action == "prepare": prepare()
        elif a.action == "plan-block": plan_block(a.block)
        elif a.action == "run": run_all(a.workers)
        elif a.action == "run-block": run_block(a.block,a.workers)
        elif a.action == "audit-block": audit_block(a.block)
        else: preserve()
    except BaseException as exc:
        if a.action in ("prepare","run"):
            write(HERE/"STOP.json",{"status":getattr(exc,"code","STAGE_18B2_BLOCKED"),"timestamp":now(),"error":repr(exc),"traceback":traceback.format_exc()})
        raise


if __name__ == "__main__": main()
