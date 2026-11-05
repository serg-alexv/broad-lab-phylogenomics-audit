# Supported protein-input route: conditional source admission

Decision: the original CheckM2 `--genes --threads 1 --extension .faa` route is a supported primary candidate for a separately staged workflow. Admission remains conditional on the one engineering memory diagnostic, exact caller/input bindings, and subsequent resource and semantic controls. No genome, model import, gene call or biological retry was executed for this review. No successful nucleotide-mode baseline or biological calibration is claimed.

## Exact feature recipe and its conditions

The pinned `feature_ordering.json` specifies 22 protein-derived metadata features: twenty uppercase amino-acid counts, `AALength`, and `CDS`; then 19,999 KO genes, 416 pathways, 757 modules and 47 categories. Total: **21,241**. The specific-model/cosine prefix contains 22 + 19,999 = **20,021** features. `vector_array[:,20]` is **AALength**, and the postprocessor's `AA_Ratio` divides that length by mean predicted completeness. It is not DNA coding density.

`metadata.MetadataCalculator` reads the supplied FAA for all twenty counts, total amino-acid length and CDS count. The same FAA records, IDs, case, stop characters, order and genome basename, combined with the same DIAMOND hit multiset, feature-order assets, database, models and options, therefore enter the same source-defined feature recipe. The general models receive the full unscaled vector; the scaler receives the full vector; the neural network and cosine path use their original 20,021-feature slices. Source conditions are not an observed numerical-equivalence result.

Stock gene-input mode skips the nine gene-calling Managers. At one thread, metadata calculation retains one Manager, one progress writer and one worker, plus the ML-loaded parent: four Python processes at that phase, apart from external programs. Later DIAMOND, postprocessing and full prediction memory are not established by an initial topology proof.

## Model-free sequential gene stage

Use the unchanged `checkm2.prodigal.ProdigalRunner` in a separate sequential process, passing the acquired DNA unchanged and `supplied_coding_table=None`. This module's static import graph includes NumPy/Pandas and utility modules, but no TensorFlow/Keras/LightGBM/scaler load. A future runtime must verify that observation; this review did not import it.

The original runner checks tables **4 then 11**. It uses Prodigal `-p single` at at least 100,000 input bases, otherwise `-p meta`, with `-q -m -f gff -g <table> -a <FAA> -d <FNA> -i <DNA>` and GFF stdout redirection. A missing/empty FAA from `single` triggers the author's `meta` fallback. Table 11 is the default winner; table 4 wins only when its coding-density advantage is greater than 0.05 and its density is greater than 0.7. Do not replace this with a fixed translation table or a newly implemented selector.

Retain the selected FAA exactly and the original ten returned fields: basename, selected table, selected coding density, caller N50, mean gene length, DNA bases, CDS count, GC, contig count and maximum contig length. The runner deletes candidate results and the selected GFF/FNA before returning. Those raw files are **not retained**. Do not intercept, monkeypatch or alter cleanup. Any independent acquired-DNA sequence-QC sidecar must remain separately named and attributed; it does not replace the caller's returned values. Later coordinate annotation requiring GFF is a distinct gated stage and must verify FAA consistency if it calls genes again.

## Report and artifact differences are explicit

Protein mode does not append these nine nucleotide-mode columns: `Translation_Table_Used`, `Coding_Density`, `Contig_N50`, `Average_Gene_Length`, `Genome_Size`, `GC_Content`, `Total_Coding_Sequences`, `Total_Contigs`, `Max_Contig_Length`. Preserve them only in the separate original-caller sidecar. Do not manufacture a nucleotide-mode CheckM2 report or declare its missing columns equivalent.

The gene-input branch copies the supplied FAA into `output/protein_files/<basename>` **without `.faa`**, while metadata and DIAMOND read the original supplied FAA path. Its basename must match the acquired assembly's existing name. A route-specific collector and comparison specification must account for this layout and the nine absent report columns. The still-unapplied nucleotide-baseline FASTA-format control is not silently reusable for this new route.

## Engineering protocol and rejected transfer

The one proposed diagnostic has separate fresh default-fork interpreters: the exact initial matched model load followed by up to nine incremental Managers, then a comparison with the same initial model load and one Manager plus two held lightweight children. There are no genomes, FAAs, Predictor initialization, original worker callbacks, Prodigal or DIAMOND. Both keep the existing 2 GiB summed-RSS stop, 1 GiB Linux headroom, two CPUs and 600-second per-arm bound. PSS/private resident totals are descriptive only. Manager/group/native/IPC/image/lock closure is required before any next stage. Initial topology measurements cannot admit a whole biological run.

Forkserver is not this chosen comparison. It has separate transfer blockers: child preparation can replay the console main path and reimport TensorFlow, and CheckM2 uses private bound worker/writer methods. The pinned standard method reducer retrieves the original unmangled method name, while Python stores those attributes under `_Predictor__...`; a lightweight parent entry alone cannot fix that lookup. No monkeyreducer or class patch is admitted. See [Python 3.12 process contexts](https://docs.python.org/3.12/library/multiprocessing.html#contexts-and-start-methods) and its [private-attribute `getattr` rule](https://docs.python.org/3.12/library/functions.html#getattr). The source audit receipt binds the exact CheckM2/CPython files and this design decision.
