from pathlib import Path
import hashlib,json,datetime
r=Path(r'C:\Users\wheel\Documents\Codex\2026-10-26\referenced-chatgpt-conversation-this-is-an\outputs\TREE2_WD_20261026')
a=r/'analysis/pilot10/runs/20261026T161347Z-c4e91c88'
b=r/'analysis/pilot10/runs/20261026T161747Z-cluster-resume-f688a380'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((a/'mmseqs_easy_cluster.exit.json').read_text())
new=json.loads((b/'mmseqs_easy_cluster.exit.json').read_text())
receipt=json.loads((b/'pilot_exit_receipt.json').read_text())
obj={'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_run':a.relative_to(r).as_posix(),'original_error':(a/'mmseqs_easy_cluster.stderr').read_text().strip(),'original_sampled_peak_group_rss_bytes':old['sampled_peak_group_rss_bytes'],'finding':'MMseqs automatic-k regular prefilter failed its1G memory admission estimate; observed RSS was35.5MB. Address-space exhaustion is not established by the evidence.','one_bounded_correction':'Explicit -k5; identity,coverage,clustering,thread,split-memory,RSS,address-space,and timeout budgets unchanged. Smaller-k sensitivity tradeoff recorded.','official_source':'https://mmseqs.com/latest/userguide.pdf','documentation_sections':'k-mer length, p50; memory consumption, pp63-64','resumed_run':b.relative_to(r).as_posix(),'status':receipt['status'],'combined_input_sha256_original':h(a/'all_proteins.faa'),'combined_input_sha256_resumed':h(b/'all_proteins.faa'),'annotations_preserved':receipt['annotations'],'new_sampled_peak_group_rss_bytes':new['sampled_peak_group_rss_bytes'],'new_elapsed_seconds':new['elapsed_seconds'],'new_exit_code':new['exit_code'],'owned_process_group_empty':new['owned_group_empty'],'summary':receipt['summary'],'scope':'Exploratory10-genome pilot only; no broad marker acceptance,no biologicalQC,no defence calls.'}
(r/'analysis/pilot10/mmseqs_failure_and_correction.json').write_text(json.dumps(obj,indent=2))
print(json.dumps({'status':obj['status'],'input_sha256':obj['combined_input_sha256_resumed'],'annotation_count':len(obj['annotations_preserved'])}))