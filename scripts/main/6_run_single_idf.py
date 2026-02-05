import os
import subprocess
import shutil
import time
import argparse
from mpi4py import MPI
from eppy.modeleditor import IDF

# --- Configuration ---
work_dir = "/jumbo/keller-lab/Jeremy_Wang/eplus_sa/scripts/main" # Change to your working directory
idd_file_path = "/jumbo/keller-lab/Applications/EnergyPlus-24-1-0/Energy+.idd" # Change to your IDD file path
base_output_idf_dir = os.path.join(work_dir, "randomized_idfs_sobol") # change base output to sobol sequence generated
weather_file = os.path.join(
    work_dir, "weather_data",
    "USA_IL_Chicago-OHare-Intl-AP.725300_AMY_2023.epw"
)
base_output_sim_dir = os.path.join(work_dir, "output_sobol") # output_sobol stores values

# --- Simulation function ---
# output_idf_dir is the location where the idf is currently stored
# output_sim_dir is where the outputs are saved to
def run_single_simulation(idf_file, output_idf_dir, output_sim_dir):
    # Ensure EnergyPlus IDD
    IDF.setiddname(idd_file_path)
    # Create per-model output folder
    case_name = os.path.splitext(idf_file)[0]
    sim_dir = os.path.join(output_sim_dir, case_name)

    # Remove existing sim_dir if it exists to avoid conflicts
    if os.path.exists(sim_dir):
        shutil.rmtree(sim_dir)
    os.makedirs(sim_dir, exist_ok=True)

    # Load and save a validated copy (saving a copy of the idf in the output folder)
    src = os.path.join(output_idf_dir, idf_file)
    idf = IDF(src)
    validated = os.path.join(sim_dir, idf_file)
    idf.save(validated)
    # Run EnergyPlus
    subprocess.run([
        '/jumbo/keller-lab/Applications/EnergyPlus-24-1-0/energyplus',
        '--weather', weather_file,
        '--output-directory', sim_dir,
        '--idd', idd_file_path,
        # annual indicates annual run, readvars processes outputs
        '--annual', '--readvars', validated # validated is the idf
    ], check=True)

