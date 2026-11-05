# Tree 2 performance and continuation checkpoint

The checkpoint on 5 November 2026 contains **165 accepted paired defence results**, **20 computed C009 results awaiting closure and file QA**, and **734 unsearched genomes**. The 900-tip full tree has completed inference and passed the saved-output and branch-support checks. Broader phylogenetic validation, final defence rings, and the representative tree remain open. [Checkpoint counts](performance_summary.json)

## Defence performance

The export covers 370 distinct terminal stock execution receipts from 11 real-input attempts. Of those, 330 phases contribute to accepted paired results and 40 belong to C009. The nine original C008 PADLOC phases occur once in the execution table and contribute to the recovered C008 cohort. Durations are wall time inside the stock phase. Cold worker time also covers model and runtime staging, input preparation, and other worker overhead. Independent file QA and handoffs are recorded separately. [Per-genome detector timing](detector_phases.csv) · [Attempt timing](defence_attempts.csv)

| Attempt or cohort | New PADLOC / DefenseFinder phases | Predictor wall time | Cold worker wall time | File QA |
| --- | ---: | ---: | ---: | ---: |
| Real-input pilot | 5 / 5 | 70m 25s | 106m 56s | No separate duration in the exported acceptance fields |
| C001–C004, one CPU | 20 / 20 each | 178–186 min each | 249–257 min each | 72–95 min each |
| C005–C007, four CPUs | 20 / 20 each | 100–117 min each | 172–189 min each | 48–53 min each |
| Original C008 attempt | 9 / 0 | 14m 51s | 15m 23s | Pending at failure boundary |
| C008 checkpoint recovery | 11 / 20 | 67m 22s | 130m 32s | 19m 18s for all 40 saved phases |
| C009 | 20 / 20 | 81m 30s | 145m 18s | Pending |

The original C008 wrapper stopped after stock PADLOC exited successfully and omitted a CSV for zero assembled systems. The saved stock and HMMER evidence established that normal output branch. Recovery preserved nine PADLOC phases, then ran the 11 remaining PADLOC phases and all 20 DefenseFinder phases. The ledger carries the original debit once. [Attempt timing](defence_attempts.csv)

| C009 component | Measured duration |
| --- | ---: |
| 20 PADLOC phases | 1,794.720 s |
| 20 DefenseFinder phases | 3,095.404 s |
| Other cold-worker time | 3,828.351 s |
| Total cold-worker time | 8,718.475 s |
| Native process creation through retained WSL exit | 8,722.409 s |

C009's median stock phase was 87.08 s for PADLOC and 154.29 s for DefenseFinder. C009 has 40 committed engine phases and retained native and WSL exit code zero. The dispatcher failed during the handoff. The next checkpoint action is to reconcile C009's exact terminal evidence and independently audit its saved files, then close the ledger entry and reserve the next disjoint cohort. [Phase timing](detector_phases.csv) · [Retained exit and controller evidence](hardware_and_checkpoint.json)

## Remaining defence time

The observed C005–C007 start-to-next-start cycles were 4h 04m, 4h 15m, and 4h 23m per 20 genomes. Their mean projects **6.48 days of continuous work** for the 734 unsearched genomes. An illustrative V003 cycle combines C009's measured cold worker time with C008 recovery's measured QA and handoffs. It projects **5.14 days** for the same remaining genomes.

Allow roughly **five to seven days of continuous defence work after continuation resumes**, including the outstanding C009 audit. This estimate assumes similar genome sizes and filesystem performance. Controller downtime, broader tree validation, and final figure assembly have separate schedules. [Measured rates and calculation](performance_summary.json)

## Host, safeguards, and tree timing

The recorded workstation has an Intel Core i5-1240P, 12 physical cores, 16 logical processors, 15.75 GiB physical RAM, and Windows 11 Pro. The startup inventory recorded WSL application 3.0.3.0 with Ubuntu 26.04.1 under WSL2, four logical CPUs, about 3.33 GiB visible Linux RAM, and 8 GiB swap. C009 used the four-CPU stock settings with PADLOC `--cpu 4` and DefenseFinder `--workers 4`. Its preflight recorded 3.04 GiB Linux memory available and 109.92 GiB project disk space free.

C009's hard limits were 1.75 GiB summed owned Linux RSS plus private RAM, at least 1.25 GiB Linux memory available, 128 MiB combined native and retained WSL RSS, and 40 GiB free project disk space. Its sampled cohort peak was 1.344 GiB owned Linux RSS plus private RAM. The sampled native and WSL peak was about 28.1 MiB. [Host, preflight, and checkpoint record](hardware_and_checkpoint.json) · [Attempt resource measurements](defence_attempts.csv)

The six measured full900 IQ-TREE attempts account for 324,742.033 s of cumulative production wall time. The four-thread attempt and its two-thread fallback hit the 1.75 GiB guard during support assembly. The one-thread, 500M cache recovery restored the saved search and bootstrap progress and completed in 1,168.348 s, with a sampled peak of 1.644 GiB. The final tree, consensus, and all 1,000 bootstrap trees passed independent saved-output validation. The preserved scientific plan records LG+F+G4, 54 markers, 13,071 amino acid columns, and 1,000 SH-aLRT replicates. [Six IQ-TREE attempt receipts](full900_attempts.csv)

## Reproduce the export

Run the exporter against the restored evidence tree or the original project. The script reads the ledger, bound source plans, measured command and execution receipts, and typed exits. It reconciles stock phase totals with each saved attempt debit. The CSV links use project-relative paths, and the per-phase command and execution records include SHA-256 digests.

```text
python -B export_performance.py --project PATH_TO_PROJECT --output PATH_TO_EXPORT
```

On the original Windows host, `--observe-local` adds a point-in-time query of the recorded process creation identities and disk free space. The query preserves typed terminal receipts as the source of exit status. The observation packaged here was recorded on 5 November 2026 at 17:30:53 UTC. [Host and process observation](hardware_and_checkpoint.json)
