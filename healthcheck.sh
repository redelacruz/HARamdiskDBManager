#!/bin/bash

# Check if RAMDISK_PATH is set
if [ -z "$RAMDISK_PATH" ]; then
  echo "ERROR: RAMDISK_PATH environment variable is not set."
  exit 1
fi

# Remove trailing slash from RAMDISK_PATH if it exists
RAMDISK_PATH=${RAMDISK_PATH%/}

# Check if the healthcheck file exists
if [ -f "${RAMDISK_PATH}/healthcheck" ]; then
  echo "Healthcheck passed"
  exit 0
else
  echo "Healthcheck failed"
  exit 1
fi