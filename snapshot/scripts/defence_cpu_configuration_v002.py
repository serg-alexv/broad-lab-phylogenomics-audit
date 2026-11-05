"""Explicit CPU profiles for newly admitted production cohorts; unchanged memory gates."""
def configuration(plan, available_cpus=None):
 if plan.get('schema') != 'TREE2_DEFENCE_NOVEL_PRODUCTION_COHORT_PLAN_V002':
  raise ValueError('CPU upgrade requires its own V002 source-bound plan')
 threads=plan.get('stock_threads');affinity=plan.get('cpu_affinity')
 if type(threads) is not int or threads not in (2,4):
  raise ValueError('Only explicit two/four CPU profiles are admitted')
 expected=[0,1,2,3] if threads==4 else [2,3]
 if type(affinity) is not list or any(type(cpu) is not int for cpu in affinity) or affinity != expected:
  raise ValueError('Explicit CPU affinity must match the stock thread allocation')
 if available_cpus is not None and not set(affinity).issubset(set(available_cpus)):
  raise ValueError('Requested CPUs unavailable; fresh admission required before science')
 for key,value in {'native_reserved_bytes':134217728,'linux_RSS_plus_RAM_bytes':1879048192,'minimum_linux_available_bytes':1342177280}.items():
  if type(plan.get(key)) is not int or plan[key] != value:
   raise ValueError('Memory safeguards must remain exact: '+key)
 return threads,affinity
