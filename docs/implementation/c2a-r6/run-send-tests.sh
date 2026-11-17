#!/bin/bash
# Redirect only the supplied runner's scratch directory, which is read-only here.
function mktemp() { command mktemp -d /tmp/c2a-r6-send.XXXXXX; }
export -f mktemp
exec bash /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b "$@"
