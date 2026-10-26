#!/usr/bin/env python3
"""Public, standard-library compact replay. No Git/model/raw-data access or overwrite.

Python >=3.9. Use: python3 -I -S -B replay_derived.py --output-dir NEW_SCRATCH
"""
import argparse
import csv
from decimal import Decimal, localcontext
import hashlib
import io
import json
from pathlib import Path
import sys

MANIFEST_SHA256='97fe4f8930f00604d2ada85f625dd7ff9b7017467d716b5e2ed875de7d6a5dad'
G1='review_revision/stage19g1_evidence/'
C1='review_revision/stage18c1_evidence/'
H1='review_revision/stage19h1_scale_context/'
SUPP='manuscript/jss/supplementary/final_evidence_supplement.tex'
NAMES=('m1_s2_robustness_24.csv','seed_sensitivity_48.csv','timetrack_memory_attribution.csv')
ROBUST_COLUMNS=['block','resource','frozen_MacroMAE_gain_percent',
    'median_candidate_reference_MAE_ratio','candidate_win_percent','ties']
SEED_COLUMNS=['block','resource','comparison','seed0_gain_percent','seed1_gain_percent',
    'seed2_gain_percent','range_percentage_points','population_SD_percentage_points','status']

class ReplayError(Exception):
    pass

def need(condition,message):
    if not condition:raise ReplayError(message)

def sha(data):return hashlib.sha256(data).hexdigest()

def serialize_csv(matrix):
    """Match the G1 UTF-8 CSV contract, including CR-only fields and final LF.

    All cells are strings. No numeric parsing/reformatting is performed here.
    Python csv.writer with LF alone would not quote a bare CR like G1 did.
    """
    need(bool(matrix),'EMPTY_TABLE')
    width=len(matrix[0]);need(width>0,'EMPTY_HEADER')
    lines=[]
    for row in matrix:
        need(len(row)==width,'RAGGED_TABLE')
        cells=[]
        for value in row:
            need(isinstance(value,str),'NON_STRING_CELL: encode the original lexeme explicitly')
            cells.append('"'+value.replace('"','""')+'"' if any(c in value for c in ',"\r\n') else value)
        lines.append(','.join(cells))
    result=('\n'.join(lines)+'\n').encode('utf-8')
    need(list(csv.reader(io.StringIO(result.decode('utf-8'),newline='')))==matrix,'CSV_ROUNDTRIP_FAILED')
    return result

def table(data):
    rows=list(csv.reader(io.StringIO(data.decode('utf-8'),newline='')))
    need(bool(rows) and len(set(rows[0]))==len(rows[0]),'BAD_CSV_HEADER')
    need(all(len(row)==len(rows[0]) for row in rows),'RAGGED_SOURCE_CSV')
    return rows[0],[dict(zip(rows[0],row)) for row in rows[1:]]

def lexical_json(data):
    return json.loads(data.decode('utf-8'),parse_int=str,parse_float=str)

def json_bytes(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')

def verified_sources(repo_root,manifest_path):
    raw=manifest_path.read_bytes()
    need(sha(raw)==MANIFEST_SHA256,'MANIFEST_HASH_MISMATCH')
    manifest=json.loads(raw.decode('utf-8'))
    need(manifest.get('schema')==1,'MANIFEST_SCHEMA_MISMATCH')
    sources={}
    for record in manifest['files']:
        rel=Path(record['path'])
        need(not rel.is_absolute() and '..' not in rel.parts,'UNSAFE_SOURCE_PATH')
        path=(repo_root/rel).resolve()
        need(repo_root in path.parents,'SOURCE_ESCAPES_ROOT')
        need(path.is_file(),'SOURCE_MISSING: '+record['path'])
        data=path.read_bytes()
        need(len(data)==record['bytes'] and sha(data)==record['sha256'],'SOURCE_HASH_MISMATCH: '+record['path'])
        need(record['path'] not in sources,'DUPLICATE_SOURCE_PATH')
        sources[record['path']]=data
    need(len(sources)==11,'SOURCE_COVERAGE_MISMATCH')
    return manifest,sources

def projected_tables(sources,payload):
    _,robust=table(sources[C1+'robust_seed_mean_cells.csv'])
    robust=[row for row in robust if row['comparison']=='M1_vs_S2']
    matrix=[ROBUST_COLUMNS]
    with localcontext() as context:
        context.prec=28
        for row in robust:
            matrix.append([row['block'],row['resource'],row['frozen_MacroMAE_gain_percent'],
                row['median_MAE_ratio'],str(Decimal(row['candidate_win_rate'])*100),row['ties']])
    need(matrix==[payload[NAMES[0]]['columns'],*payload[NAMES[0]]['rows']],'ROBUST_SOURCE_PROJECTION_MISMATCH')
    _,seeds=table(sources[C1+'seed_sensitivity.csv'])
    seed_matrix=[SEED_COLUMNS]
    for row in seeds:
        need(row['aggregate_seed_sign_variable'] in ['True','False'],'BAD_EXISTING_SEED_FLAG')
        seed_matrix.append([row['block'],row['resource'],row['comparison'],
            row['seed0_gain'],row['seed1_gain'],row['seed2_gain'],row['seed_gain_range_pp'],
            row['seed_gain_population_SD_pp'],'FLIP' if row['aggregate_seed_sign_variable']=='True' else 'stable'])
    need(seed_matrix==[payload[NAMES[1]]['columns'],*payload[NAMES[1]]['rows']],'SEED_SOURCE_PROJECTION_MISMATCH')
    return {NAMES[0]:matrix,NAMES[1]:seed_matrix}

def display(value):
    # This is display formatting only, matching the existing supplement convention.
    need(Decimal(value).is_finite(),'NONFINITE_DISPLAY_VALUE')
    return '\\evidencevalue{'+value+'}{'+format(float(value),'.6f')+'}'

def resource_label(value):
    labels={'CPU':'CPU','THROUGHPUT':'Throughput','MEMORY':'Memory','DISK_WRITE':'Disk write'}
    need(value in labels,'UNKNOWN_RESOURCE')
    return labels[value]

def supplement_fragments(payload):
    a=[];previous=None
    for row in payload[NAMES[0]]['rows']:
        r=dict(zip(ROBUST_COLUMNS,row))
        if previous is not None and r['block']!=previous:a.append(r'\addlinespace')
        previous=r['block']
        a.append(r['block']+' / '+resource_label(r['resource'])+' & '+
            ' & '.join(display(r[k]) for k in ROBUST_COLUMNS[2:5])+' & '+r['ties']+r' \\')
    b=[]
    for index,comparison in enumerate(['S2_vs_S1','M1_vs_S2']):
        if index:b.append(r'\pagebreak[4]')
        b.append(r'\multicolumn{7}{l}{\textbf{Panel '+('A: S2:S1' if index==0 else 'B: M1:S2')+r'}}\\*')
        previous=None
        for row in payload[NAMES[1]]['rows']:
            r=dict(zip(SEED_COLUMNS,row))
            if r['comparison']!=comparison:continue
            if previous is not None and r['block']!=previous:b.append(r'\addlinespace')
            previous=r['block']
            b.append(r['block']+' / '+resource_label(r['resource'])+' & '+
                ' & '.join(display(r[k]) for k in SEED_COLUMNS[3:8])+' & '+r['status']+r' \\')
    return {'m1_s2_robustness_rows.tex':('\n'.join(a)+'\n').encode('utf-8'),
        'seed_sensitivity_rows.tex':('\n'.join(b)+'\n').encode('utf-8')}

def derive(manifest,sources):
    payload=lexical_json(sources[G1+'table_payload.json'])
    need(list(payload)==list(NAMES),'G1_PAYLOAD_TABLE_ORDER_MISMATCH')
    projections=projected_tables(sources,payload)
    outputs={};checks=[]
    for name in NAMES:
        item=payload[name];matrix=projections.get(name,[item['columns'],*item['rows']])
        need(len(matrix)-1==manifest['expected_csv_rows'][name],'CSV_ROW_COUNT_MISMATCH')
        data=serialize_csv(matrix)
        need(data==sources[G1+name],'CSV_BYTES_DIFFER: '+name)
        outputs[name]=data
        checks.append(dict(file=name,rows=len(matrix)-1,columns=len(matrix[0]),
            byte_identical=True,parsed_table_identical=True,sha256=sha(data)))
    fragments=supplement_fragments(payload)
    original=[section.split(r'\endlastfoot'+'\n',1)[1].split(r'\end{longtable}',1)[0].encode('utf-8')
        for section in sources[SUPP].decode('utf-8').split(r'\begin{longtable}')[1:]]
    need(len(original)==2,'SUPPLEMENT_TABLE_COVERAGE_MISMATCH')
    for (name,data),reference in zip(fragments.items(),original):
        need(data==reference,'SUPPLEMENT_ROWS_DIFFER: '+name)
        need(sha(data)==manifest['authoritative_supplement_fragment_sha256'][name],'SUPPLEMENT_FRAGMENT_HASH_MISMATCH')
        outputs[name]=data
    for name in ['sharing_sensitivity.csv','contextual_evidence.csv']:
        columns,rows=table(sources[C1+name])
        need(len(rows)==24 and len({(r['block'],r['resource']) for r in rows})==24,'C1_CELL_COVERAGE_MISMATCH')
        data=serialize_csv([columns,*[[r[c] for c in columns] for r in rows]])
        need(data==sources[C1+name],'C1_CSV_BYTES_DIFFER: '+name)
        outputs[name]=data
    g1=lexical_json(sources[G1+'analysis.json']);h1=lexical_json(sources[H1+'analysis.json'])
    extracts=dict(numeric_encoding='Source JSON numeric lexemes retained as strings; no statistics recalculated',
        materna_attribution=g1['materna'],timetrack_memory=g1['timetrack_memory'],
        capacity_exact=g1['capacity_exact'],scale_context_summaries=h1['summaries'],
        scope='Selected existing diagnostics, not a rerun of the full saved-artifact audit')
    outputs['diagnostic_extract.json']=json_bytes(extracts)
    flips={comparison:sum(1 for row in payload[NAMES[1]]['rows'] if row[2]==comparison and row[-1]=='FLIP')
        for comparison in ['S2_vs_S1','M1_vs_S2']}
    need(flips=={'S2_vs_S1':9,'M1_vs_S2':4},'EXISTING_SEED_FLAG_COUNT_MISMATCH')
    outputs['replay_checks.json']=json_bytes(dict(status='PASS',scope='Derived-only compact-endpoint replay',
        manifest_sha256=MANIFEST_SHA256,source_hashes_verified=len(sources),csv_checks=checks,
        C1_robustness_seed_projections_exact=True,existing_seed_flip_counts=flips,
        supplement_fragments_byte_identical=True,
        output_sha256={name:sha(data) for name,data in outputs.items()},
        training=0,inference=0,new_scientific_statistics=0,historical_seal_changes=0,
        runtime=dict(python=sys.version.split()[0],implementation=sys.implementation.name),
        note='Metadata checks are newly derived; CSV/TeX outputs match authoritative bytes. No Git or historical HEAD required.'))
    return outputs

def replay(repo_root,output_dir,manifest_path=None):
    root=Path(repo_root).resolve()
    need(root.is_dir(),'SOURCE_ROOT_MISSING')
    requested=Path(output_dir).expanduser()
    need(not requested.is_symlink(),'OUTPUT_SYMLINK_REFUSED')
    destination=requested.resolve()
    need(destination!=root and root not in destination.parents,'OUTPUT_INSIDE_SOURCE_ROOT_REFUSED')
    need(destination.parent.is_dir(),'OUTPUT_PARENT_MISSING')
    need(not destination.exists() or (destination.is_dir() and not any(destination.iterdir())),
        'OUTPUT_NOT_EMPTY_OR_NOT_DIRECTORY')
    manifest_path=Path(manifest_path) if manifest_path is not None else Path(__file__).with_name('replay_sources.json')
    manifest,sources=verified_sources(root,manifest_path)
    outputs=derive(manifest,sources)
    # All source/schema/byte comparisons finish before any scratch output is written.
    destination.mkdir(exist_ok=True)
    for name,data in outputs.items():
        with (destination/name).open('xb') as stream:stream.write(data)
        need((destination/name).read_bytes()==data,'OUTPUT_WRITE_MISMATCH')
    for record in manifest['files']:
        need(sha((root/record['path']).read_bytes())==record['sha256'],'SOURCE_CHANGED_DURING_REPLAY')
    return json.loads(outputs['replay_checks.json'])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output-dir',type=Path,required=True,help='New or empty scratch directory OUTSIDE the source root')
    args=parser.parse_args()
    try:
        result=replay(args.repo_root,args.output_dir)
    except (ReplayError,OSError,ValueError,KeyError,TypeError) as error:
        print('DERIVED_REPLAY_BLOCKED: '+str(error),file=sys.stderr)
        return 2
    print(json.dumps(result,indent=2))
    return 0

if __name__=='__main__':sys.exit(main())
