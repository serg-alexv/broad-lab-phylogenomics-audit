"""Prewarm short private multiprocessing socket path, then unchanged stock CLI."""
import os,sys,tempfile,multiprocessing.util,runpy
short='/tmp/tree2_checkm1';os.makedirs(short,exist_ok=True);tempfile.tempdir=short
multiprocessing.util.get_temp_dir()
script=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(script,run_name='__main__')
