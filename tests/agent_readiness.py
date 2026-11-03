#!/usr/bin/env python3
"""Reproducible entry point for the agent-core additions."""
import os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    for script in ['agent_codecs.py','agent_utilities.py','agent_network.py','http_keepalive.py','http_large_body.py']:
        subprocess.run([sys.executable,str(ROOT/'tests'/script)],cwd=ROOT,check=True,env=os.environ)
if __name__=='__main__':main()
