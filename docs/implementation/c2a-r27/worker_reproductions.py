"""Run the review's verbatim worker reproduction bodies on baseline and release."""
from contextlib import ExitStack
from pathlib import Path
import sys

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(OUT.parent / 'c2a-r26')]
import replay26 as prior

prior.measure.replay.prior.OUT = OUT
with ExitStack() as stack:
    for revision in ('r26', 'r27'):
        module = prior.measure.replay.prior.make_module('real_reproduction_' + revision,
                    (OUT / (revision + '-source.py.txt')).read_text(), stack)
        for call in (29, 43):
            print('REVISION', revision, 'REVIEW CALL', call, flush=True)
            source = (OUT / f'reviewer-r26-call{call}.py.txt').read_text()
            source = source.replace('from dealroom_sign import placement\n', 'placement = reviewed_module\n')
            exec(compile(source, f'reviewer-r26-call{call}.py.txt', 'exec'), {'reviewed_module': module})
