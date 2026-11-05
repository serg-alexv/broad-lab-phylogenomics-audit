"""Bounded file arithmetic for alignment agreement and diagnostic unrooted clades."""
import collections,math,re,sys

def residues(original,aligned):
 if set(original)!=set(aligned)or len({len(s)for s in aligned.values()})!=1:raise ValueError('Alignment IDs/lengths differ')
 for n,s in original.items():
  if aligned[n].replace('-','').replace('.','')!=s:raise ValueError('Alignment changes original residues')

def pair_agreement(first,second,original):
 residues(original,first);residues(original,second);names=sorted(original);na=nb=shared=union=0
 def pairs(a,b):
  left=right=0;result=set()
  for x,y in zip(a,b):
   left+=x not in'-.';right+=y not in'-.'
   if x not in'-.'and y not in'-.':result.add((left,right))
  return result
 for i,n in enumerate(names):
  for m in names[i+1:]:
   a=pairs(first[n],first[m]);b=pairs(second[n],second[m]);na+=len(a);nb+=len(b);shared+=len(a&b);union+=len(a|b)
 return {'full_alignment_projected_pairs':na,'careful_subset_pairs':nb,'shared_pairs':shared,'union_pairs':union,'paired_residue_jaccard':shared/union if union else None,'projected_pair_fraction_recovered':shared/na if na else None,'careful_pair_fraction_in_full_projection':shared/nb if nb else None,'bounded_memory_one_sequence_pair_at_a_time':True,'alignment_accuracy_against_biological_truth_claimed':False}

def parse_newick(text,expected):
 tokens=re.findall(r"'(?:[^']|'')*'|[(),:;]|[^\s(),:;]+",text);at=0;leaves=[];sys.setrecursionlimit(max(sys.getrecursionlimit(),len(expected)*4+100))
 def label(value):return value[1:-1].replace("''", "'")if value.startswith("'")else value
 def node():
  nonlocal at
  if at>=len(tokens):raise ValueError('Truncated Newick')
  if tokens[at]=='(':
   at+=1;children=[node()]
   while at<len(tokens)and tokens[at]==',':at+=1;children.append(node())
   if at>=len(tokens)or tokens[at]!=')':raise ValueError('Newick closing parenthesis missing')
   at+=1;n={'children':children}
   if at<len(tokens)and tokens[at]not in('(',')',',',':',';'):n['internal_label']=label(tokens[at]);at+=1
  else:
   if tokens[at]in('(',')',',',':',';'):raise ValueError('Newick leaf missing')
   name=label(tokens[at]);at+=1;leaves.append(name);n={'leaf':name,'children':[]}
  if at<len(tokens)and tokens[at]==':':
   at+=1
   if at>=len(tokens):raise ValueError('Missing branch length')
   length=float(tokens[at]);at+=1
   if not math.isfinite(length)or length<0:raise ValueError('Invalid branch length')
   n['branch_length']=length
  return n
 root=node()
 if tokens[at:]!=[';']or len(leaves)!=len(set(leaves))or set(leaves)!=set(expected):raise ValueError('Newick leaf set, duplication or terminator mismatch')
 return root

def unrooted_monophyly(root,leaf_groups):
 total=collections.Counter(leaf_groups.values());matched=set();edges=0
 def visit(node):
  nonlocal edges
  if not node['children']:counts=collections.Counter([leaf_groups[node['leaf']]])
  else:
   counts=collections.Counter()
   for child in node['children']:counts.update(visit(child))
  if counts!=total:
   edges+=1
   for side in(counts,total-counts):
    if len(side)==1:
     group=next(iter(side))
     if side[group]==total[group]:matched.add(group)
  return counts
 visit(root)
 return {'expected_group_leaf_counts':dict(total),'groups_matching_one_unrooted_split':sorted(matched),'groups_without_a_single_split':sorted(set(total)-matched),'tree_edges_checked':edges,'source_labels_are_diagnostic_not_taxonomy_truth':True,'automatic_acceptance_or_exclusion':False}
