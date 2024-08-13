#!/bin/bash
#

# Returns a string `true` if the string is considered a boolean true,
# otherwise `false`. An empty value is considered false.
function str_bool {
  local str="${1:-false}"
  local pat='^(true|1|yes)$'
  if [[ "$str" =~ $pat ]]; then
    echo 'true'
  else
    echo 'false'
  fi
}

use_root=$(str_bool "${USE_ROOT:-}")

if [ "$use_root" = "true" ]; then
    echo "Starting using sudo"
    echo "docker" | sudo -SE sh -c 'python db_copy.py'
else
    echo "Starting"
    python db_copy.py
fi