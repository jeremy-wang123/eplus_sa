# Sobol Sensitivity Analysis
# Importing libraries
from pathlib import Path
import time
from eppy.modeleditor import IDF
import pandas as pd
import numpy as np
import shutil
import os
from mpi4py import MPI
from scipy.stats import norm, qmc
import SALib
from SALib.sample import sobol

# Configurations
idd_file_path = "/jumbo/keller-lab/Applications/EnergyPlus-24-1-0/Energy+.idd" # Change to your IDD file path
skeleton_idf_path = Path("/jumbo/keller-lab/Jeremy_Wang/eplus_sa/data/SingleFamilyHouse_TwoSpeed_CutoutTemperature.idf") # Change to your skeleton IDF path
work_dir = Path("/jumbo/keller-lab/Jeremy_Wang/eplus_sa/scripts/main") # Change to your working directory
base_output_idf_dir = work_dir / "randomized_idfs_normal"
param_dir = work_dir / "params_normal"

# Set IDD and working dir
IDF.setiddname(idd_file_path)
os.chdir(work_dir)
base_output_idf_dir.mkdir(exist_ok=True)
param_dir.mkdir(exist_ok=True)

### Sobol sequence random sample generation

# Input: number of files generated for each seed (N), seed number
# Output: Samples (list of dictionaries, with each dictionary containing parameters and corresponding values)
def generate_sobol_sequence(num_files, seed):
    # standard deviation for each paramter is 5% of its original value
    sd_frac = 0.05
    # Means for each parameter
    means = {
        'heating_setpoint': 22.0,
        'cooling_setpoint': 26.6,
        'people_per_area': 3.0,
        'infil_flow_rate_living': 0.01,
        'infil_flow_rate_garage': 0.05,
        'infil_flow_rate_attic': 0.05,
        'watts_equip': 500,
        'watts_lights': 1000,
        'heating_COP': 4.0,
        'fan_efficiency': 0.7,
        'pressure_rise': 400.0,
        'solar_transmittance': 0.837,
        'burner_eff': 0.8,
        'vent_flow_rate': 0.131944
    }

    # additional variable for gap between heating and cooling
    gap_mean = means['cooling_setpoint'] - means['heating_setpoint']
    gap_sd = np.sqrt((sd_frac*means['heating_setpoint'])**2 + (sd_frac*means['cooling_setpoint'])**2)
    min_gap = 4 # establish minimum 4 degrees between heating and cooling setpoint
    max_solar_transmittance = 1-0.075 # max solar transmittance
    means['gap'] = gap_mean # gap to means dictionary

    # creating a dictionary to store the std
    parameter_std = {}
    parameter_names = []

    for name, mean in means.items():
        # add parameters to a list
        parameter_names.append(name)
        # adding std into dictionary
        parameter_std[name] = mean*sd_frac

    parameter_std['gap'] = gap_sd
    parameter_std['burner_eff'] = sd_frac # manually change burner efficiency


    # creating problem dictionary for sobol sampling
    # requires first initially excluding the cooling setpoint because it is dependent on the heating setpoint
    problem = {}
    names_for_problem = [n for n in parameter_names if n != 'cooling_setpoint']
    means_for_problem = {k: v for k, v in means.items() if k != 'cooling_setpoint'}
    std_for_problem = {k: v for k, v in parameter_std.items() if k != 'cooling_setpoint'}

    # determine indexes for gap and solar transmittance (required truncated normal)
    gap_idx = names_for_problem.index("gap")
    solar_idx = names_for_problem.index("solar_transmittance")

    # create normal distribution bounds for each parameter
    bounds = []
    for name in names_for_problem:
        mean = means_for_problem[name]
        sd = std_for_problem[name]
        bounds.append([mean,sd])

    bounds[gap_idx] = [min_gap, np.inf, means['gap'], parameter_std['gap']]
    bounds[solar_idx] = [0, max_solar_transmittance, means['solar_transmittance'], parameter_std['solar_transmittance']]

    # creating distributions
    dists = ['norm'] * len(names_for_problem)
    dists[gap_idx] = "truncnorm"
    dists[solar_idx] = "truncnorm"

    # dictionary formatted for Sobol sequence
    problem = {
        'num_vars': len(names_for_problem),
        'names': names_for_problem,
        'bounds': bounds,
        'dists': dists
    }

    # conduct sobol sequence sampling
    N = 1000 # baseline number of samples
    param_values = sobol.sample(problem, N, calc_second_order=True, seed = seed) # array with dimensions [N*(2P+2), P]

    ### reintegrating the cooling setpoint into the generated sample
    # Find the column index of heating_sp
    heating_idx = problem['names'].index('heating_setpoint')
    gap_idx = problem['names'].index('gap')

    # Extract heating_sp samples from param_values
    heating_samples = param_values[:, heating_idx]
    gap_samples = param_values[:, gap_idx]
    cooling_samples = heating_samples + gap_samples # calculate cooling samples

    #  update parameter values to reinsert cooling setpoint
    param_values = np.insert(param_values, heating_idx+1, cooling_samples, axis=1) # inserting it in correct index
    param_values = np.delete(param_values, gap_idx+1, axis=1) # deleting the gap column of values
    parameter_names.remove('gap') # delete gap from list of parameters
    del means['gap']

    ### Creating samples
    # convert param_values into a list of dictionaries, where the keys correspond to the input parameters
    samples = []
    for i in range(len(param_values)):
        sample_dict = {}
        for j in range(param_values.shape[1]):
            sample_dict[parameter_names[j]] = param_values[i,j]
        samples.append(sample_dict)

    ### validating samples 
    invalid_samples = []
    for i, dict in enumerate(samples):
        # making sure heating point is below cooling point
        if  (dict['cooling_setpoint'] - dict['heating_setpoint']) < min_gap:
            print('Setpoint Error')
            invalid_samples.append(i)

    if not invalid_samples:
        print("No invalid samples")
    else:
        print("Invalid samples:", invalid_samples)

    ### returning outputs
    return samples


### IDF Update

# --- IDF Update Function ---

# writes the values from the previous sample generater into actual idf files
def process_sample(args):
    # params is each row within samples (a singular row of parameters)
    i, params, output_idf_dir = args
    # Ensure each process has IDD loaded
    IDF.setiddname(idd_file_path) # indicates which IDD file to use
    idf = IDF(str(skeleton_idf_path)) # loads template idf
    
    ### helpful to imagine the energyplus idf has divided into "blocks", with parameters within the blocks indexed by order
    # each block has a key (type of object), name, and field values contained inside
    def update_schedule_field(schedule, idx, val):
        try:
            # checking to make sure the value stored is a number
            float(schedule.fieldvalues[idx])
            # converting and rounding values into a string, putting into schedule
            schedule.fieldvalues[idx] = str(round(val, 2))
        except Exception:
            pass
    
    # Heating & cooling schedules
    try:
        sched_h = idf.getobject('SCHEDULE:COMPACT', 'Dual Heating Setpoints')
        update_schedule_field(sched_h, 6, params['heating_setpoint'])
    except Exception as e:
        print(f"Error updating heating schedule (sample {i+1}): {e}")
    try:
        sched_c = idf.getobject('SCHEDULE:COMPACT', 'Dual Cooling Setpoints')
        update_schedule_field(sched_c, 6, params['cooling_setpoint'])
    except Exception as e:
        print(f"Error updating cooling schedule (sample {i+1}): {e}")
    
    # PEOPLE
    try:
        ppl = idf.getobject('PEOPLE', 'LIVING ZONE People')
        ppl.fieldvalues[5] = params['people_per_area']
    except Exception as e:
        print(f"Error updating PEOPLE: {e}")
    
    # Infiltration (3 parameters relating to infiltration)
    for zone, key in [('Living', 'infil_flow_rate_living'),
                      ('Garage', 'infil_flow_rate_garage'),
                      ('Attic', 'infil_flow_rate_attic')]:
        try:
            infil = idf.getobject('ZONEINFILTRATION:DESIGNFLOWRATE', f'{zone.upper()} ZONE Infil 1')
            infil.fieldvalues[5] = params[key]
        except Exception as e:
            print(f"Error updating {zone} infiltration: {e}")
    
    # Equipment & lighting
    try:
        eq = idf.getobject('ELECTRICEQUIPMENT', 'LIVING ZONE ElecEq')
        eq.Design_Level = params['watts_equip'] # named attribute (no index)
    except Exception as e:
        print(f"Error updating electric equipment: {e}")
    try:
        lt = idf.getobject('LIGHTS', 'LIVING ZONE Lights')
        lt.Lighting_Level = params['watts_lights']
    except Exception as e:
        print(f"Error updating lights: {e}")
    
    # Heating coil COP
    try:
        coil = idf.getobject('COIL:HEATING:DX:MULTISPEED', 'Heat Pump DX Heating Coil 1')
        coil.Speed_1_Gross_Rated_Heating_COP = params['heating_COP']
        coil.Speed_2_Gross_Rated_Heating_COP = params['heating_COP']
    except Exception as e:
        print(f"Error updating heating coil COP: {e}")
    
    # Fan parameters
    try:
        fan = idf.getobject('FAN:ONOFF', 'Supply Fan 1')
        fan.fieldvalues[3] = str(round(params['fan_efficiency'], 3))
        fan.fieldvalues[4] = str(round(params['pressure_rise'], 1))
    except Exception as e:
        print(f"Error updating fan: {e}")
    
    # Glazing - Some updating error is happening here
    try:
        glazing = idf.getobject('WINDOWMATERIAL:GLAZING', 'CLEAR 3MM')
        glazing.fieldvalues[5] = str(round(params['solar_transmittance'], 3))
    except Exception as e:
        print(f"Error updating glazing: {e}")
    
    # Burner efficiency
    try:
        burner = idf.getobject('COIL:HEATING:FUEL', 'Supp Heating Coil 1')
        burner.fieldvalues[4] = str(round(params['burner_eff'], 3))
    except Exception as e:
        print(f"Error updating burner: {e}")
    
    # Ventilation
    try:
        vent = idf.getobject('ZONEVENTILATION:DESIGNFLOWRATE', 'LIVING ZONE Ventl 1')
        vent.fieldvalues[5] = str(round(params['vent_flow_rate'], 6))
    except Exception as e:
        print(f"Error updating ventilation: {e}")
    
    # Save
    out_path = output_idf_dir / f"randomized_{i+1}.idf"
    idf.save(str(out_path))
    return (i, out_path.name)

### MPI
def run_simulation(seed_num):
    start = time.time()
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size() # number of mpi ranks
    
    # Create a seed-specific output directory
    output_idf_dir = base_output_idf_dir / f"seed_{seed_num}"
    if rank == 0:
        output_idf_dir.mkdir(exist_ok=True)
    comm.Barrier()  # Ensure directory is created before other ranks try to use it
    
    # Rank 0 generates samples & cleans output dir (rank 0 is the "master" rank)
    if rank == 0:
        num_files = 1000
        seed = 42 + seed_num  # Different seed for each run
        samples = generate_sobol_sequence(num_files, seed=seed)
        
        # Clean output directory
        for item in output_idf_dir.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        # i is the index, sample is the parameter value, and output_idf_dir is the destination folder        
        args = [(i, sample, output_idf_dir) for i, sample in enumerate(samples)]
    else:
        args = None
        samples = None
    
    # Broadcast args and synchronize (sending data from rank 0 to all other ranks)
    args = comm.bcast(args, root=0)
    samples = comm.bcast(samples, root=0)
    comm.Barrier()
    
    # Divide work among ranks
    local = args[rank::size]
    local_out = [process_sample(a) for a in local] # takes sample and modifies idf using local rank
    
    # Gather results
    all_out = comm.gather(local_out, root=0)
    
    # Rank 0 writes CSV and timing
    if rank == 0:
        flat_with_idx = [item for sub in all_out for item in sub]
        flat_with_idx.sort(key=lambda x: x[0])  # sort by index i

        # Need to extract just the filenames after sorting
        sorted_filenames = [name for _, name in flat_with_idx]

        df = pd.DataFrame(samples)
        df.insert(0, 'IDF_file', sorted_filenames) # row 0 is the idf file name
        df.insert(1, 'seed', seed) # row 1 is the seed
        csv_file = param_dir / f"simulation_parameters_seed_{seed_num}.csv"
        df.to_csv(csv_file, index=False)
        end = time.time()
        print(f"Seed {seed_num}: Simulation parameters saved to {csv_file}")
        print(f"Seed {seed_num}: Total execution time: {end - start:.2f} seconds")
    
    return

if __name__ == '__main__':
    overall_start = time.time()
    
    # Run for 5 different seeds
    for seed_num in range(1, 6):
        print(f"Starting ensemble generation with seed {seed_num}...")
        run_simulation(seed_num)
        print(f"Completed ensemble generation with seed {seed_num}")
    
    # Only rank 0 prints the final timing
    comm = MPI.COMM_WORLD
    if comm.Get_rank() == 0:
        overall_end = time.time()
        print(f"All 5 simulations completed in {overall_end - overall_start:.2f} seconds")

# mpirun -hostfile myhosts -np 225 /jumbo/keller-lab/Applications/mambaforge/envs/eplus/bin/python 4_eplus_normalsampling.py
