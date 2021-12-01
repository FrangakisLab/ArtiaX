"""
Script to convert ChimeraX's marker file format .cmm
To an EM file and vice versa
"""

import numpy as np
import csv as csv
from io import StringIO

def cmmToEm(path):
    # Get the filepath to load the marker file
    filepath = None
    if ".cmm" in path:
        filepath = path
    elif ".em" in path:
        filepath = path[:-3] + ".cmm"
    else:
        filepath = path + ".cmm"

    # Read the data
    markers_file = open(filepath, "r")
    markers_read = markers_file.read()

    # Get the number of markers
    number_lines = -2
    for i in range(len(markers_read)):
        if markers_read[i] == "<":
            number_lines += 1

    # Initialize the data matix
    markers_data = [[0 for i in range(20)] for j in range(number_lines)]

    # Save the relevant rows
    rows = []
    row = -2

    for i in range(len(markers_read)):
        current_sign = markers_read[i]
        if current_sign == "<":
            row += 1
            temp_row = ""
        if row > -1 and row < number_lines:
            temp_row += current_sign
            if current_sign == ">":
                rows.append(temp_row)

    # Separate each row but its column entries
    # And save the wanted columns in matrix
    for i in range(number_lines):
        current_row = StringIO(rows[i])
        rows_csv = csv.reader(current_row, delimiter=" ")
        for row in rows_csv:
            # markers_data[i][1] = float(row[1][4:-1])
            markers_data[i][7] = float(row[2][3:-1])
            markers_data[i][8] = float(row[3][3:-1])
            markers_data[i][9] = float(row[4][3:-1])
            markers_data[i][2] = float(row[8][8:-3])

    # Transpose matrix
    markers_data = np.asarray(markers_data)
    # markers_data = markers_data.transpose()

    return markers_data
