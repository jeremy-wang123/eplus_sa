# This is a test file to trial run an analysis using eppy, the EnergyPlus API, and a test data file. 

# Importing eppy 
from eppy import modeleditor
from eppy.modeleditor import IDF
import matplotlib.pyplot as plt
import os
# import sys
# pathnameto_eppy = '/opt/homebrew/lib/python3.11/site-packages/eppy'
# pathnameto_eppy = '../'
# sys.path.append(pathnameto_eppy)

iddfile = "/Applications/EnergyPlus-23-2-0/Energy+.idd"
IDF.setiddname(iddfile)

idfname = "/Applications/EnergyPlus-23-2-0/ExampleFiles/BasicsFiles/Exercise1A.idf"
epwfile = "/Applications/EnergyPlus-23-2-0/WeatherData/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"

idf = IDF(idfname, epwfile)
idf.run()



# eplusout.shd: Contains shading information for the building.
# eplusout.bnd: Contains boundary condition information.
# eplusout.dxf: Contains the building geometry in DXF (Drawing Exchange Format) format.
# eplusout.eio: Contains a summary of the input and output variables used in the simulation.
# eplusout.end: Contains information about the end of the simulation.
# eplusout.err: Contains any error messages generated during the simulation.
# eplusout.eso: Contains detailed simulation results, such as temperatures, energy consumption, and other variables, in a binary format.
# eplusout.mdd: Contains metadata about the variables in the eplusout.eso file.
# eplusout.mtd: Contains additional metadata about the simulation.
# eplusout.mtr: Contains hourly, daily, and monthly reports of various variables.
# eplusout.rdd: Contains the Runtime Description (RDD) file, which describes the format of the eplusout.eso file.
# eplusout.audit: Contains an audit of the input file, showing any warnings or potential issues with the input.

# Set the path to the EnergyPlus executable
# energyplus_path = "/Applications/EnergyPlus-x-x-x/"

# # Set the path to the EnergyPlus input file (IDF) and weather file (EPW)
# idf_path = "input_file.idf"
# weather_file = "weather_file.epw"

# # Initialize the IDF model
# IDF.setiddname(os.path.join(energyplus_path, "Energy+.idd"))
# idf = IDF(idf_path)

# # Modify your IDF model as needed
# # For example, change the name of the building
# idf.idfobjects["BUILDING"][0].Name = "New Building Name"

# # Save the modified IDF to a new file
# new_idf_path = "/path/to/your/modified_input_file.idf"
# idf.saveas(new_idf_path)

# # Run the EnergyPlus simulation
# command = f"{energyplus_path}/energyplus -w {weather_file} -d /path/to/output/directory {new_idf_path}"
# os.system(command)
