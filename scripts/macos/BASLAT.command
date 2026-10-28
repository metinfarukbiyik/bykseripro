#!/bin/bash
cd "$(dirname "$0")" || exit 1
# CRLF ile bozulmuş .sh varsa düzelt
perl -pi -e 's/\r$//' BASLAT.sh 2>/dev/null
chmod +x BASLAT.sh
exec ./BASLAT.sh "$@"
