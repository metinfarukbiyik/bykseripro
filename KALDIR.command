#!/bin/bash
cd "$(dirname "$0")" || exit 1
perl -pi -e 's/\r$//' KALDIR.sh 2>/dev/null
chmod +x KALDIR.sh
exec ./KALDIR.sh "$@"
