# Automatic signature placement operations (C2a r4)

Placement holds are fail closed: no fields are sent. A bare document remains a
hold. Rules resolve clearly attributed blocks; unusual labels may use one
bounded model call after local identity checks. Model output cannot override a
printed-name mismatch or an unresolved identity.

## Identity extent

The current local parser examines rows starting at most **90 PDF points above**
and **125 points below** each signature rule. Previous rules and neighbouring
blocks can shorten that window. The horizontal band includes text beside the
rule, stopping at neighbouring rule columns. Text in a gap shared by two columns
participates in both. Stacked blocks are separated using the previous block's
companion fields/close caption and the next block's first attributable label.
Ambiguous boundaries hold. This is bounded local evidence, not page-wide person
recognition: a name starting 100 points above a rule is outside this identity
window, even if only ordinary labels intervene. Do not infer an all-page identity
guarantee from a `high` local score.

Raw rows are scored only inside the parser child. Other people's names and body
prose are redacted before model input, result fields or History. A company word
inside prose does not permit its disclosure. Company text is emitted only for
mapped role companies or a heading contributing to a local identity score.

## Parser and model capacity

Each parser child is limited to **768 MiB address space**, at most eight CPU
seconds, and the remaining parse/total wall budget. The default parse budget is
three seconds, the default total budget twelve. `PARSE_SLOTS` is a **per-process**
semaphore of two, not a host-wide limit.

For `W` synchronous Gunicorn workers there can be `W` parser children: budget
`W × 768 MiB` for child address-space ceilings, **plus** worker processes and the
rest of the stack. Four synchronous workers therefore permit 3 GiB of child
address space; eight permit 6 GiB. With `T` concurrent request threads per worker,
the child ceiling is `W × min(T, 2) × 768 MiB`. Actual RSS can be smaller, but
these are not reservations or host-wide enforcement. Size the container/host
memory limit and worker count together. A synchronous worker cannot exhaust its
own two slots, so `placement_busy` does not provide a cross-worker admission
limit. Timed-out children are killed and reaped before their slots are released.

The caller still returns at the total deadline. HTTP model reads time out within
`min(2 seconds, remaining budget)` and pool acquisition within
`min(1 second, remaining budget)`. A read blocked at the deadline can retain its
model slot for up to two further seconds; closing a socket from another thread
alone is not a reliable interruption of Linux `recv`.

## Upload reservations and uncertain responses

Board commits a per-submission reservation before uploading, releases the SQLite
write lock during the network call, then stores the upload's exact verified
version. Different submission keys proceed concurrently. A retry for the same
pending key waits at most one second for completion, then gets retryable 503
without another upload. A crashed worker's reservation expires after 120 seconds;
a stale owner cannot overwrite a newer reservation. Existing completed mappings
remain valid and both source-hash checks still apply on retry. The local SQLite
store creates its reservation table automatically; no Django migration is needed.

**Known upload limitation (L-4):** Send does not yet deduplicate uploads by the
submission key. If Send commits an upload but Board loses the response, the
outcome is unknown and the uploaded document can remain orphaned in the room.
An ordinary exception releases the reservation; a crash leaves it until expiry.
A retry may upload a fresh version and uses only that upload's returned version
and verified hash. It never selects a version by filename or polling. Existing
send idempotency prevents duplicate sends after the source mapping is recorded.

On `outcome_unknown`, check History before retrying. If duplicate documents are
present, compare their exact version IDs and source hashes with recorded signing
requests before manually removing an unreferenced upload through the authorized
room workflow. Never automatically delete a document based on a matching name
or hash. Upload-level idempotency is deferred to the later slice identified by
the review; this round documents the orphan risk rather than changing the upload
API or guessing an orphan's identity.
