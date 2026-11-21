"""Create separately registered descriptive transfer cases; never selects a primary claim."""
import argparse,json
from pathlib import Path
from run_local import ROOT,hashes
p=argparse.ArgumentParser();p.add_argument('--primary-lock',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--frames',type=int,default=256);a=p.parse_args()
l=json.loads(a.primary_lock.read_text());pr=json.loads((ROOT/'protocol/protocol.json').read_text())
if l['source_hashes']!=hashes():raise ValueError('Sources differ from primary lock')
if a.frames<1:raise ValueError('Positive sample size required')
l['cells']=pr['transfer_cells'];l['frames_per_cell']=a.frames;l['primary_baseline_by_cell']={str(c['id']):next(iter(l['primary_baseline_by_cell'].values())) for c in l['cells']};l['registration']='separate descriptive transfer, not a primary claim or new selection';l['statistical_contract']='Report paired outcomes and model-boundary failures descriptively; do not reinterpret primary multiplicity correction.'
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(l,indent=2))
