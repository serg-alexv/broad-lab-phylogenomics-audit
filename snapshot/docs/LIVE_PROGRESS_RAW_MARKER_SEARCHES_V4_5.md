# Raw marker-search progress

V4.5 adds a current-batch raw marker-search count separately from fully measured
CheckM1 QC genomes. It derives the batch folder from the bound current plan and
the producer's batch/log path, reads the staged accession list, and scans only
that batch's existing `HMMER_receipts/*.json` files.

A completed raw search requires `hmmsearch`, exactly one `--domtblout`, numeric
`actual_exit_code=0`, and a query accession present in the staged batch. The
query and domain-output accession must match. Duplicate successful commands
for one accession count once. Probes, index/fetch commands, nonzero exits,
started-only receipts and malformed/partial files do not increase the count.
Unreadable records are reported; missing or mismatched batch evidence stays
unknown. HMMER output files, protein sequences and marker databases are not
opened by the counter. RAM-scratch query paths are parsed as text only.

All JSON reads use shared WRITE and DELETE access, so the observer does not
block live atomic receipt writers. The display refreshes every30 seconds and
starts no extra daemon or scientific process. It does not change the native
producer's measured-QC count, scientific gate, admission or controller.

During verification the counter first showed18/18 successful raw searches while
fully measured QC was0/919. The producer then completed batch analyze and QA
and reported18/919 with genome processing false pending Root review. The
replacement display followed those real states. Raw search success alone did
not promote a genome to a QC estimate or final panel acceptance.

Original V4.4 sources remain preserved. The replacement GUI became visible and
produced two actual frames before the old GUI was closed using its retained,
creation-matched process handle. Launch, visible-console, cadence, exit and
synthetic shared-reader receipts are in
`metadata/monitor_checkm1_raw_display_v001`.
