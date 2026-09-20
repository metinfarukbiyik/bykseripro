#!/bin/bash
cd "$(dirname "$0")" || exit 1
perl -pi -e 's/\r$//' KURULUM.sh 2>/dev/null
chmod +x KURULUM.sh
exec ./KURULUM.sh "$@"
