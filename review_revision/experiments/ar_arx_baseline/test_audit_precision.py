"""Read-only regression for NumPy2 scalar promotion in post-fit audit."""
import numpy as np
import run_linear_control as r

def main():
    e=r.frozen.Engine("TimeTrack"); count=0; previous_failures=0
    for spec in r.read(r.HERE/"plans/TimeTrack.json")["groups"]:
        f,fold,sc=r.checked_data(e,spec,"final")
        X,y,_,_,_=r.arrays(e,f,spec,fold.outer_test,sc)
        for i,resource in enumerate(e.resources):
            pm=np.mean(np.abs(y[:,i,:]-np.repeat(X[:,-1,i,None],len(e.leads),axis=1)),axis=0)
            for form in ("AR","ARX"):
                selection=r.read(r.selection_path(spec,form,resource))
                identity=r.ident(spec,"final",form,resource,selection["alpha"],r.sha(r.selection_path(spec,form,resource)))
                value=r.read(r.completion_path(identity)); r.validate_completion(identity,value)
                for j,m in enumerate(value["metrics"]):
                    if pm[j]>0:
                        correct=1-np.float64(m["mae"])/pm[j]
                        r.require(correct==m["persistence_skill"],"Float64 audit differs from stored computation")
                        previous_failures+=int(not np.isclose(1-float(m["mae"])/pm[j],m["persistence_skill"],rtol=1e-12,atol=1e-14))
                    count+=1
    r.require(previous_failures>0,"Old checker blocker not reproduced")
    r.write(r.HERE/"recovery/audit_precision_test.json",{"status":"PASS","checked_metrics":count,"old_scalar_promotion_failures_reproduced":previous_failures,"scientific_fits":0,"test_inference":0,"metrics_changed":0,"timestamp":r.now()})
    print("AUDIT_PRECISION_PASS",count,previous_failures,flush=True)

if __name__=="__main__":main()
