#!/bin/bash

db="/path/to/your.db"

# Temporary file to hold table names and counts
temp_file=$(mktemp)

# Ensure temporary file gets deleted on script exit
trap "rm -f $temp_file" EXIT

# Fetch each table name from the database
table_names=$(sqlite3 "$db" "SELECT name FROM sqlite_master WHERE type='table';")

# Iterate over each table name, count its rows, and write to the temp file
for table in $table_names; do
    count=$(sqlite3 "$db" "SELECT COUNT(*) FROM \"$table\";")
    echo "$count|$table" >> "$temp_file"
done

# Sort the temporary file numerically by counts and then print
sort -n "$temp_file" | while IFS='|' read -r count name; do
    echo "$name = $count"
done

# Clean up the temporary file
rm -f "$temp_file"