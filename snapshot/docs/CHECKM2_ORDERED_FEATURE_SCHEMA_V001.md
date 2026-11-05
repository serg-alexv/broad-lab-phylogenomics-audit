# CheckM2 1.1.0 ordered feature schema

The source-only manifest is `metadata/checkm2_feature_schema_v001.json`; its SHA256 is written beside it. It contains the exact **21,242 DataFrame column names**, beginning with `Name`, and the **21,241 model-feature names** in producer order. No model, genome, FAA or pickle was loaded to build it.

| Group | Count | Model indices, zero based |
|---|---:|---|
| Metadata: A C D E F G H I K L M N P Q R S T V W Y AALength CDS | 22 | 0–21 |
| KO genes, in the packaged order | 19,999 | 22–20,020 |
| KO pathways | 416 | 20,021–20,436 |
| KO modules, in module-definition key order | 757 | 20,437–21,193 |
| KO categories | 47 | 21,194–21,240 |

The original producer assembles metadata first and then KO genes/pathways/modules/categories, removes the KO-side `Name`, and retains the metadata-side `Name` first. Module-definition key order was checked against the feature-order asset; they agree. Do not alphabetize names or KO IDs. Group and global names are unique in these exact assets.

Raw pickle storage is the mixed numeric DataFrame, not the scaled neural input. Count features are logically nonnegative integers; pathway/category/module features are membership fractions. `Name` is text; its precise pandas storage dtype is not asserted statically. The actual predictor forms `feature_vectors.iloc[:,1:].values.astype(float)`, giving the unscaled float64 model matrix. Both general models use that full matrix; MinMaxScaler transforms the full matrix; the neural network and cosine computation use the original first 20,021 scaled features. The model selector's zero-based feature 20 is **AALength**.

`AALength` sums full protein-string lengths. The twenty amino-acid counts count their uppercase letters only, so their sum may be smaller because stop/ambiguous or other preserved characters contribute to length. Do not strip stops, uppercase sequences, or require sum(AA counts) = AALength. KO counts are retained DIAMOND annotation-row counts, not a new independent orthology assertion.

The original module algorithm keeps the initial membership-list length as denominator, then removes identifiers outside the KO feature dictionary. The verified module asset has fourteen missing-KO membership occurrences and sixty-three repeated-membership occurrences. Preserve this original behavior: do not deduplicate, alter denominators, or derive a replacement module order. The schema records these exceptions and binds all three original data assets and relevant source hashes.

The supported `--dbg_vectors` flag passes the Boolean into `prediction_wf` and writes `feature_vectors_<chunk>.pkl` with pandas pickle protocol 4; the first chunk is numbered 1. The write happens after that chunk's model/postprocessing work and does not select a different model or change the feature recipe. It adds serialization/I/O work within the same resource and time gates; it is not a model-accuracy validation.

A future reader must verify the controlled run manifest/hash before reading its pickle, require exactly one expected `Name` row and this exact full column list, reject missing/extra/duplicate/reordered columns, missing/nonfinite/nonnumeric values and invalid count/fraction domains, and only then derive the float64 matrix. Do not fill absent columns with zero or compare opaque pickle bytes as a substitute for ordered numeric values. These are parser requirements, not evidence that an actual feature artifact exists yet.

Protein mode has exactly five stock report columns in auto mode: `Name`, `Completeness`, `Contamination`, `Completeness_Model_Used`, `Additional_Notes`. Its copied protein file is extensionless. Use the plan's versioned accession, not `splitext` of that copy's name, which would strip `.1`. Nine DNA-report fields remain separate original-caller provenance. No biological admission follows from this schema.
