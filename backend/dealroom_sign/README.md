# Send ↔ Sign integration

This app runs inside Coneshare's Django database and uses the v2 envelope API. It owns no Sign tables. SignCredential encrypts each staff member's team credential using Django's SECRET_KEY; retain that key in backups. Raw credentials and signing tokens have no agent read API.

Workflows pin a native DocumentVersion and SHA-256. The caller supplies recipient fields in percentage coordinates; no inferred placement. External IDs correlate ambiguous creates, never assert upstream uniqueness. Repeated or lost send responses are reconciled before any retry. Duplicate discoveries and changed source/signer/artifact bytes quarantine the workflow.

Webhooks are authenticated hints; no inbox/payload storage. `manage.py sign_poll` sweeps durable state every 15 seconds, including after worker/Redis loss. The private webhook route can wake a Celery worker sooner. Only verified completed envelopes with valid PDF signatures, retrieved certificate and audit are filed and accepted. Artifact and NDA acceptance publication share one transaction. Canonical sealed PDFs remain byte-identical.

Configuration: SIGN_INTERNAL_URL, SIGN_PUBLIC_URL, SIGN_DEPLOYMENT_ID, SIGN_WEBHOOK_SECRET. The deployment must include Poppler pdfsig. Recipient exposure defaults off. The sender/agent surface uses Send's registry and approval service. NDA entry requires Send's verified member session and live grant; signing redirect or webhook status cannot grant access.

Known initial slice limits: one PDF source item; SIGNER roles only; caller-supplied basic fields (rich field metadata remains in the native editor); room agreements file staff-only. Native Sign UI may edit an envelope, but changing its recipient identity or pinned source quarantines the integration until reviewed.
