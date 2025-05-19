#!/usr/bin/env python3
"""
Runs EnergyPlus simulations using the previously generated randomized IDF files.
Parallelized across MPI ranks (mpi4py).
Processes multiple seed directories (seed_1 through seed_20) in a single invocation.
Outputs are placed under output/<seed_i>.
"""
import os
import subprocess
import shutil
import time
import argparse
from mpi4py import MPI
from eppy.modeleditor import IDF
  
# --- Argument parsing ---
parser = argparse.ArgumentParser(
    description="Run EnergyPlus sims for multiple seed directories."
)
parser.add_argument(
    "--seeds",
    default="1-20",
    help="Which seed directories to process (e.g., '1-5' or '1,3,5' or '1-10,15,18-20')"
)
args = parser.parse_args()

# Parse seed range input
def parse_seed_range(seed_range_str):
    seeds = []
    parts = seed_range_str.split(',')
    for part in parts:
        if '-' in part:
            start, end = map(int, part.split('-'))
            seeds.extend(range(start, end + 1))
        else:
            seeds.append(int(part))
    return [f"seed_{i}" for i in seeds]

selected_seeds = parse_seed_range(args.seeds)
  
# --- Configuration ---
work_dir = "/jumbo/keller-lab/Daniel_Xu/eplus_sensitivity/scripts/main" # Change to your working directory
idd_file_path = "/jumbo/keller-lab/Applications/EnergyPlus-24-1-0/Energy+.idd" # Change to your IDD file path
base_output_idf_dir = os.path.join(work_dir, "randomized_idfs")
weather_file = os.path.join(
    work_dir, "weather_data",
    "USA_IL_Chicago-OHare-Intl-AP.725300_AMY_2023.epw"
)
base_output_sim_dir = os.path.join(work_dir, "output")
  
# --- MPI initialization ---
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()
  
# Change to working directory
os.chdir(work_dir)
if rank == 0:
    print(f"Processing seeds: {', '.join(selected_seeds)}")
  
# --- Simulation function ---
def run_single_simulation(idf_file, output_idf_dir, output_sim_dir):
    # Ensure EnergyPlus IDD
    IDF.setiddname(idd_file_path)
    # Create per-model output folder
    case_name = os.path.splitext(idf_file)[0]
    sim_dir = os.path.join(output_sim_dir, case_name)
    os.makedirs(sim_dir, exist_ok=True)
    # Load and save a validated copy
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
        '--annual', '--readvars', validated
    ], check=True)
    print(f"Rank {rank}: Completed {idf_file}")
  
# Broadcast seed list to all ranks
if rank == 0:
    seed_dirs = selected_seeds
else:
    seed_dirs = None
seed_dirs = comm.bcast(seed_dirs, root=0)
  
overall_start = time.time()
for seed_dir in seed_dirs:
    seed_start = time.time()
    output_idf_dir = os.path.join(base_output_idf_dir, seed_dir)
    output_sim_dir = os.path.join(base_output_sim_dir, seed_dir)
    
    # Check if the seed directory exists
    if not os.path.exists(output_idf_dir):
        if rank == 0:
            print(f"Warning: Directory {output_idf_dir} does not exist. Skipping.")
        continue
    
    # Rank 0 prepares directories
    if rank == 0:
        os.makedirs(output_sim_dir, exist_ok=True)
        # Clean existing simulations
        for entry in os.listdir(output_sim_dir):
            path = os.path.join(output_sim_dir, entry)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        idf_files = sorted(
            f for f in os.listdir(output_idf_dir) if f.endswith('.idf')
        )
        print(f"[{seed_dir}] Found {len(idf_files)} IDF files to simulate")
    else:
        idf_files = None
  
    # Synchronize before broadcasting
    comm.Barrier()
    idf_files = comm.bcast(idf_files, root=0)
  
    # Distribute files across ranks
    local_files = idf_files[rank::size]
    print(f"Rank {rank} • {seed_dir}: {len(local_files)} files assigned")
  
    # Run local simulations
    for idf_file in local_files:
        try:
            run_single_simulation(idf_file, output_idf_dir, output_sim_dir)
        except Exception as e:
            print(f"Rank {rank} • {seed_dir}: Error {idf_file}: {e}")
  
    comm.Barrier()
    if rank == 0:
        print(f"[{seed_dir}] completed in {time.time() - seed_start:.1f}s")
  
# Final sync and report
comm.Barrier()
if rank == 0:
    print(f"All done in {time.time() - overall_start:.1f}s")