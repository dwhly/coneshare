# Automatic signature placement operations (C2a r7)

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
Ambiguous boundaries hold. A previous block with its own heading and no close
caption also separates stacked blocks at its rule-row bottom, including side
dates. An independent boundary uncertainty flag cannot be cleared by another
pair's successful partition.

**Company-only confidence has an additional veto walk.** From each local extent
edge, walk upward/downward through overlapping rows in the same column band,
stopping at a non-companion rule or prose. The upward walk also stops at a row
whose top belongs to another host's `(rule.y, rule.y + 125]` extent in that band.
Rules whose own label matches `^[A-Za-z][\w .'/&-]{0,30}:\s*$`, without
matching a known signature/name/title/date label, are `OTHER` companions.
Witness remains a signature host. The existing model-reviewed caption
`Hand of the covenanting party:` also retains its host/model path to preserve
the unusual-label golden. `OTHER` rules cannot create hosts, shorten either
extent edge, bound neighbouring columns or stop the walk. Their attached empty
captions carry no identity; surrounding typed rows retain their veto. At a page edge, continue from the adjacent page's
edge through its block-like rows. Any person-like or unresolved identity row
blocks company-only placement. A distant name can only remove confidence; it
cannot identify the signer or add a field. Named blocks retain their local
identity behavior. Fully accounted local evidence and a unique matching signer
are still required. The r4 acceptance of a name just outside the local window
is superseded by this rule.

Page-number rows are neutral anywhere in this walk. Digit-normalised text
repeated at the same y ±2 points on at least two distinct pages is neutral only
inside the page margins (`top < 72` or `bottom > page height - 72`, in PDF points).
Repeated body names still veto company-only confidence. Neutral rows neither
stop the walk nor veto confidence; local identity evidence remains intact.
Execution clauses recognise the additional company suffixes listed in the EDD
and distinguish roles from capitalised person names. Comma witness clauses stay
prose; title remainders before a comma and bare person names ending in a period
retain their veto. Clause endings whose last word is `date`, `agreement`,
`above`, `below` or `hereof` remain prose. Hold reasons use “sign and date” for
multiple named subjects and “signs and dates” for one.

**Annotations hold the entire document** with `form_fields`: “Form fields or
annotations require placement review. Nothing was sent.” Plain `/Link`
annotations remain allowed; a normal appearance stream makes a link hold too.
An empty widget is allowed only with an explicitly empty `/V` somewhere in its
field/parent chain, no nonempty values anywhere in that chain, and appearances
proven text-free. The proof accepts simple rectangle/border appearances only;
text operators, XObjects, images, appearance-state dictionaries, missing values,
cycles, malformed objects and unknown operators hold. No annotation text is
flattened, attributed or emitted. This preserves blank ReportLab text fields.
The broader absent-`/V` empty-widget exception and `/Sig` placement hints remain
deferred to C2b, as accepted in Gate 3 r5's L-1 finding.

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
