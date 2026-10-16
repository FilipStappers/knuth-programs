#!/bin/sh
# one argument, a signed 32-bit random seed

usage() {
  printf 'Usage: %s seed (signed 32-bit integer)\n' "$0" >&2
  exit 2
}
[ "$#" -eq 1 ] || usage
seed=$1
case $seed in
  -*) digits=${seed#-} ;;
  +*) digits=${seed#+} ;;
  *) digits=$seed ;;
esac
case $digits in ''|*[!0-9]*) usage ;; esac
{ [ "$seed" -ge -2147483648 ] && [ "$seed" -le 2147483647 ]; } 2>/dev/null || usage

# Materialize each formula before running the solver, so a failed producer
# cannot leave the solver working on truncated input. Keep POSIX sh semantics.
input=$(mktemp "${TMPDIR:-/tmp}/gates-stuck-hardest.XXXXXXXX") || exit 1
trap 'rm -f "$input"' 0
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

run_case() {
  printf '%s\n' "$1"
  sat-gates-stuck-namekludge /tmp/prod,16,32-wires.gb "$2" > "$input"
  status=$?
  if [ "$status" -ne 0 ]; then
    printf '%s: generator failed (%s)\n' "$1" "$status" >&2
    exit "$status"
  fi
  sat13 h9 "s$seed" < "$input" > /dev/null
  status=$?
  if [ "$status" -ne 0 ]; then
    printf '%s: solver failed (%s)\n' "$1" "$status" >&2
    exit "$status"
  fi
}

run_case '1W21#10' '1W21#10'
run_case '0W21#18' '0W21#18'
run_case '1W21#19' '1W21#19'
run_case '0D29:8#16' '0D290816'
run_case '0D34:13#3' '0D341303'
run_case '0D34:13#8' '0D341308'
run_case '0D34:13#9' '0D341309'
run_case '0B41:41' '0B41:41'
run_case '0D42:3#3' '0D42:3#3'
run_case '0D42:3#7' '0D42:3#7'
run_case '0D42:3#8' '0D42:3#8'
run_case '0D42:13#2' '0D421302'
run_case '0B42:42' '0B42:42'
run_case '0D43:9#2' '0D43:9#2'
run_case '0B43:43' '0B43:43'
run_case '0D44:10#2' '0D441002'
