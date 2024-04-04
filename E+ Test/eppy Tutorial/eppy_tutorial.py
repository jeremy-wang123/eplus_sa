# This is the tutorial that is provided on the eppy documentation online. 

import sys
pathnameto_eppy = 'c:/eppy'
pathnameto_eppy = '../'
sys.path.append(pathnameto_eppy)

# Changing working directory
import os
os.chdir("/Users/danielxu/Desktop/Dartmouth College/5. Keller Lab/eplus/E+ Test/eppy Tutorial")
print("Current working directory:", os.getcwd())


# Importing necessary libraries
from eppy import modeleditor
from eppy.modeleditor import IDF 

iddfile = "/Applications/EnergyPlus-23-2-0/Energy+.idd" # EnergyPlus data dictionary 
fname1 = "/Applications/EnergyPlus-23-2-0/ExampleFiles/BasicsFiles/Exercise1A.idf" # Data set for building in Exercise 1A
epwfile = "/Applications/EnergyPlus-23-2-0/WeatherData/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw" # Corresponding weather data 

IDF.setiddname(iddfile) # Set the location of the Energyplus IDD file 
idf1 = IDF(fname1) # Creating a new object that reads in the IDF in EnergyPlus

idf1.printidf() # Prints the contents of the IDF file 

print(idf1.idfobjects['BUILDING']) # Put the name of the object you'd like to look at in brackets

building = idf1.idfobjects['BUILDING'][0] # Retrieves the first building object in the IDF and assigns it to a new object
print(building.Name)

building.Name = "Chicago Midway International Airport" # Changing the name of the building object 
print(building.Name) # Printing just the building name 

idf1.printidf()

# Examples of other information that can be isolated and pulled 
print(building.Name)
print(building.Terrain)
print(building.North_Axis)
print(building.Loads_Convergence_Tolerance_Value)
print(building.Temperature_Convergence_Tolerance_Value)
print(building.Solar_Distribution)
print(building.Maximum_Number_of_Warmup_Days)
print(building.Minimum_Number_of_Warmup_Days)

idf1.saveas('something.idf') # Saving the modified IDF 

try:
    IDF.setiddname(iddfile)
except modeleditor.IDDAlreadySetError as e:
    pass

fname2 = "/Applications/EnergyPlus-23-2-0/ExampleFiles/ASHRAE901_Hospital_STD2019_Denver.idf" # Another sample IDF file 
idf2 = IDF(fname2)
idf2.printidf()
materials = idf2.idfobjects["MATERIALS"]
print(materials)