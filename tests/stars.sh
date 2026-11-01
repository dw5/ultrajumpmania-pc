#!/bin/bash
# Collects every star in the hack and the port with tests/star.sh and lists where each one ends up.
ROOT=$(cd "$(dirname "$0")/.." && pwd); OUT=$ROOT/build/oracle/stars; mkdir -p "$OUT"; cd "$ROOT"
run() {
    echo "== $1"
    NOACT=$5 AREA=$4 N=${N:-10} GAP=4 timeout 300 bash tests/star.sh "$2" "$3" "$6" 2>&1 | grep -E "^(EMU|END) " | tail -2
    cp build/oracle/star/sheet.png "$OUT/$1.png"
}
run l9-star0 9 9 0 "" "11729 3731 -19522 0"
run l9-star1 9 9 0 "" "1387 1789 -6410 0"
run l9-star5 9 9 0 "" "12536 1966 -10446 0"
run l9-star2 9a2 9 2 "" "337 1018 -9335 0"
run l9-star3 9a4 9 4 "" "-2478 1678 -3090 0"
run l9-star4 9a5 9 5 "" "-195 3075 10763 0"
run l17-star 17 17 0 1 "4790 1340 -9353 0"
