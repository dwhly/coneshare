#!/bin/bash
# The supplied runner's scratch root is read-only in the sandbox.
function mktemp() { command mktemp -d /tmp/c2a-r5-send.XXXXXX; }
export -f mktemp
exec bash /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b "$@"
