"""Generated native MAE cells and provenance for statistical tests."""

from fgcs_strengthening_v03.src.statistics.design import CONFIG, CORE, FOLDS, analysis_slots
from fgcs_strengthening_v03.src.statistics.endpoints import Cell, entity_aggregate
from fgcs_strengthening_v03.src.statistics.schema import Provenance

GENERATED_PROVENANCE = Provenance("1" * 64, "2" * 64, {"generated_source": "3" * 64},
                                  {"generated_input": "4" * 64})


def cells(model, mae=1., *, block="fastStorage", entity="697", resource="CPU", seeds=CORE,
          context=None, support="support", scaler="scaler"):
    config = CONFIG["blocks"][block]
    context = config["contexts"][0] if context is None else context
    return [Cell(model, block, entity, resource, fold, horizon, seed,
                 mae(fold, horizon, seed) if callable(mae) else mae, context,
                 f"{support}-{fold}", f"{scaler}-{fold}", f"origins-{fold}")
            for fold in FOLDS for horizon in config["horizons"] for seed in seeds]


def aggregate(model, mae=1., *, block="fastStorage", entity="697", resource="CPU", seeds=CORE, **kwargs):
    return entity_aggregate(cells(model, mae, block=block, entity=entity, resource=resource, seeds=seeds, **kwargs),
                            model=model, block=block, entity=entity, resource=resource, seeds=seeds)


def slot(estimand, candidate, reference, group="fastStorage", resource="CPU"):
    return next(item for item in analysis_slots()
                if (item.estimand, item.candidate, item.reference, item.environment, item.resource)
                == (estimand, candidate, reference, group, resource))
