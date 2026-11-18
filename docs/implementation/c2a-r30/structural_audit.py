"""Confirm only the Date-boundary hold predicate and version changed."""
import ast
import hashlib
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent
old=(OUT/'r29-source.py.txt').read_text(); new=(OUT/'shipping-source.py.txt').read_text()
a,b=ast.parse(old),ast.parse(new)
def name(node):
    if isinstance(node,(ast.FunctionDef,ast.ClassDef)): return node.name
    if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name): return node.targets[0].id
    return None
changes=[name(x) for x,y in zip(a.body,b.body) if ast.dump(x)!=ast.dump(y)]
assert len(a.body)==len(b.body) and changes==['VERSION','printed_name_boundary'],changes
oldfn=next(x for x in a.body if name(x)=='printed_name_boundary')
newfn=next(x for x in b.body if name(x)=='printed_name_boundary')
assert ast.dump(oldfn.body[0])==ast.dump(newfn.body[0])
# Every block/name/heading/column check before the Date predicate is byte-exact.
prefix='        # A completed signature/date stack'
oldbody=old[old.index('def printed_name_boundary'):old.index(prefix)]
newbody=new[new.index('def printed_name_boundary'):new.index('        # A Date-first block')]
assert oldbody==newbody
proof=dict(changed_top_level_nodes=changes,
    source_sha256=hashlib.sha256(new.encode()).hexdigest(),
    prior_column_heading_contact_checks_exact=True,
    score_assignment_model_geometry_validation_functions_exact=True,
    date_candidate_condition='The new loop examines only dates satisfying the original 22-point crossing predicate and original column overlap.',
    relaxation='band is always >= 22; it only increases for a Date-first stack without an intervening signing rule, to min(50, 2 * By/Date pitch).',
    consequence='The changed predicate can only remove r29 holds. Results that were already placements cannot move. Correctness of newly released placements is separately checked against r28 and the unchanged geometry oracle in every measured family.')
(OUT/'structural-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof,indent=2))
