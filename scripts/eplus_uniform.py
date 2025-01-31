import os
import requests
from datetime import datetime, timedelta
from eppy import modeleditor
from eppy.modeleditor import IDF
import numpy as np
import diyepw
import subprocess

# Change working directory
os.chdir("/Users/danielxu/Desktop/Dartmouth College/6. Keller Lab/24S/eplus_sensitivity/scripts")
print("Current working directory:", os.getcwd())

# Set EnergyPlus Input Data Dictionary
idd_file_path = "/Applications/EnergyPlus-24-2-0/Energy+.idd"
IDF.setiddname(idd_file_path)

# Load Skeleton IDF File
idfname = "/Applications/EnergyPlus-24-2-0/ExampleFiles/SingleFamilyHouse_TwoSpeed_CutoutTemperature.idf"
preidf = IDF(idfname)

# Print site location
print(preidf.idfobjects['Site:Location'])

# Define function to get active weather stations
def get_active_weather_stations(api_key, lat, lon):
    base_url = 'https://www.ncei.noaa.gov/cdo-web/api/v2/stations'
    headers = {'token': api_key}
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    params = {
        'extent': f'{lat-0.05},{lon-0.05},{lat+0.05},{lon+0.05}',
        'limit': '1000',
        'sortfield': 'mindate',
        'sortorder': 'desc'
    }
    response = requests.get(base_url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Failed to fetch data: {response.status_code} - {response.text}")
        return []
    try:
        data = response.json()
        active_stations = [
            station for station in data.get('results', []) 
            if station['maxdate'] >= one_year_ago
        ]
        return active_stations
    except ValueError:
        print("Failed to decode JSON from response.")
        return []

# Define function to update IDF parameters
def update_building_parameters(skeleton_idf_path, idd_file_path, output_idf_dir):
    IDF.setiddname(idd_file_path)
    for i in range(100):
        idf = IDF(skeleton_idf_path)

        valid_setpoints = False
        while not valid_setpoints:
            new_heating_setpoint = np.random.uniform(15.0, 22.0)
            new_cooling_setpoint = np.random.uniform(24.0, 29.0)
            if new_cooling_setpoint - new_heating_setpoint >= 5:
                valid_setpoints = True

        new_people_per_area = np.random.uniform(0.002, 0.060)
        new_flow_per_area = np.random.uniform(0.0, 1.5)
        new_design_level = np.random.uniform(1, 40)
        new_dhw_flow_rate = np.random.uniform(1e-8, 20e-8)

        people_object = idf.getobject('PEOPLE', 'LIVING ZONE People')
        people_object.People_per_Floor_Area = new_people_per_area

        infiltration_object = idf.getobject('ZONEINFILTRATION:DESIGNFLOWRATE', 'LIVING ZONE Infil 1')
        infiltration_object.Design_Flow_Rate_Calculation_Method = 'Flow/Area'
        infiltration_object.Design_Flow_Rate = new_flow_per_area

        equipment_object = idf.getobject('ELECTRICEQUIPMENT', 'LIVING ZONE ElecEq')
        equipment_object.Design_Level = new_design_level

        water_heater = idf.getobject('WATERHEATER:MIXED', 'New Water Heater')
        water_heater.Use_Side_Design_Flow_Rate = new_dhw_flow_rate

        heating_schedule = idf.getobject('SCHEDULE:COMPACT', 'Dual Heating Setpoints')
        heating_schedule.fieldvalues[6] = str(new_heating_setpoint)

        cooling_schedule = idf.getobject('SCHEDULE:COMPACT', 'Dual Cooling Setpoints')
        cooling_schedule.fieldvalues[6] = str(new_cooling_setpoint)

        output_file_path = f"{output_idf_dir}/randomized_{i+1}.idf"
        idf.save(output_file_path)

# Define function to run EnergyPlus simulations
def run_energyplus_simulation(idf_dir, weather_file, idd_file_path, output_base_dir):
    IDF.setiddname(idd_file_path)
    idf_files = [f for f in os.listdir(idf_dir) if f.endswith('.idf')]
    for idf_file in idf_files:
        idf_path = os.path.join(idf_dir, idf_file)
        idf_output_dir = os.path.join(output_base_dir, os.path.splitext(idf_file)[0])
        os.makedirs(idf_output_dir, exist_ok=True)
        idf = IDF(idf_path)
        idf_copy_path = os.path.join(idf_output_dir, os.path.basename(idf_path))
        idf.save(idf_copy_path)
        subprocess.run([
            'energyplus',
            '--weather', weather_file,
            '--output-directory', idf_output_dir,
            '--idd', idd_file_path,
            idf_copy_path
        ])

# Paths for files and directories
skeleton_idf_path = "/Users/danielxu/Desktop/Dartmouth College/6. Keller Lab/24S/eplus_sensitivity/scripts/skeleton.idf"
output_idf_dir = "/Users/danielxu/Desktop/Dartmouth College/6. Keller Lab/24S/eplus_sensitivity/scripts/randomized idfs"
idf_dir = output_idf_dir
weather_file = "/Applications/EnergyPlus-24-2-0/WeatherData/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
output_base_dir = "/Users/danielxu/Desktop/Dartmouth College/6. Keller Lab/24S/eplus_sensitivity/scripts/output"

# Execute functions
update_building_parameters(skeleton_idf_path, idd_file_path, output_idf_dir)
run_energyplus_simulation(idf_dir, weather_file, idd_file_path, output_base_dir)
