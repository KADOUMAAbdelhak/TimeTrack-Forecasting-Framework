"""Pre-result catalogue of the v0.3 analysis slots and compatible data slices."""

from dataclasses import dataclass
from itertools import product

from ..identity import RESOURCES, SCOPES, ScientificIdentity, read_config
from ..transfer.design import MatrixEntry, transfer_matrices

CONFIG = read_config()
SPEC = CONFIG["inference_spec"]
GROUPS = tuple(SPEC["groups"])
EXTERNAL = GROUPS[:2]
TRACES = ("Materna-T1", "Materna-T2", "Materna-T3")
BLOCKS = tuple(CONFIG["blocks"])
FOLDS = tuple(CONFIG["folds"])
CORE = tuple(CONFIG["core_seeds"])
SECONDARY = tuple(CONFIG["secondary"]["seeds"])
DETERMINISTIC = (None,)
SEED0 = (0,)
COMMON_CONTEXT = "frozen v1 H64 M1-selected context, shared by both arms"
_HISTORICAL_CONTEXT = "historical arm-specific selected contexts; exact matched test support"


def blocks_for(group):
    return TRACES if group == "Materna" else (group,)


def cohort_for(group, reduced=False):
    blocks = blocks_for(group)
    if reduced:
        return tuple(CONFIG["modern"]["cohorts"][group])
    cohorts = [tuple(CONFIG["blocks"][block]["entities"]) for block in blocks]
    if any(entities != cohorts[0] for entities in cohorts[1:]):
        raise RuntimeError("Temporal traces must share exact frozen VM rank order")
    return cohorts[0]


@dataclass(frozen=True, slots=True)
class AnalysisSlot:
    analysis_id: str
    estimand: str
    candidate: str
    reference: str
    environment: str
    resource: str
    seeds: tuple[int | None, ...]
    reference_seeds: tuple[int | None, ...]
    context_rule: str
    cohort_definition: str
    cohort: tuple[str, ...]
    blocks: tuple[str, ...]
    family: str | None = None
    correction: str | None = None
    predicted_direction: str | None = None
    match_context: bool = True
    interval: bool = False
    transfer: MatrixEntry | None = None

    @property
    def inferential(self):
        return self.family is not None


def _slot(kind, candidate, reference, group, resource, seeds=CORE, *, family=None,
          direction=None, reduced=False, context=COMMON_CONTEXT, match_context=True,
          interval=False, transfer=None, reference_seeds=None):
    cohort = cohort_for(group, reduced)
    return AnalysisSlot(
        transfer.test_id if transfer else f"{kind}/{candidate}/{reference}/{group}/{resource}",
        kind, candidate, reference, group, resource, seeds,
        seeds if reference_seeds is None else reference_seeds, context,
        "first 10 frozen V2-ranked VMs" if reduced else (
            "seven frozen TimeTrack machines" if group == "TimeTrack" else
            "same 35 frozen ranked VMs in all three traces" if group == "Materna" else
            "35 frozen ranked VMs"),
        cohort, blocks_for(group), family, ("BH" if transfer else "Holm") if family else None,
        direction, match_context, interval or family is not None, transfer,
    )


def subset_key(scope, tasks):
    return ("M0" if scope == "own" else "M1") + "/" + "+".join(tasks)


def analysis_slots():
    for group, resource in product(GROUPS, RESOURCES):
        yield _slot("D", "M1", "S2", group, resource, family="primary",
                    direction="positive" if resource in SPEC["m1_predicted_penalty"] else None)
        yield _slot("I", "M1:S2", "M0:S1", group, resource, family="primary")
        yield _slot("Spearman", "K(M1)", "D(M1:S2)", group, resource,
                    family="gradient_association", direction="positive")
    for group, resource in product(EXTERNAL, RESOURCES):
        for family, candidate in (("PCGrad", "PCGrad-M1"), ("GradNorm", "GradNorm-M1"),
                                  ("checkpoint", "M1-task-selected")):
            yield _slot("D", candidate, "M1", group, resource, SECONDARY, family=family, direction="negative")
            yield _slot("R_persist", candidate, "persistence", group, resource, SECONDARY,
                        reference_seeds=DETERMINISTIC, match_context=False,
                        context="frozen v1 M1 context; persistence on matched test origins")

    for matrix in transfer_matrices():
        for entry in matrix.entries:
            subset = subset_key(entry.scope, entry.subset)
            candidate, reference = ((subset, entry.comparator) if entry.estimand == "F"
                                    else (entry.comparator, subset))
            yield _slot(entry.estimand, candidate, reference, entry.block, entry.target_task, SECONDARY,
                        family=matrix.matrix_id if entry.estimand == "F" else None, interval=True, transfer=entry)

    for group, resource in product((*BLOCKS, "Materna"), RESOURCES):
        for candidate, reference in (("S2", "S1"), ("M1", "M0"), ("M0", "S1"), ("M0-H128", "S1")):
            yield _slot("D", candidate, reference, group, resource)
        if group not in GROUPS:
            yield _slot("D", "M1", "S2", group, resource)
        for model in ("S1", "S2", "M0", "M1", "M0-H128"):
            yield _slot("R_persist", model, "persistence", group, resource, reference_seeds=DETERMINISTIC,
                        context="model at frozen v1 M1 context; persistence on matched test origins",
                        match_context=False)
    for block, resource in product(BLOCKS, RESOURCES):
        for reference in ("S2-common-v1", "S2-v1"):
            yield _slot("D", "M1-H129-v1", reference, block, resource, SECONDARY,
                        context=_HISTORICAL_CONTEXT, match_context=False)
        yield _slot("D", "M1-H64-v1", "S2-common-v1", block, resource, SECONDARY)
        yield _slot("D", "Ridge-ARX", "Ridge-AR", block, resource, DETERMINISTIC)
        for model, seeds in (("Ridge-AR", DETERMINISTIC), ("Ridge-ARX", DETERMINISTIC),
                             ("M1-H129-v1", SECONDARY), ("M1-H64-v1", SECONDARY),
                             ("S2-common-v1", SECONDARY), ("S2-v1", SECONDARY)):
            yield _slot("R_persist", model, "persistence", block, resource, seeds,
                        reference_seeds=DETERMINISTIC, match_context=False,
                        context="historical arm context; persistence on exact matched test origins")
    for group, resource in product(EXTERNAL, RESOURCES):
        yield _slot("D", "LightGBM-all", "LightGBM-own", group, resource, SEED0)
        for model in ("LightGBM-all", "LightGBM-own"):
            yield _slot("R_persist", model, "persistence", group, resource, SEED0,
                        reference_seeds=DETERMINISTIC, match_context=False,
                        context="frozen v1 M1 context; persistence on matched test origins")
        for family in CONFIG["modern"]["families"]:
            yield _slot("D", f"{family}-shared", f"{family}-independent", group, resource, SEED0, reduced=True)
            for variant in ("shared", "independent"):
                yield _slot("R_persist", f"{family}-{variant}", "persistence", group, resource, SEED0,
                            reference_seeds=DETERMINISTIC, match_context=False, reduced=True,
                            context="frozen v1 M1 context; persistence on matched test origins")


def model_slices(slot):
    """Exact normalised model keys and seed slices needed by a slot."""
    if slot.estimand == "I":
        return tuple((model, slot.seeds) for model in ("M1", "S2", "M0", "S1"))
    if slot.estimand == "Spearman":
        return (("M1", slot.seeds), ("S2", slot.seeds))
    return ((slot.candidate, slot.seeds), (slot.reference, slot.reference_seeds))


def expected_identity(cell):
    """Translate normalised v0.3 model labels into exact final journal identities."""
    model, target = cell.model, cell.resource
    prefix = (cell.block, cell.entity, cell.fold, cell.seed, "final")
    width = CONFIG["lstm"]["primary_hidden_size"]
    if model in SCOPES:
        tasks = (target,) if model in ("S1", "S2") else RESOURCES
        return ScientificIdentity(*prefix, "core", model, tasks, SCOPES[model], width, "baseline")
    if model == "M0-H128":
        return ScientificIdentity(*prefix, "capacity", "M0", RESOURCES, "own",
                                  CONFIG["lstm"]["m0_capacity_hidden_size"], "baseline")
    if model in ("PCGrad-M1", "GradNorm-M1"):
        arm = model.split("-")[0].lower()
        return ScientificIdentity(*prefix, arm, "M1", RESOURCES, "all", width, arm)
    if model == "M1-task-selected":
        return ScientificIdentity(*prefix, "checkpoint_request", "M1", (target,), "all", width, "task_selected")
    if model.startswith(("M0/", "M1/")):
        formulation, subset = model.split("/", 1)
        tasks = tuple(subset.split("+"))
        arm = {2: "pairwise", 3: "leave_one_out"}[len(tasks)]
        if target not in tasks:
            raise ValueError("Transfer cell target is not retained by its subset")
        return ScientificIdentity(*prefix, arm, formulation, tasks, SCOPES[formulation], width, "baseline")
    if model in ("LightGBM-all", "LightGBM-own"):
        return ScientificIdentity(*prefix, "lightgbm", "LightGBM", (target,),
                                  model.split("-")[1], None, "selected")
    for family, spec in CONFIG["modern"]["families"].items():
        if model in (f"{family}-shared", f"{family}-independent"):
            variant = model.rsplit("-", 1)[1]
            tasks = RESOURCES if variant == "shared" else (target,)
            return ScientificIdentity(*prefix, "modern", family, tasks, spec["scope"], None, variant)
    return None
