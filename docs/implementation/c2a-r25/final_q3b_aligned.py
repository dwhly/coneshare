"""Evaluate the separately retained Q3b reconstruction on the frozen final source."""
import replay25 as replay
from review_q3b import inputs


if __name__ == '__main__':
    replay.inputs = inputs
    replay.main('q3b_aligned', replay.OUT / 'final', replay.OUT / 'structural-source.py.txt')
