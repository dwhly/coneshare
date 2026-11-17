#!/bin/bash
function mktemp() { command mktemp -d /tmp/c2a-r5-board.XXXXXX; }
export -f mktemp
exec bash /root/work/sign-product/run-board-tests.sh /root/worktrees/board-s1 "$@"
