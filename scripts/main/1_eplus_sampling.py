#!/usr/bin/env python3
"""
MPI-enabled script to generate randomized EnergyPlus IDF files via Latin Hypercube Sampling,
update every relevant object (heating, cooling, people, infiltration, equipment, lighting,
coils, fans, glazing, burner, ventilation), and record simulation parameters.
Parallelized across MPI ranks.
"""
from pathlib import Path
import time
from eppy.modeleditor import IDF
import pandas as pd
import numpy as np
import shutil
import os
from mpi4py import MPI
from scipy.stats import norm, qmc

# --- Configurations ---
idd_file_path = "/jumbo/keller-lab/Applications/EnergyPlus-24-1-0/Energy+.idd"
skeleton_idf_path = Path("../../data/SingleFamilyHouse_TwoSpeed_CutoutTemperature.idf")
work_dir = Path("/jumbo/keller-lab/Daniel_Xu/eplus_sensitivity/scripts/main")
base_output_idf_dir = work_dir / "randomized_idfs"
param_dir = work_dir / "params"

# Set IDD and working dir
IDF.setiddname(idd_file_path)
os.chdir(work_dir)
base_output_idf_dir.mkdir(exist_ok=True)
param_dir.mkdir(exist_ok=True)

# --- Latin Hypercube Sampling and Valid Samples Generation ---
def generate_valid_samples(num_files, seed=None, verbose=True):
    sd_frac = 0.05
    # Means for each parameter
    means = {
        'heating_sp': 22.0,
        'cooling_sp': 26.6,
        'people_per_area': 3.0,
        'infil_flow_rate': 0.01,
        'watts_equip': 500,
        'watts_lights': 1000,
        'heating_COP': 4.0,
        'fan_efficiency': 0.7,
        'pressure_rise': 400.0,
        'solar_transmittance': 0.837,
        'burner_eff': 0.8,
        'vent_flow_rate': 0.131944
    }
    # Standard deviations
    sds = {k: v * sd_frac for k, v in means.items()}
    sds['burner_eff'] = sd_frac
    gap_mean = means['cooling_sp'] - means['heating_sp']
    gap_sd = np.sqrt((sd_frac*means['heating_sp'])**2 + (sd_frac*means['cooling_sp'])**2)
    
    # Initialize sampler with seed if provided
    rng = np.random.RandomState(seed) if seed is not None else None
    sampler = qmc.LatinHypercube(d=14, seed=rng)
    sample_matrix = sampler.random(n=num_files * 2)
    
    valid_samples = []
    for row in sample_matrix:
        new_heating_sp = norm.ppf(row[0], loc=means['heating_sp'], scale=sds['heating_sp'])
        new_gap = max(norm.ppf(row[1], loc=gap_mean, scale=gap_sd), 4.0)
        new_cooling_sp = new_heating_sp + new_gap
        
        new_values = {
            'people_per_area': norm.ppf(row[2], loc=means['people_per_area'], scale=sds['people_per_area']),
            'infil_flow_rate_living': norm.ppf(row[3], loc=means['infil_flow_rate'], scale=sds['infil_flow_rate']),
            'infil_flow_rate_garage': norm.ppf(row[4], loc=means['infil_flow_rate'], scale=sds['infil_flow_rate']),
            'infil_flow_rate_attic': norm.ppf(row[5], loc=means['infil_flow_rate'], scale=sds['infil_flow_rate']),
            'watts_equip': norm.ppf(row[6], loc=means['watts_equip'], scale=sds['watts_equip']),
            'watts_lights': norm.ppf(row[7], loc=means['watts_lights'], scale=sds['watts_lights']),
            'heating_COP': norm.ppf(row[8], loc=means['heating_COP'], scale=sds['heating_COP']),
            'fan_efficiency': norm.ppf(row[9], loc=means['fan_efficiency'], scale=sds['fan_efficiency']),
            'pressure_rise': norm.ppf(row[10], loc=means['pressure_rise'], scale=sds['pressure_rise']),
            'solar_transmittance': np.clip(
                norm.ppf(row[11], loc=means['solar_transmittance'], scale=sds['solar_transmittance']), 0, 1
            ),
            'burner_eff': np.clip(norm.ppf(row[12], loc=means['burner_eff'], scale=sds['burner_eff']), 0.7, 0.9),
            'vent_flow_rate': norm.ppf(row[13], loc=means['vent_flow_rate'], scale=sds['vent_flow_rate'])
        }
        # Validate
        if (new_heating_sp > 0 and new_cooling_sp > 0 and
            all(v >= 0 for v in new_values.values())):
            valid_samples.append({
                'heating_setpoint': new_heating_sp,
                'cooling_setpoint': new_cooling_sp,
                **new_values
            })
        if len(valid_samples) >= num_files:
            break
    if verbose and len(valid_samples) < num_files:
        print(f"Warning: only generated {len(valid_samples)} of {num_files} samples.")
    return valid_samples

# --- IDF Update Function ---
def process_sample(args):
    i, params, output_idf_dir = args
    # Ensure each process has IDD loaded
    IDF.setiddname(idd_file_path)
    idf = IDF(str(skeleton_idf_path))
    
    def update_schedule_field(schedule, idx, val):
        try:
            float(schedule.fieldvalues[idx])
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
    
    # Infiltration
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
        eq.Design_Level = params['watts_equip']
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
    
    # Glazing
    try:
        glazing = idf.getobject('WINDOWMATERIAL:GLAZING', 'CLEAR 3MM')
        glazing.fieldvalues[4] = str(round(params['solar_transmittance'], 3))
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
    return out_path.name

def run_simulation(seed_num):
    start = time.time()
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    
    # Create a seed-specific output directory
    output_idf_dir = base_output_idf_dir / f"seed_{seed_num}"
    if rank == 0:
        output_idf_dir.mkdir(exist_ok=True)
    comm.Barrier()  # Ensure directory is created before other ranks try to use it
    
    # Rank 0 generates samples & cleans output dir
    if rank == 0:
        num_files = 10000
        seed = 42 + seed_num  # Different seed for each run
        samples = generate_valid_samples(num_files, seed=seed)
        
        # Clean output directory
        for item in output_idf_dir.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
                
        args = [(i, sample, output_idf_dir) for i, sample in enumerate(samples)]
    else:
        args = None
        samples = None
    
    # Broadcast args and synchronize
    args = comm.bcast(args, root=0)
    samples = comm.bcast(samples, root=0)
    comm.Barrier()
    
    # Divide work among ranks
    local = args[rank::size]
    local_out = [process_sample(a) for a in local]
    
    # Gather results
    all_out = comm.gather(local_out, root=0)
    
    # Rank 0 writes CSV and timing
    if rank == 0:
        flat = [name for sub in all_out for name in sub]
        df = pd.DataFrame(samples)
        df.insert(0, 'IDF_file', flat)
        df.insert(1, 'seed', seed)
        csv_file = param_dir / f"simulation_parameters_seed_{seed_num}.csv"
        df.to_csv(csv_file, index=False)
        end = time.time()
        print(f"Seed {seed_num}: Simulation parameters saved to {csv_file}")
        print(f"Seed {seed_num}: Total execution time: {end - start:.2f} seconds")
    
    return

if __name__ == '__main__':
    overall_start = time.time()
    
    # Run for 5 different seeds
    for seed_num in range(1, 21):
        print(f"Starting ensemble generation with seed {seed_num}...")
        run_simulation(seed_num)
        print(f"Completed ensemble generation with seed {seed_num}")
    
    # Only rank 0 prints the final timing
    comm = MPI.COMM_WORLD
    if comm.Get_rank() == 0:
        overall_end = time.time()
        print(f"All 5 simulations completed in {overall_end - overall_start:.2f} seconds")

# mpirun -hostfile myhosts -np 225 /jumbo/keller-lab/Applications/mambaforge/envs/eplus/bin/python 1_eplus_sampling.py