#!/bin/bash

# Set default values for search and target directories
search_dir=${1:-./plugins}
target_dir=${2:-./data/config}

# Find all files that start with "sample." and end with ".yaml"
files=$(find "${search_dir}" -type f -name "*.sample.yaml")

for file in ${files}; do
  # Get the filename without the leading "./plugins/" directory
  filename=$(basename ${file})

  # Remove "sample." from the filename
  new_filename=${filename/.sample/}

  # Copy the file into the target directory with the new filename
  cp "${file}" "${target_dir}/${new_filename}"
done