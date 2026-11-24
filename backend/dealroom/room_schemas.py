"""OpenAPI/MCP request shapes for the S2 command endpoints."""
TEXT = {'type': 'string'}
SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
ACCESS = {'type': 'object', 'additionalProperties': False,
          'required': ['download_ceiling', 'expires_at'], 'properties': {
              'download_ceiling': {'type': 'string', 'enum': ['none', 'watermarked']},
              'expires_at': {'type': 'string', 'format': 'date-time', 'nullable': True}}}
MANIFEST = {'type': 'object', 'additionalProperties': False,
            'required': ['name', 'items', 'nda', 'access', 'intended_emails'], 'properties': {
                'name': TEXT, 'items': {'type': 'array', 'maxItems': 2000, 'items': {
                    'type': 'object', 'additionalProperties': False,
                    'required': ['client_item_id', 'kind', 'name', 'parent_id', 'position'],
                    'properties': {'client_item_id': TEXT, 'kind': {'type': 'string', 'enum': ['folder', 'file']},
                        'name': TEXT, 'parent_id': {'type': 'string', 'nullable': True},
                        'position': {'type': 'integer', 'minimum': 0}, 'sha256': SHA,
                        'purpose': {'type': 'string', 'enum': ['document', 'nda']}}}},
                'nda': {'type': 'object', 'required': ['enabled'], 'properties': {'enabled': {'type': 'boolean'},
                    'source': {'type': 'object', 'nullable': True}, 'fields': {'type': 'array', 'items': {'type': 'object'}},
                    'revision': {'type': 'string', 'nullable': True}}},
                'access': ACCESS, 'intended_emails': {'type': 'array', 'maxItems': 200,
                                                   'items': {'type': 'string', 'format': 'email'}}}}
IMPORTS = {'type': 'object', 'additionalProperties': False,
           'required': ['expected_revision', 'approved_manifest', 'manifest_sha256', 'idempotency_key'],
           'properties': {'expected_revision': {'type': 'integer', 'minimum': 1},
                          'approved_manifest': MANIFEST, 'manifest_sha256': SHA, 'idempotency_key': TEXT}}
COMPLETE = {'type': 'object', 'additionalProperties': False,
            'required': ['approval_key', 'import_id', 'idempotency_key', 'expected_revision', 'manifest_sha256',
                         'items', 'nda_revision', 'access'],
            'properties': {'approval_key': TEXT, 'import_id': TEXT, 'idempotency_key': TEXT,
                           'expected_revision': {'type': 'integer', 'minimum': 1}, 'manifest_sha256': SHA,
                           'nda_revision': {'type': 'string', 'nullable': True}, 'access': ACCESS,
                           'items': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                               'required': ['client_item_id', 'version_id', 'sha256'],
                               'properties': {'client_item_id': TEXT, 'version_id': TEXT, 'sha256': SHA}}}}}

ABANDON = {'type': 'object', 'additionalProperties': False,
           'required': ['approval_key', 'idempotency_key', 'expected_revision'],
           'properties': {'approval_key': TEXT, 'idempotency_key': TEXT,
                          'expected_revision': {'type': 'integer', 'minimum': 1}}}
