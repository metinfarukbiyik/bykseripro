#!/bin/bash
cd "$(dirname "$0")" || exit 1
perl -pi -e 's/\r$//' BUILD_RELEASE_MAC.sh BUILD_APP.sh 2>/dev/null
chmod +x BUILD_RELEASE_MAC.sh BUILD_APP.sh
./BUILD_RELEASE_MAC.sh "$@"
status=$?
echo
read -r -p "Kapatmak için Enter..."
exit "$status"
