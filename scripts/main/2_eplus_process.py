#!/usr/bin/env python3
"""
Runs EnergyPlus simulations using the previously generated randomized IDF files.
Parallelized across multiple nodes with MPI (mpi4py).
Each MPI rank processes a subset of the IDF files.
"""

import os
import subprocess
import shutil
from mpi4py import MPI
from eppy.modeleditor import IDF

# --- Configuration ---
work_dir = "/jumbo/keller-lab/Daniel_Xu/eplus_sensitivity/scripts/main"
idd_file_path = "/jumbo/keller-lab/Applications/EnergyPlus-24-1-0/Energy+.idd"
output_idf_dir = os.path.join(work_dir, "randomized_idfs")
weather_file = os.path.join(work_dir, "weather_data", "USA_IL_Chicago-OHare-Intl-AP.725300_AMY_2023.epw")
output_sim_dir = os.path.join(work_dir, "output")

# Ensure output directory exists
os.makedirs(output_sim_dir, exist_ok=True)

# MPI initialization
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Change to working directory
os.chdir(work_dir)
print(f"Rank {rank}/{size} starting. Working dir: {work_dir}")

# Rank 0: prepare list of IDF files and clean output
if rank == 0:
    # Clean the output simulation directory
    if os.path.isdir(output_sim_dir):
        for entry in os.listdir(output_sim_dir):
            path = os.path.join(output_sim_dir, entry)
            if os.path.isdir(path): shutil.rmtree(path)
            else: os.remove(path)

    # Gather all IDF files
    idf_files = [f for f in os.listdir(output_idf_dir) if f.endswith('.idf')]
    idf_files.sort()
else:
    idf_files = None

# Broadcast the list of files to all ranks
idf_files = comm.bcast(idf_files, root=0)

# Each rank processes every size-th file
local_files = idf_files[rank::size]
print(f"Rank {rank}: Assigned {len(local_files)} files to simulate.")

# Function to run one simulation
def run_single_simulation(idf_file):
    IDF.setiddname(idd_file_path)

    # create output subfolder
    name = os.path.splitext(idf_file)[0]
    sim_dir = os.path.join(output_sim_dir, name)
    os.makedirs(sim_dir, exist_ok=True)

    # copy and validate IDF
    src = os.path.join(output_idf_dir, idf_file)
    idf = IDF(src)
    copy_path = os.path.join(sim_dir, idf_file)
    idf.save(copy_path)

    # run EnergyPlus
    subprocess.run([
        '/jumbo/keller-lab/Applications/EnergyPlus-24-1-0/energyplus',
        '--weather', weather_file,
        '--output-directory', sim_dir,
        '--idd', idd_file_path,
        '--annual',
        '--readvars',
        copy_path
    ], check=True)
    print(f"Rank {rank}: Completed {idf_file}")

# Execute local simulations
for idf_file in local_files:
    try:
        run_single_simulation(idf_file)
    except Exception as e:
        print(f"Rank {rank}: Error with {idf_file}: {e}")

# Synchronize and finish
comm.Barrier()
if rank == 0:
    print("All simulations completed.")