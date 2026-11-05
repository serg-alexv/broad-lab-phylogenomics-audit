"""Source-only review of deterministic priority-1 components 4 through 6.

Never imports scientific tools, runs analyses, or changes an accepted review.
HTTP responses are SHA-bound; short excerpts and factual pattern checks are retained.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin
import concurrent.futures
import datetime
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'analysis/sequence_qc/d64e016face251f1/curation_source_review/3fa9c62b41bb4a54'
FIRST = ROOT / 'analysis/sequence_qc/d64e016face251f1/nomenclature_source_review/priority1_first3_20261026'
OUT = ROOT / 'analysis/sequence_qc/d64e016face251f1/nomenclature_source_review/priority1_next3_20261027_v1'
STATE = ROOT / 'state/ani_nomenclature_next3_progress.json'
EXPECTED_FIRST = '79d3d67b690a123d1fb13382fff613dfcc44ae61345d15f8caf2faae4672bfd8'
EXPECTED_INPUT = 'd52295b4a69c03746ac51f8a289a568ea8a5776572202099713586d33d932f53'
sys.path.insert(0, str(ROOT / 'tools/python_lib'))
import requests


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w', encoding='utf-8') as handle:
        json.dump(obj, handle, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def progress(detail, status='SOURCE_REVIEW_IN_PROGRESS', done=0):
    save(STATE, dict(status=status, updated_utc=utc(), detail=detail,
         done=done, total=3, reviewer='checkm2_resolve',
         scope='SOURCE_ONLY_NO_RECOMPUTATION', scientific_worker_running=False,
         requires_user_input=False,
         no_label_selection_pruning_or_biological_qc_change=True,
         artifact_directory=OUT.relative_to(ROOT).as_posix()))


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.skip:
            self.skip -= 1

    def handle_data(self, text):
        if not self.skip:
            self.parts.append(text)


def verify_manifest(directory, expected):
    if sha(directory / 'manifest.json') != expected:
        raise RuntimeError('Accepted manifest changed: ' + str(directory))
    rows = read(directory / 'manifest.json')['files']
    for item in rows:
        target = (directory / item['path']).resolve()
        if not target.is_relative_to(directory.resolve()):
            raise RuntimeError('Manifest path escaped directory')
        if target.stat().st_size != item['bytes'] or sha(target) != item['sha256']:
            raise RuntimeError('Accepted source artifact differs: ' + str(target))
    return rows


def check_host(url):
    host = urlparse(url).hostname or ''
    if urlparse(url).scheme != 'https' or not any(
        host == domain or host.endswith('.' + domain)
        for domain in ('dsmz.de', 'ncbi.nlm.nih.gov', 'jcm.riken.jp')):
        raise RuntimeError('Source host outside primary-source allowlist: ' + host)


def fetch(item):
    name, url, needle, patterns = item
    path = OUT / 'sources' / (name + '.json')
    if path.exists():
        prior = read(path)
        if prior['requested_url'] != url:
            raise RuntimeError('Existing source URL differs')
        return prior
    # Reuse an already accepted first-three receipt, if this exact URL overlaps.
    for cached in (FIRST / 'sources').glob('*.json'):
        previous = read(cached)
        if previous.get('requested_url') == url:
            result = dict(previous, source_id=name, reused_receipt_path=cached.relative_to(ROOT).as_posix(),
                          reused_receipt_sha256=sha(cached), reused_without_fetch=True)
            save(path, result)
            return result
    result = dict(source_id=name, requested_url=url, retrieved_utc=utc(),
                  scope='SOURCE_PAGE_NOT_GENOME', reused_without_fetch=False)
    try:
        with requests.Session() as session:
            session.headers['User-Agent'] = 'Tree2-WD-bounded-source-review/2.0'
            target = url
            for attempt in range(4):
                check_host(target)
                response = session.get(target, timeout=(15, 40), allow_redirects=False, stream=True)
                if response.status_code in (301, 302, 303, 307, 308):
                    target = urljoin(target, response.headers['Location'])
                    check_host(target)
                    response.close()
                    continue
                raw = bytearray()
                for block in response.iter_content(65536):
                    raw.extend(block)
                    if len(raw) > 4 * 1024 * 1024:
                        raise RuntimeError('Source exceeds 4 MiB bound')
                break
            else:
                raise RuntimeError('Redirect limit exceeded')
            parser = Text()
            parser.feed(bytes(raw).decode(response.encoding or 'utf-8', errors='replace'))
            text = ' '.join(' '.join(parser.parts).split())
            match = re.search(needle, text, re.I)
            result.update(final_url=response.url, http_status=response.status_code,
                response_bytes=len(raw), response_sha256=hashlib.sha256(raw).hexdigest(),
                content_type=response.headers.get('Content-Type'),
                last_modified=response.headers.get('Last-Modified'),
                raw_bounded_excerpt=' '.join(text[match.start():].split()[:24]) if match else '',
                excerpt_word_limit=24, response_body_retained=False,
                source_readable=response.status_code == 200 and bool(match),
                factual_pattern_checks={key: bool(re.search(pattern, text, re.I)) for key, pattern in patterns.items()})
            if 'efetch.fcgi' in url and response.status_code == 200:
                articles = []
                for article in ET.fromstring(raw).findall('.//PubmedArticle'):
                    pmid = article.findtext('.//MedlineCitation/PMID')
                    title = ''.join(article.find('.//ArticleTitle').itertext())
                    abstract = ' '.join(''.join(n.itertext()) for n in article.findall('.//AbstractText'))
                    articles.append(dict(pmid=pmid, title=title,
                        doi=[n.text for n in article.findall('./PubmedData/ArticleIdList/ArticleId') if n.attrib.get('IdType') == 'doi'],
                        abstract_sha256=hashlib.sha256(abstract.encode()).hexdigest(),
                        abstract_bounded_excerpt=' '.join(abstract.split()[:24]),
                        abstract_full_text_retained=False))
                # The title and identifier facts support precise attribution; no full abstract is copied.
                if {article['pmid'] for article in articles} != {'32250238','33112225','37433981','37755156','38651909'}:
                    raise RuntimeError('The five requested primary records are not exactly present')
                result['articles'] = articles
                result['doi_selection_rule'] = 'PubmedData/ArticleIdList/ArticleId; cited-reference DOIs excluded'
    except Exception as error:
        result.update(source_readable=False, error=repr(error))
    save(path, result)
    return result


def main():
    if os.environ.get('COMPUTERNAME', '').upper() != 'WD':
        raise RuntimeError('WD-only source review')
    verify_manifest(FIRST, EXPECTED_FIRST)
    if (OUT / 'commit.json').exists():
        committed = read(OUT / 'commit.json')
        rows = verify_manifest(OUT, committed['manifest_sha256'])
        print(json.dumps(dict(status='VERIFIED_SOURCE_ONLY_REVIEW_REUSE_NO_FETCH',
              manifest_sha256=committed['manifest_sha256'], artifacts=len(rows),
              first3_manifest_sha256=EXPECTED_FIRST)))
        return
    accepted = verify_manifest(INPUT, EXPECTED_INPUT)
    components = sorted((row for row in read(INPUT / 'component_reviews.json') if row['priority'] == 1),
                        key=lambda row: row['component_id'])[3:6]
    assert [row['component_id'] for row in components] == ['ANI_REVIEW_054', 'ANI_REVIEW_059', 'ANI_REVIEW_064']
    members = {accession for component in components for accession in component['members']}
    sources = [row for row in read(INPUT / 'source_evidence.json') if row['accession'] in members]
    progress('Verifying preserved first3 artifacts, accepted inputs, and nine cached genome source records')
    for row in sources:
        report = ROOT / row['report_path']
        receipt = ROOT / 'raw' / row['accession'] / 'acquisition_receipt.json'
        if sha(report) != row['report_sha256'] or sha(receipt) != row['acquisition_receipt_sha256']:
            raise RuntimeError('Cached genome metadata identity changed: ' + row['accession'])
        dna = [entry for entry in read(receipt)['files'] if entry['path'].endswith('.fna')]
        if len(dna) == 1:
            with (ROOT / 'raw' / row['accession'] / dna[0]['path']).open('rb') as handle:
                row['cached_first_fasta_header_read_only'] = handle.readline().decode('ascii').strip()
            row['whole_fasta_rehashed_by_this_review'] = False
    save(OUT / 'accepted_inputs.json', dict(created_utc=utc(), source_only=True,
         input_manifest_sha256=EXPECTED_INPUT, first3_manifest_sha256=EXPECTED_FIRST,
         accepted_artifacts_verified=accepted, accepted_first3_artifacts_verified=31,
         selection='PRIORITY1_SORT_BY_COMPONENT_ID_ZERO_BASED_SLICE_3_6',
         component_ids=[row['component_id'] for row in components], components=components,
         genome_source_records=sources,
         type_anchor_baseline='SOURCE_ASSERTIONS_ONLY_UNTIL_INDEPENDENT_NOMENCLATURE_AND_IDENTIFIER_REVIEW'))
    taxa = [
        ('argentoratensis', 'lactiplantibacillus-argentoratensis', 271881, {'DSM16365':r'DSM\s+16365','correct_name':r'Taxonomic status:\s+correct name'}),
        ('plantarum', 'lactiplantibacillus-plantarum', 1590, {'DSM20174':r'DSM\s+20174','ATCC14917':r'ATCC\s+14917'}),
        ('mundtii', 'enterococcus-mundtii', 53346, {'DSM4838':r'DSM\s+4838','ATCC43186':r'ATCC\s+43186'}),
        ('spodopteracolus', 'enterococcus-spodopteracolus', 3034501, {'not_validly_published':r'Nomenclatural status:\s+not validly published','preferred_not_correct':r'preferred name \(not correct name\)','no_discernible_protologue':r'lacks a discernible description'}),
        ('mictus', 'aerococcus-mictus', 2976810, {'UMB3440':r'UMB3440','DSM115699':r'DSM\s+115699','ATCCTSD301':r'ATCC\s+TSD-301'}),
        ('tenax', 'aerococcus-tenax', 3078812, {'UMB3669':r'UMB3669','DSM115700':r'DSM\s+115700','ATCCTSD302':r'ATCC\s+TSD-302'})]
    urls = []
    for key, slug, taxid, checks in taxa:
        urls.append((key + '_lpsn', 'https://lpsn.dsmz.de/species/' + slug,
                     r'Nomenclatural status:' if key == 'spodopteracolus' else r'Type strain:', checks))
        urls.append((key + '_ncbi', 'https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=' + str(taxid) + '&mode=Info',
                     r'current name', {'type_statement':r'type strain of', 'IIL_Cl25':r'IIL-Cl25'} if key == 'spodopteracolus' else {'type_statement':r'type strain of'}))
    for key, number in [('argentoratensis',16365),('plantarum',20174),('mundtii',4838),('mictus',115699),('tenax',115700)]:
        urls.append((key + '_dsm', 'https://www.dsmz.de/collection/catalogue/details/culture/DSM-' + str(number),
                     r'DSM No.', {'type_culture':r'Type strain', 'CP132985':r'CP132985'} if key == 'mictus' else {'type_culture':r'Type strain'}))
    urls.append(('argentoratensis_jcm16169', 'https://www.jcm.riken.jp/cgi-bin/jcm/jcm_number?JCM=16169',
                 r'16169', {'DSM16365':r'DSM\s+16365','CIP108320':r'CIP\s+108320','type_strain':r'Type strain'}))
    urls.append(('primary_revisions_pubmed_xml', 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=32250238,33112225,37433981,37755156,38651909&retmode=xml',
                 r'Proposal', {'all_five_ids':r'38651909'}))
    save(OUT / 'input_spec.json', dict(schema=1, created_utc=utc(), selection_slice=[3,6],
         expected_component_ids=[row['component_id'] for row in components],
         accepted_input_manifest_sha256=EXPECTED_INPUT, preserved_first3_manifest_sha256=EXPECTED_FIRST,
         source_request_count_bound=19, response_byte_bound=4194304, http_workers=3,
         no_github=True, no_new_genomes=True, no_biological_computation=True,
         source_requests=[dict(source_id=a,url=b,needle=c,factual_patterns=d) for a,b,c,d in urls]))
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(fetch, urls):
            results.append(result)
            progress('Retained primary source receipts ' + str(len(results)) + '/' + str(len(urls)))
    save(OUT / 'source_retrieval_summary.json', dict(created_utc=utc(), source_only=True,
         sources=results, source_count=len(results), readable_count=sum(row['source_readable'] for row in results),
         reused_accepted_receipt_count=sum(row.get('reused_without_fetch',False) for row in results),
         cached_genome_source_records_reused=9, no_new_genomes_downloaded=True))
    progress('Source pages retrieved; exact nomenclature/type relation assessment pending',
             'SOURCE_PAGES_RETRIEVED_REVIEW_PENDING')
    print(json.dumps(dict(output=str(OUT), source_count=len(results),
                         readable_count=sum(row['source_readable'] for row in results))))


if __name__ == '__main__':
    main()
