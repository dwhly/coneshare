"""Run from a quiescent glue worktree: this temporarily changes one implementation at a time.

Never run alongside another build/test process. Logs stay in ignored .local/r2.
Each implementation is restored in finally, including on interruption.
"""
from pathlib import Path
import ast, subprocess, argparse, os

parser = argparse.ArgumentParser(description='Revert one reviewed fix, require regression failure, restore and require pass.')
parser.add_argument('--base', default='ecd20b4', help='Gate 3 r1 source commit')
parser.add_argument('--only', help='Run one finding ID, e.g. 02b')
args = parser.parse_args()
os.chdir(Path(__file__).resolve().parents[2])
BASE=args.base
OUT=Path('deploy/chief-glue-v1/.local/r2')
OUT.mkdir(parents=True, exist_ok=True)
def old(path):
    return subprocess.check_output(['git','show',BASE+':'+path],text=True)
def fn_range(s, name, cls=None):
    tree=ast.parse(s)
    nodes=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls).body if cls else tree.body
    n=next(n for n in nodes if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
    return min([n.lineno]+[d.lineno for d in n.decorator_list])-1,n.end_lineno
def replace_fn(s, previous, name, cls=None):
    a,b=fn_range(s,name,cls); c,d=fn_range(previous,name,cls)
    lines=s.splitlines(True);lines[a:b]=previous.splitlines(True)[c:d];return ''.join(lines)
cases=[
 ('01','backend/dealroom_sign/views.py','path_room_cannot_be_overridden',('scoped_room',None)),
 ('02','backend/dealroom/recipient.py','two_members_only_see_subject_executed_folders',('get','RecipientRoomView')),
 ('03','backend/dealroom_sign/urls.py','staff_resets_one_member_with_fresh_generation',None),
 ('04','mcp-server/coneshare_mcp/tools/signing.py','agent_catalog_has_no_recipient_signing_capabilities',None),
 ('05','backend/dealroom_sign/views.py','policy_toggle_keeps_acceptance_revision',('put','SigningNdaPolicyView')),
 ('06','backend/dealroom_sign/workflows.py','duplicate_command_does_not_fetch_or_parse_pdf',('command',None)),
 ('07','backend/dealroom_sign/storage.py','every_pdf_signature_must_validate',('verify_seal',None)),
 ('08a','backend/dealroom_sign/workflows.py','unexpected_errors_increment_attempts_and_backoff',('process',None)),
 ('08b','backend/dealroom_sign/views.py','credential_team_change_warns_before_stranding_work',('put','SignCredentialView')),
 ('09','deploy/chief-glue-v1/docker-compose.yml','staff_port_is_tailnet_only',None),
 ('10','backend/dealroom_sign/views.py','member_start_can_enter_identity_and_revocation',('get','RecipientNdaView')),
 ('01c','backend/dealroom_sign/views.py','path_conflicts_rejected_for_human_staff',('staff_room',None)),
 ('01b','backend/dealroom_sign/views.py','scoped_workflow_query_uses_actual_target',('scoped_room',None)),
 ('02b','backend/dealroom_sign/policy.py','ordinary_file_cannot_expose_private_executed_folder',('artifact_allowed',None)),
 ('03b','backend/dealroom_sign/client.py','native_reset_invalidates_old_envelope',None),
 ('03c','backend/dealroom_sign/serializers.py','stuck_nda_status_identifies_subject_for_staff',None),
]
for number,path,test,func in cases:
    if args.only and args.only != number:
        continue
    p=Path(path);fixed=p.read_text();previous=old(path)
    mutant=replace_fn(fixed,previous,*func) if func else previous
    try:
        p.write_text(mutant)
        with (OUT/f'mutation-{number}.log').open('w') as f:
            r=subprocess.run(['bash','deploy/chief-send-v1/test-backend.sh','dealroom_sign/tests/test_review_r2.py','--ds=dealroom_sign.test_settings','-k',test],stdout=f,stderr=subprocess.STDOUT)
        summary=(OUT/f'mutation-{number}.log').read_text().splitlines()[-1]
        print(f'{number}: reverted exit={r.returncode}: {summary}',flush=True)
        if r.returncode!=1 or 'failed' not in summary:
            raise RuntimeError('Mutation did not produce expected assertion failure')
    finally:
        p.write_text(fixed)
    with (OUT/f'restored-{number}.log').open('w') as f:
        r=subprocess.run(['bash','deploy/chief-send-v1/test-backend.sh','dealroom_sign/tests/test_review_r2.py','--ds=dealroom_sign.test_settings','-k',test],stdout=f,stderr=subprocess.STDOUT)
    summary=(OUT/f'restored-{number}.log').read_text().splitlines()[-1]
    print(f'{number}: restored exit={r.returncode}: {summary}',flush=True)
    if r.returncode:
        raise RuntimeError('Restored regression failed')
