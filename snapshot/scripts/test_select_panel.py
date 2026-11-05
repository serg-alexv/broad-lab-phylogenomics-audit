"""Targeted QC regression checks; source fixtures never run acquisition."""
import copy
import json
from pathlib import Path
import select_panel as m

ROOT = Path(__file__).resolve().parents[1]


def main():
    checks = []
    def check(name, condition):
        assert condition, name
        checks.append(name)
    source = m.source_provenance
    check("snake genome_notes MAG", source({"assembly_info": {"genome_notes": ["derived from metagenome"]}})["is_mag"])
    check("camel genomeNotes MAG", source({"assemblyInfo": {"genomeNotes": ["derived from metagenome"]}})["is_mag"])
    def attr(name, value):
        return {"assemblyInfo": {"biosample": {"attributes": [{"name": name, "value": value}]}}}
    check("investigation type MAG", source(attr("investigation_type", "metagenome-assembled genome"))["is_mag"])
    check("investigation type SAG", source(attr("investigation_type", "single amplified genome"))["is_sag"])
    check("affirmative metagenomic flag", source(attr("metagenomic", "true"))["is_mag"])
    check("false metagenomic is not MAG", not source(attr("metagenomic", "false"))["is_mag"])
    check("false flag does not prove isolate", source(attr("metagenomic", "false"))["status"] == "HOLD_SOURCE_UNRESOLVED")
    check("metagenomic source field MAG", source(attr("metagenomic source", "food fermentation metagenome"))["is_mag"])
    check("unknown metagenomic source not MAG", not source(attr("metagenome_source", "not applicable"))["is_mag"])
    check("MIMAG package recognized", source({"assemblyInfo": {"biosample": {"package": "MIMAG.human-gut.6.0"}}})["is_mag"])
    check("MISAG model recognized", source({"assemblyInfo": {"biosample": {"models": ["MISAG"]}}})["is_sag"])
    check("mixed environmental package not MAG", not source({"assemblyInfo": {"biosample": {"models": ["MIGS/MIMS/MIMARKS.human-gut"]}}})["is_mag"])
    check("project-title metagenome ignored", not source({"assemblyInfo": {"bioprojectLineage": [{"bioprojects": [{"title": "metagenome-assembled genome study"}]}]}})["is_mag"])
    check("explicit isolate supported", source(attr("sample_type", "isolate"))["isolate_source_supported"])
    check("camel atypical true excluded", source({"assemblyInfo": {"atypical": {"isAtypical": True}}})["is_atypical"])
    check("camel atypical false not excluded", not source({"assemblyInfo": {"atypical": {"isAtypical": False}}})["is_atypical"])
    check("explicit uncultivated excluded", source(attr("cultured", "false"))["is_uncultivated"])
    base = json.loads((ROOT / "metadata/reference_probe.json").read_text())["reports"][0]
    tax = m.load_taxonomy(ROOT / "metadata/taxonomy_map.json")
    check("known reference source metadata pass", m.normalize(base, tax, [])['metadata_qc'] == 'QC_METADATA_PASS')
    record = copy.deepcopy(base); del record['checkm_info']['contamination']
    check("missing contamination remains pending", m.normalize(record, tax, [])['metadata_qc'] == 'QC_PENDING')
    record['checkm_info']['contamination'] = 0
    check("explicit zero contamination preserved", m.normalize(record, tax, [])['metadata_qc'] == 'QC_METADATA_PASS')
    record['checkm_info']['contamination'] = 5.1
    check("contamination threshold preserved", m.normalize(record, tax, [])['metadata_qc'] == 'EXCLUDED')
    record = copy.deepcopy(base); record['assembly_info']['biosample']['attributes'].append({'name': 'investigation_type', 'value': 'single amplified genome'})
    check("SAG excluded despite type material", 'mag_or_single_cell' in m.normalize(record, tax, [])['exclusion_reasons'])
    record = copy.deepcopy(base); record['assembly_info']['assembly_status'] = 'suppressed'
    check("suppression excluded", m.normalize(record, tax, [])['metadata_qc'] == 'EXCLUDED')
    rows = json.loads((ROOT / 'metadata/candidates_qc.json').read_text()); panel = m.choose_panel(rows, 1000)
    check("eligible species represented in provisional selection", len({r['species_taxid'] for r in panel}) == len({r['species_taxid'] for r in rows if r['metadata_qc'] != 'EXCLUDED'}))
    check("biosamples unique in provisional selection", len({r['biosample'] for r in panel if r['biosample']}) == sum(bool(r['biosample']) for r in panel))
    check("pilot prefix covers five families", len({r['family'] for r in panel[:5]}) == 5)
    receipt = {'created_utc': m.utcnow(), 'status': 'PASS', 'count': len(checks), 'checks': checks,
               'scope': 'Structured source and metadata-selection regression checks; no acquisition or independent biology',
               'normalizer_sha256': m.sha256(ROOT / 'scripts/select_panel.py'), 'test_sha256': m.sha256(__file__)}
    m.atomic_json(ROOT / 'checkpoints/selection_checks.json', receipt)
    print(json.dumps({'status': 'PASS', 'count': len(checks)}))


if __name__ == '__main__': main()
