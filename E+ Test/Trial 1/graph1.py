from eppy import modeleditor
from eppy.modeleditor import IDF
import matplotlib.pyplot as plt

# Path to the .eso file
eso_file = "/Users/danielxu/Desktop/Dartmouth College/5. Keller Lab/eplus/E+ Test/Trial 1/eplusout.eso"

# Open the .eso file
iddfile = "/Applications/EnergyPlus-23-2-0/Energy+.idd"
IDF.setiddname(iddfile)
idf = IDF()
idf.read_from_eso(eso_file)

# Get the time series data for a specific variable (e.g., Zone Air Temperature)
variable_name = "Zone Air Temperature"
data = idf.variables[variable_name.upper()].timeseries

# Plot the data
plt.figure(figsize=(12, 6))
plt.plot(data["Date/Time"], data["Value"])
plt.xlabel("Date/Time")
plt.ylabel("Temperature (C)")
plt.title("Zone Air Temperature")
plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()
plt.show()
