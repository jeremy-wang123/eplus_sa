#!/usr/bin/env python3
"""
run_simulations.py

Runs EnergyPlus simulations using the previously generated randomized IDF files.
Each simulation output is saved in a separate subdirectory.
"""

import os
import subprocess
from eppy import modeleditor
from eppy.modeleditor import IDF

# --- Set paths and directories ---
work_dir = "/jumbo/keller-lab/Daniel_Xu/eplus_sensitivity/scripts/main"
os.chdir(work_dir)
print("Current working directory:", os.getcwd())

idd_file_path = "/jumbo/keller-lab/Applications/EnergyPlus-24-1-0/Energy+.idd"
IDF.setiddname(idd_file_path)

# Directory containing randomized IDF files (from script 1)
output_idf_dir = os.path.join(work_dir, "randomized_idfs")

# Weather file used for simulation (ensure it exists in the weather_data folder)
weather_file = os.path.join("weather_data", "USA_IL_Chicago-OHare-Intl-AP.725300_AMY_2023.epw")

# Define the simulation output directory
output_sim_dir = os.path.join(work_dir, "output")
os.makedirs(output_sim_dir, exist_ok=True)

# Clean the output simulation directory
for filename in os.listdir(output_sim_dir):
    file_path = os.path.join(output_sim_dir, filename)
    if os.path.isfile(file_path) or os.path.islink(file_path):
        os.unlink(file_path)
    elif os.path.isdir(file_path):
        import shutil
        shutil.rmtree(file_path)

# --- Define function to run EnergyPlus simulation for each IDF file ---
def run_energyplus_simulation(output_idf_dir, weather_file, idd_file_path, output_sim_dir):
    IDF.setiddname(idd_file_path)
    idf_files = [f for f in os.listdir(output_idf_dir) if f.endswith('.idf')]
    
    for idf_file in idf_files:
        idf_path = os.path.join(output_idf_dir, idf_file)
        simulation_output_folder = os.path.join(output_sim_dir, os.path.splitext(idf_file)[0])
        os.makedirs(simulation_output_folder, exist_ok=True)
        
        # Load the IDF (to validate file and save a copy in the output folder)
        idf = IDF(idf_path)
        idf_copy_path = os.path.join(simulation_output_folder, os.path.basename(idf_path))
        idf.save(idf_copy_path)
        
        # Run the EnergyPlus simulation using a subprocess call
        subprocess.run([
            '/jumbo/keller-lab/Applications/EnergyPlus-24-1-0/energyplus',
            '--weather', weather_file,
            '--output-directory', simulation_output_folder,
            '--idd', idd_file_path,
            '--annual',
            '--readvars',
            idf_copy_path
        ])

# --- Execute simulations ---
if __name__ == '__main__':
    run_energyplus_simulation(output_idf_dir, weather_file, idd_file_path, output_sim_dir)