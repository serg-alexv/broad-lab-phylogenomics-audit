# Full 900-genome production phylogeny - 29 October 2026

The production inference is running on the unchanged900-genome,54-marker,13,071-amino-acid matrix. It performs a thorough maximum-likelihood search with1,000 ultrafast bootstrap and1,000 SH-aLRT replicates, including bootstrap NNI refinement. These are requested support counts; results are not yet complete.

The redundant model/resource and fast-tree diagnostic sequence was deliberately stopped under the human instruction. Its partial results and checkpoints remain preserved. No additional sample, model-selection pilot or fast-tree pilot precedes production.

The pinned IQ-TREE executable uses a fixed LG+F+G4 empirical model. This is a transparent primary choice, not a claim of best fit or model adequacy. The run uses the same matrix without likelihood gene partitions because the installed executable explicitly does not support its memory limit with partition models. The54 original partitions remain available for provenance and later QC. Model adequacy and composition sensitivity remain required before final scientific acceptance.

The production command uses one thread, a700M internal memory target, a1.75GiB owned-RSS/private-RAM guard, and1.25GiB Linux free-memory headroom. It writes stock checkpoints every30seconds and has a separate seven-day production budget. It does not inherit a short pilot deadline.

Actual startup was observed in IQ-TREE output: the900-sequence alignment was read, an initial parsimony tree was built,1,000 bootstrap samples generated, and model parameter estimation began. The first recorded likelihood was-3,090,881.646. Recorded process memory was approximately1.1GB, within its allocation.

The existing event controller was rearmed with unchanged source and configuration, and holds the exact native production process. Ordinary waiting invokes no AI model. Actual failure/completion triggers local continuation, preserving compatible checkpoints and accepted work. The visible monitor shows PRODUCTION_ML_SEARCH_AND_SUPPORT and refreshes every30seconds.

Known19-genome,3-marker and9-composition holds remain explicit. This production run does not itself grant final orthology, taxonomy, model adequacy, whole-species sampling or final-tree acceptance. Independent phylogenetic QC follows; defence processing, rings and the separate representative tree remain subsequent stages. All files remain local, with no project upload.

Evidence: metadata/full900_production_v001/Root_ACTUAL_PRODUCTION_RUNNING.json
Plan: metadata/full900_production_v001/Root_plan.json
Production prefix: analysis/phylogeny/full900_production_v001/inference/full_tree
Current progress: work/full900_production_v001/progress.json
