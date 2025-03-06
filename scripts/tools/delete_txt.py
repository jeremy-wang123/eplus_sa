#!/usr/bin/env python3
"""
This script deletes all .txt files in a specified folder.
Usage: python3 delete_txt.py /path/to/folder
"""

import os
import glob
import sys

# Check if a folder path was provided as an argument.
if len(sys.argv) != 2:
    print("Usage: {} data/ORNL Model America/NH_Grafton_IDF".format(sys.argv[0]))
    sys.exit(1)

folder = sys.argv[1]

# Verify that the provided argument is a directory.
if not os.path.isdir(folder):
    print("Error: '{}' is not a valid directory.".format(folder))
    sys.exit(1)

# Construct the pattern to match .txt files in the folder.
pattern = os.path.join(folder, "*.txt")

# Iterate over all matching files and delete them.
for file_path in glob.glob(pattern):
    try:
        os.remove(file_path)
        print("Deleted:", file_path)
    except Exception as e:
        print("Error deleting '{}': {}".format(file_path, e))