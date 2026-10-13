"""Thin separately versioned entry for unused seeds; no generator duplication."""
import argparse
import json
from pathlib import Path
import generate
import wrapper_global


def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--source',type=Path);p.add_argument('--baseline',type=Path);p.add_argument('--allocation',type=Path,required=True);p.add_argument('--split',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--registration',type=Path,required=True);a=p.parse_args()
    rt=wrapper_global.bootstrap(a.project,a.source,a.baseline)
    reg=json.loads(a.registration.read_text());wrapper_global.verify_registration(rt,reg)
    print(json.dumps(generate.generate(rt,a.allocation,a.split,a.out,a.registration)))

if __name__=='__main__':main()
