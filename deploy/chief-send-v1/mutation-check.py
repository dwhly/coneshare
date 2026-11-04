"""Reproduce r2 negative checks. Run only in an otherwise idle worktree.
Each mutation restores source in finally; logs are written to out/. A nonzero
pytest result is required for each deliberately reverted protection.
#11 and #12 mutate approved/pre-existing checks, rather than claim an old bug.
"""
from pathlib import Path
import subprocess, json
root=Path(__file__).resolve().parents[2]; out=root/'deploy/chief-send-v1/out'
def old(path):return subprocess.check_output(['git','show','2244526:'+path],cwd=root,text=True)
def mutate(label, changes, tests, frontend=False):
    originals={path:(root/path).read_text() for path in changes}
    try:
        for path, change in changes.items():
            original=originals[path]
            (root/path).write_text(change(original))
        command=['fnm','exec','--using=24','npm','test','--prefix','frontend','--','--run'] if frontend else ['./deploy/chief-send-v1/test-backend.sh']
        with (out/f'r2-{label}-mutation.log').open('w') as stream:
            result=subprocess.run(command+tests,cwd=root,stdout=stream,stderr=subprocess.STDOUT)
        print(label, result.returncode, flush=True)
        assert result.returncode != 0, label+' survived mutation'
    finally:
        for path,data in originals.items():(root/path).write_text(data)
review='tests/dealroom/test_review_r2.py'
mutate('01-transport',{'backend/dealroom/hooks.py':lambda s:s[:s.index("        if request.method not in ('GET', 'HEAD', 'OPTIONS')")] + s[s.index('        if not request.auth.user.is_staff'): ]},[review+'::test_r2_01_form_mutations_cannot_restore_access'])
mutate('01-scalar',{'backend/dealroom/registry.py':lambda s:s.replace('        if isinstance(value, (list, dict, tuple, set)):\n            return True\n','')},[review+'::test_r2_01_non_scalar_changes_are_widening'])
mutate('02',{'backend/dealroom/views.py':lambda s:s.replace("        self.fact('grant.revoked', instance)","        if instance.email:\n            member = Viewer.objects.filter(organization=self.request.user.organization, email=instance.email).first()\n            if member:\n                MemberDeny.objects.get_or_create(room=instance.share_link.dataroom, member=member)\n        self.fact('grant.revoked', instance)")},[review+'::test_r2_02_grant_revoke_does_not_deny_org_member_and_restore_is_audited'])
mutate('04',{'backend/dealroom/serializers.py':lambda s: s[:s.index('class GrantSerializer')] + old('backend/dealroom/serializers.py')[old('backend/dealroom/serializers.py').index('class GrantSerializer'):old('backend/dealroom/serializers.py').index('class EntryLinkSerializer')] + s[s.index('class EntryLinkSerializer'):]},[review+'::test_r2_04_active_grants_normalized_unique_and_regrantable'])
mutate('05',{'backend/dealroom/operations.json':lambda s:s.replace('"human_only": true,\n    "method": "POST",\n    "operation_id": "dealroom_DriftViewSet_acknowledge_post"','"human_only": false,\n    "method": "POST",\n    "operation_id": "dealroom_DriftViewSet_acknowledge_post"')},[review+'::test_r2_05_agent_cannot_acknowledge_own_drift'])
mutate('06-api',{'backend/dealroom/serializers.py':lambda s:s.replace("'payload', 'current_state', 'payload_hash'", "'payload', 'payload_hash'").replace('    current_state = serializers.SerializerMethodField()\n','')},[review+'::test_r2_06_approval_reports_target_current_state_and_proposed_change'])
mutate('06-ui',{'frontend/src/pages/DealroomConsole.jsx':lambda s:old('frontend/src/pages/DealroomConsole.jsx')},['src/tests/pages/DealroomConsole.test.jsx'],True)
mutate('07',{'backend/dealroom/views.py':lambda s:s.replace("        instance.archived_at = timezone.now()\n        instance.save(update_fields=['archived_at'])\n        instance.grants.filter(revoked_at__isnull=True).update(revoked_at=instance.archived_at)\n        self.fact('org.archived', instance)", '        instance.delete()')},[review+'::test_r2_07_used_org_archives_and_retains_evidence'])
mutate('08-health',{'backend/dealroom/hooks.py':lambda s:s.replace(" or type(self).__name__ == 'HealthCheckView'",'')},['tests/core/test_views.py::TestHealthCheckView::test_health_check_database_unreachable'])
mutate('08-audit',{'backend/dealroom/hooks.py':lambda s:s.replace('            audit_denial(self, response)', '            pass')},[review+'::test_r2_08_denial_survives_transaction_rollback'])
mutate('08-render',{'backend/dealroom/hooks.py':lambda s:s.replace("render = type(self).__name__ in {'WatermarkedPageRenderView', 'ShareLinkFileDownloadView'}", "render = type(self).__name__ in {'WatermarkedPageRenderView', 'ShareLinkFileDownloadView', 'OriginalDownloadView'}")},[review+'::test_r2_08_original_download_does_not_acquire_render_semaphore'])
mutate('09',{'backend/core/authentication.py':lambda s:old('backend/core/authentication.py')},[review+'::test_r2_09_legacy_prefix_authenticates_only_matching_hash'])
mutate('10-api',{'backend/dealroom/recipient.py':lambda s:s.replace('#challenge={challenge.id}&token={token}', '?challenge={challenge.id}&token={token}')},[review+'::test_r2_10_magic_token_is_fragment_only'])
mutate('10-ui',{'frontend/src/pages/DealroomRecipient.jsx':lambda s:old('frontend/src/pages/DealroomRecipient.jsx')},['src/tests/pages/DealroomRecipient.test.jsx'],True)

migration='backend/sharelinks/migrations/0017_remove_sharelinkaccessgrant_uq_sharelink_grant_org_and_more.py'
mutate('04-constraint', {migration:lambda s:s.replace("('revoked_at__isnull', True), ", '').replace(", ('revoked_at__isnull', True)", '')}, [review+'::test_r2_04_active_grants_normalized_unique_and_regrantable'])
mutate('12-member-deny', {'backend/dealroom/policy.py':lambda s:s.replace('MemberDeny.objects.filter(room=policy.room, member=member).exists()', 'False')}, [review+'::test_r2_12_recipient_policy_after_real_otp[member_deny]'])
mutate('12-revocation', {'backend/dealroom/policy.py':lambda s:s.replace('.filter(revoked_at__isnull=True)', '.all()')}, [review+'::test_r2_12_recipient_policy_after_real_otp[revoked_page]'])
mutate('12-room', {'backend/dealroom/policy.py':lambda s:s.replace("proof.get('room_id') != str(link.dataroom_id) or ", '')}, [review+'::test_r2_12_recipient_policy_after_real_otp[wrong_room]'])
mutate('12-idle', {'backend/dealroom/policy.py':lambda s:s.replace(" or now - proof.get('last_seen', 0) > 1800", '')}, [review+'::test_r2_12_recipient_policy_after_real_otp[idle]'])
mutate('12-ceilings', {'backend/dealroom/policy.py':lambda s:s.replace('level = min((level, file_level)', 'level = max((level, file_level)')}, [review+'::test_r2_12_recipient_policy_after_real_otp[grant_ceiling]',review+'::test_r2_12_recipient_policy_after_real_otp[file_ceiling]'])
mutate('11-visibility', {'backend/dealroom/registry.py':lambda s:s.replace("elif key in ('is_visible', 'audiences'):\n            # Existing grantees seeing new files is not a new subject or original permission.\n            continue", "elif key in ('is_visible', 'audiences'):\n            return True")}, ['tests/dealroom/test_foundation.py::test_file_visibility_for_existing_grantees_not_widening'])
mutate('03', {'backend/dealroom/recipient.py':lambda s:s.replace("'folders': folders", "'folders': list(link.dataroom.folders.values('id', 'name'))")}, [review+'::test_r2_03_recipient_folders_require_visible_permitted_content'])
mutate('01-all-edits', {'backend/dealroom/hooks.py':lambda s:s[:s.index("        if request.method not in ('GET', 'HEAD', 'OPTIONS')")] + s[s.index('        if not request.auth.user.is_staff'): ]}, ['tests/dealroom/test_foundation.py::test_each_edit_to_widen_cannot_bypass_the_http_gate'])
