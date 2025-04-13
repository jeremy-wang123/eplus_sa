# #!/usr/bin/env python3
# """
# run_simulations.py

# Runs EnergyPlus simulations using the previously generated randomized IDF files.
# Each simulation output is saved in a separate subdirectory.
# """

# import os
# import subprocess
# from eppy import modeleditor
# from eppy.modeleditor import IDF

# # --- Set paths and directories ---
# work_dir = "/jumbo/keller-lab/Daniel_Xu/eplus_sensitivity/scripts/main"
# os.chdir(work_dir)
# print("Current working directory:", os.getcwd())

# idd_file_path = "/jumbo/keller-lab/Applications/EnergyPlus-24-1-0/Energy+.idd"
# IDF.setiddname(idd_file_path)

# # Directory containing randomized IDF files (from script 1)
# output_idf_dir = os.path.join(work_dir, "randomized_idfs")

# # Weather file used for simulation (ensure it exists in the weather_data folder)
# weather_file = os.path.join("weather_data", "USA_IL_Chicago-OHare-Intl-AP.725300_AMY_2023.epw")

# # Define the simulation output directory
# output_sim_dir = os.path.join(work_dir, "output")
# os.makedirs(output_sim_dir, exist_ok=True)

# # Clean the output simulation directory
# for filename in os.listdir(output_sim_dir):
#     file_path = os.path.join(output_sim_dir, filename)
#     if os.path.isfile(file_path) or os.path.islink(file_path):
#         os.unlink(file_path)
#     elif os.path.isdir(file_path):
#         import shutil
#         shutil.rmtree(file_path)

# # --- Define function to run EnergyPlus simulation for each IDF file ---
# def run_energyplus_simulation(output_idf_dir, weather_file, idd_file_path, output_sim_dir):
#     IDF.setiddname(idd_file_path)
#     idf_files = [f for f in os.listdir(output_idf_dir) if f.endswith('.idf')]
    
#     for idf_file in idf_files:
#         idf_path = os.path.join(output_idf_dir, idf_file)
#         simulation_output_folder = os.path.join(output_sim_dir, os.path.splitext(idf_file)[0])
#         os.makedirs(simulation_output_folder, exist_ok=True)
        
#         # Load the IDF (to validate file and save a copy in the output folder)
#         idf = IDF(idf_path)
#         idf_copy_path = os.path.join(simulation_output_folder, os.path.basename(idf_path))
#         idf.save(idf_copy_path)
        
#         # Run the EnergyPlus simulation using a subprocess call
#         subprocess.run([
#             '/jumbo/keller-lab/Applications/EnergyPlus-24-1-0/energyplus',
#             '--weather', weather_file,
#             '--output-directory', simulation_output_folder,
#             '--idd', idd_file_path,
#             '--annual',
#             '--readvars',
#             idf_copy_path
#         ])

# # --- Execute simulations ---
# if __name__ == '__main__':
#     run_energyplus_simulation(output_idf_dir, weather_file, idd_file_path, output_sim_dir)

#!/usr/bin/env python3
"""
Runs EnergyPlus simulations using the previously generated randomized IDF files.
Each simulation output is saved in a separate subdirectory.
This version parallelizes the simulations using concurrent.futures.
"""

import os
import subprocess
import shutil
import concurrent.futures
from eppy import modeleditor
from eppy.modeleditor import IDF

# --- Set paths and directories ---
work_dir = "/jumbo/keller-lab/Daniel_Xu/eplus_sensitivity/scripts/main"
os.chdir(work_dir)
print("Current working directory:", os.getcwd())

idd_file_path = "/jumbo/keller-lab/Applications/EnergyPlus-24-1-0/Energy+.idd"
# Set the IDD for the main process (each worker will reset it as needed)
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
        shutil.rmtree(file_path)

def run_single_simulation(idf_file, output_idf_dir, weather_file, idd_file_path, output_sim_dir):
    """
    Run EnergyPlus simulation for a single IDF file.
    This function is designed to be called in parallel.
    """
    # Set the IDD for this process
    IDF.setiddname(idd_file_path)
    
    # Define the path for the current IDF file
    idf_path = os.path.join(output_idf_dir, idf_file)
    
    # Create a subdirectory for the simulation's output (based on the IDF filename without extension)
    simulation_output_folder = os.path.join(output_sim_dir, os.path.splitext(idf_file)[0])
    os.makedirs(simulation_output_folder, exist_ok=True)
    
    # Load the IDF to validate the file and save a copy into the output folder
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
    print(f"Completed simulation for: {idf_file}")

def run_energyplus_simulations_parallel(output_idf_dir, weather_file, idd_file_path, output_sim_dir):
    """
    Sets up a parallel executor to run all EnergyPlus simulations concurrently.
    """
    # Gather all IDF files in the directory
    idf_files = [f for f in os.listdir(output_idf_dir) if f.endswith('.idf')]
    
    # Optionally, you can set max_workers to an appropriate number for your system.
    with concurrent.futures.ProcessPoolExecutor() as executor:
        # Submit each simulation job to the executor
        futures = [
            executor.submit(
                run_single_simulation, idf_file, output_idf_dir, weather_file, idd_file_path, output_sim_dir
            )
            for idf_file in idf_files
        ]
        
        # Wait for all submitted jobs to complete
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()  # Retrieve result (or raise exception if occurred)
            except Exception as e:
                print("An error occurred during simulation:", e)

# --- Execute simulations in parallel ---
if __name__ == '__main__':
    run_energyplus_simulations_parallel(output_idf_dir, weather_file, idd_file_path, output_sim_dir)