#!/usr/bin/env python3
"""UNIQUE ownership flags: buffers written in place keep a flag through record
moves, helpers and loop states, so later writes skip the reference-count test;
slicing, copying, borrowing helpers, second loop states and array storage
clear it, and those writes still copy."""
import os,subprocess,tempfile
from pathlib import Path
from agent_codecs import RUNNER,build

def main():
    with tempfile.TemporaryDirectory(prefix='neo-unique-flags-') as temp:
        for flags in ['1','0']:
            binary=Path(temp)/('probe'+flags)
            os.environ['NEO_UNIQUE']=flags;build('tests/fixtures/unique_flags.neo',binary)
            for workers in ['1','4']:
                result=subprocess.run(RUNNER+[str(binary)],env={**os.environ,'NEO_THREADS':workers},capture_output=True,text=True,timeout=60)
                assert result.returncode==0 and result.stdout=='unique flags OK\n',(flags,workers,result.returncode,result.stdout,result.stderr)
        os.environ.pop('NEO_UNIQUE')
    print('PASS unique flags: trusted moves write in place; slices, copies, borrows, second states and stored records still copy (flags on and off)',flush=True)

if __name__=='__main__':main()
