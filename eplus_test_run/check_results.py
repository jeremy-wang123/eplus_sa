import sqlite3

conn = sqlite3.connect('eplusout.sql')
cur = conn.cursor()

# List all tables in the SQL file
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cur.fetchall()
print("Tables in SQL file:", tables)

# Listing variable outputs
with sqlite3.connect('eplusout.sql') as conn:
    cur = conn.cursor()

    # List all variables
    cur.execute("SELECT ReportDataDictionaryIndex, Name FROM ReportDataDictionary;")
    variables = cur.fetchall()
    for var in variables:
        print(var)


# printing out the total site electricity 
cur.execute("SELECT Value FROM ReportData WHERE ReportDataDictionaryIndex=?;", (11,))
values = [row[0] for row in cur.fetchall()]
total_electricity = sum(values)
print("Total site electricity (J):", total_electricity)


# heating load energy consumption
heating_indices = [251, 388, 453]  # Zone Air System Sensible Heating Energy
heating_values = []

for idx in heating_indices:
    cur.execute("SELECT Value FROM ReportData WHERE ReportDataDictionaryIndex=?;", (idx,))
    heating_values.extend([row[0] for row in cur.fetchall()])

total_heating = sum(heating_values)
print("Total heating energy (J):", total_heating)

# cooling load energy consumption
cooling_indices = [336, 425, 490]  # Zone Air System Sensible Cooling Energy
cooling_values = []

for idx in cooling_indices:
    cur.execute("SELECT Value FROM ReportData WHERE ReportDataDictionaryIndex=?;", (idx,))
    cooling_values.extend([row[0] for row in cur.fetchall()])

total_cooling = sum(cooling_values)
print("Total cooling energy (J):", total_cooling)

# peak zone temp
temperature_indices = [250, 387, 452]  # Zone Air Temperature
temps = []

for idx in temperature_indices:
    cur.execute("SELECT Value FROM ReportData WHERE ReportDataDictionaryIndex=?;", (idx,))
    temps.extend([row[0] for row in cur.fetchall()])

peak_temperature = max(temps)
print("Peak zone temperature (°C):", peak_temperature)

conn.close()