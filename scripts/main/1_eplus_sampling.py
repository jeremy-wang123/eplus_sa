# #!/usr/bin/env python3
# """
# Generates randomized EnergyPlus IDF files by sampling parameters via Latin Hypercube Sampling.
# It also downloads (or creates) weather files required for the simulations.
# Parallelized.
# """

# # --- Import necessary libraries ---
# from pathlib import Path
# from eppy import modeleditor
# from eppy.modeleditor import IDF
# import pandas as pd
# import numpy as np
# import shutil
# import os
# import requests
# import subprocess
# import esoreader
# # import diyepw
# from scipy.stats import norm, qmc
# from concurrent.futures import ProcessPoolExecutor

# # --- Global configurations ---
# idd_file_path = "/jumbo/keller-lab/Applications/EnergyPlus-24-1-0/Energy+.idd" 
# IDF.setiddname(idd_file_path)
# skeleton_idf_path = Path("../../data/SingleFamilyHouse_TwoSpeed_CutoutTemperature.idf")
# work_dir = Path("/jumbo/keller-lab/Daniel_Xu/eplus_sensitivity/scripts/main")
# os.chdir(work_dir)
# print("Current working directory:", Path.cwd())

# # # --- Create and populate weather data directory ---
# # weather_dir = work_dir / "weather_data"
# # weather_dir.mkdir(exist_ok=True)
# # os.chdir(weather_dir)
# # diyepw.create_amy_epw_files_for_years_and_wmos(
# #     [2023],
# #     [725300],
# #     max_records_to_interpolate=6,
# #     max_records_to_impute=48,
# #     max_missing_amy_rows=5,
# #     allow_downloads=True,
# #     amy_epw_dir="."  # Use current directory
# # )
# # os.chdir(work_dir)

# # --- Prepare directory for randomized IDF files ---
# output_idf_dir = work_dir / "randomized_idfs"
# output_idf_dir.mkdir(exist_ok=True)
# # Clean up any existing files in the output directory
# for item in output_idf_dir.iterdir():
#     if item.is_file() or item.is_symlink():
#         item.unlink()
#     elif item.is_dir():
#         shutil.rmtree(item)

# # --- Latin Hypercube Sampling and Valid Samples Generation ---
# def generate_valid_samples(num_files, verbose=True):
#     # Define simulation parameters (means and standard deviations)
#     sd_frac = 0.05

#     mean_heating_sp = 22.0
#     mean_cooling_sp = 26.6
#     gap_mean = mean_cooling_sp - mean_heating_sp
#     mean_people_per_area = 3.0      
#     mean_infil_flow_rate = 0.01     
#     mean_watts_equip = 500          
#     mean_watts_lights = 1000        
#     mean_heating_COP = 4.0          
#     mean_fan_efficiency = 0.7       
#     mean_pressure_rise = 400.0      
#     mean_solar_transmittance = 0.837  
#     mean_burner_eff = 0.8           
#     mean_vent_flow_rate = 0.131944  

#     sd_heating_sp = sd_frac * mean_heating_sp 
#     sd_cooling_sp = sd_frac * mean_cooling_sp
#     gap_sd = np.sqrt(sd_heating_sp**2 + sd_cooling_sp**2)
#     sd_people_per_area = sd_frac * mean_people_per_area
#     sd_infil_flow_rate = sd_frac * mean_infil_flow_rate
#     sd_mean_watts_equip = sd_frac * mean_watts_equip
#     sd_mean_watts_lights = sd_frac * mean_watts_lights
#     sd_heating_COP = sd_frac * mean_heating_COP
#     sd_fan_efficiency = sd_frac * mean_fan_efficiency
#     sd_pressure_rise = sd_frac * mean_pressure_rise
#     sd_solar_transmittance = sd_frac * mean_solar_transmittance
#     sd_burner_eff = sd_frac
#     sd_vent_flow_rate = sd_frac * mean_vent_flow_rate

#     total_dims = 14
#     sampler = qmc.LatinHypercube(d=total_dims)
#     n_points = num_files * 2
#     sample_matrix = sampler.random(n=n_points)

#     valid_samples = []
#     for row in sample_matrix:
#         new_heating_sp = norm.ppf(row[0], loc=mean_heating_sp, scale=sd_heating_sp)
#         new_gap = norm.ppf(row[1], loc=gap_mean, scale=gap_sd)
#         if new_gap < 4:
#             new_gap = 4.0
#         new_cooling_sp = new_heating_sp + new_gap

#         new_people = norm.ppf(row[2], loc=mean_people_per_area, scale=sd_people_per_area)
#         new_infil_living = norm.ppf(row[3], loc=mean_infil_flow_rate, scale=sd_infil_flow_rate)
#         new_infil_garage = norm.ppf(row[4], loc=mean_infil_flow_rate, scale=sd_infil_flow_rate)
#         new_infil_attic = norm.ppf(row[5], loc=mean_infil_flow_rate, scale=sd_infil_flow_rate)
#         new_watts_equip = norm.ppf(row[6], loc=mean_watts_equip, scale=sd_mean_watts_equip)
#         new_watts_lights = norm.ppf(row[7], loc=mean_watts_lights, scale=sd_mean_watts_lights)
#         new_heating_COP = norm.ppf(row[8], loc=mean_heating_COP, scale=sd_heating_COP)
#         new_fan_efficiency = norm.ppf(row[9], loc=mean_fan_efficiency, scale=sd_fan_efficiency)
#         new_pressure_rise = norm.ppf(row[10], loc=mean_pressure_rise, scale=sd_pressure_rise)
#         new_solar_transmittance = norm.ppf(row[11], loc=mean_solar_transmittance, scale=sd_solar_transmittance)
#         new_solar_transmittance = np.clip(new_solar_transmittance, 0, 1)
#         new_burner_eff = norm.ppf(row[12], loc=mean_burner_eff, scale=sd_burner_eff)
#         new_burner_eff = np.clip(new_burner_eff, 0.7, 0.9)
#         new_vent_flow_rate = norm.ppf(row[13], loc=mean_vent_flow_rate, scale=sd_vent_flow_rate)

#         # Skip invalid samples
#         if new_heating_sp <= 0 or new_cooling_sp <= 0 or new_people < 0 or \
#            new_infil_living < 0 or new_infil_garage < 0 or new_infil_attic < 0 or \
#            new_watts_equip < 0 or new_watts_lights < 0 or new_heating_COP <= 0 or \
#            new_fan_efficiency <= 0 or new_pressure_rise <= 0 or new_vent_flow_rate < 0:
#             continue

#         valid_samples.append({
#             'heating_setpoint': new_heating_sp,
#             'cooling_setpoint': new_cooling_sp,
#             'people_per_area': new_people,
#             'infil_flow_rate_living': new_infil_living,
#             'infil_flow_rate_garage': new_infil_garage,
#             'infil_flow_rate_attic': new_infil_attic,
#             'watts_equip': new_watts_equip,
#             'watts_lights': new_watts_lights,
#             'heating_COP': new_heating_COP,
#             'fan_efficiency': new_fan_efficiency,
#             'pressure_rise': new_pressure_rise,
#             'solar_transmittance': new_solar_transmittance,
#             'burner_eff': new_burner_eff,
#             'vent_flow_rate': new_vent_flow_rate
#         })
#         if len(valid_samples) >= num_files:
#             break

#     if verbose and len(valid_samples) < num_files:
#         print("Warning: Could not generate the desired number of valid samples.")

#     if verbose:
#         print(f"Generated {len(valid_samples)} valid Latin hypercube sample(s).")
#     return valid_samples

# # --- Define a function to update a single IDF file ---
# def process_sample(args):
#     """
#     Processes a single sample: loads the skeleton IDF, updates parameters,
#     and saves the updated file.
#     """
#     i, params = args
#     # Load the skeleton IDF
#     idf = IDF(str(skeleton_idf_path))
    
#     # --- Helper function to update schedule field ---
#     def update_schedule_field(schedule, field_index, new_setpoint):
#         try:
#             float(schedule.fieldvalues[field_index])
#             schedule.fieldvalues[field_index] = str(round(new_setpoint, 2))
#         except (ValueError, TypeError):
#             pass

#     # Set the IDD file (ensure it's set in each process)
#     IDF.setiddname(idd_file_path)
    
#     # Update Dual Heating Setpoints
#     try:
#         heating_schedule = idf.getobject('SCHEDULE:COMPACT', 'Dual Heating Setpoints')
#         update_schedule_field(heating_schedule, 6, params['heating_setpoint'])
#     except Exception as e:
#         print(f"Sample {i+1}: Error updating Dual Heating Setpoints: {e}")
#     # Update Dual Cooling Setpoints
#     try:
#         cooling_schedule = idf.getobject('SCHEDULE:COMPACT', 'Dual Cooling Setpoints')
#         update_schedule_field(cooling_schedule, 6, params['cooling_setpoint'])
#     except Exception as e:
#         print(f"Sample {i+1}: Error updating Dual Cooling Setpoints: {e}")
#     # Update PEOPLE object
#     try:
#         people_object = idf.getobject('PEOPLE', 'LIVING ZONE People')
#         people_object.fieldvalues[5] = params['people_per_area']
#     except Exception as e:
#         print(f"Sample {i+1}: Error updating PEOPLE object: {e}")
#     # Update Infiltration objects
#     try:
#         infil_obj_living = idf.getobject('ZONEINFILTRATION:DESIGNFLOWRATE', 'LIVING ZONE Infil 1')
#         infil_obj_living.fieldvalues[5] = params['infil_flow_rate_living']
#     except Exception as e:
#         print(f"Sample {i+1}: Error updating Living Zone infiltration: {e}")
#     try:
#         infil_obj_garage = idf.getobject('ZONEINFILTRATION:DESIGNFLOWRATE', 'GARAGE ZONE Infil 1')
#         infil_obj_garage.fieldvalues[5] = params['infil_flow_rate_garage']
#     except Exception as e:
#         print(f"Sample {i+1}: Error updating Garage Zone infiltration: {e}")
#     try:
#         infil_obj_attic = idf.getobject('ZONEINFILTRATION:DESIGNFLOWRATE', 'ATTIC ZONE Infil 1')
#         infil_obj_attic.fieldvalues[5] = params['infil_flow_rate_attic']
#     except Exception as e:
#         print(f"Sample {i+1}: Error updating Attic Zone infiltration: {e}")
#     # Update equipment and lighting power
#     try:
#         equipment_object = idf.getobject('ELECTRICEQUIPMENT', 'LIVING ZONE ElecEq')
#         equipment_object.Design_Level = params['watts_equip']
#     except Exception as e:
#         print(f"Sample {i+1}: Error updating ELECTRICEQUIPMENT: {e}")
#     try:
#         lighting_object = idf.getobject('LIGHTS', 'LIVING ZONE Lights')
#         lighting_object.Lighting_Level = params['watts_lights']
#     except Exception as e:
#         print(f"Sample {i+1}: Error updating LIGHTS object: {e}")
#     # Update heating coil COP
#     try:
#         heating_coil = idf.getobject('COIL:HEATING:DX:MULTISPEED', 'Heat Pump DX Heating Coil 1')
#         heating_coil.Speed_1_Gross_Rated_Heating_COP = params['heating_COP']
#         heating_coil.Speed_2_Gross_Rated_Heating_COP = params['heating_COP']
#     except Exception as e:
#         print(f"Sample {i+1}: Error updating heating coil COP: {e}")
#     # Update fan parameters
#     try:
#         fan = idf.getobject('FAN:ONOFF', 'Supply Fan 1')
#         fan.fieldvalues[4] = str(round(params['pressure_rise'], 1))
#         fan.fieldvalues[3] = str(round(params['fan_efficiency'], 3))
#     except Exception as e:
#         print(f"Sample {i+1}: Error updating fan parameters: {e}")
#     # Update window glazing
#     try:
#         window_glazing = idf.getobject('WINDOWMATERIAL:GLAZING', 'CLEAR 3MM')
#         window_glazing.fieldvalues[4] = str(round(params['solar_transmittance'], 3))
#     except Exception as e:
#         print(f"Sample {i+1}: Error updating window solar transmittance: {e}")
#     # Update burner efficiency
#     try:
#         heater = idf.getobject('COIL:HEATING:FUEL', 'Supp Heating Coil 1')
#         heater.fieldvalues[4] = str(round(params['burner_eff'], 3))
#     except Exception as e:
#         print(f"Sample {i+1}: Error updating burner efficiency: {e}")
#     # Update ventilation airflow rate
#     try:
#         vent_obj = idf.getobject('ZONEVENTILATION:DESIGNFLOWRATE', 'LIVING ZONE Ventl 1')
#         vent_obj.fieldvalues[5] = str(round(params['vent_flow_rate'], 6))
#     except Exception as e:
#         print(f"Sample {i+1}: Error updating ventilation flow rate: {e}")
        
#     # Save the updated IDF file
#     output_file_path = output_idf_dir / f"randomized_{i+1}.idf"
#     idf.save(str(output_file_path))
#     return f"Sample {i+1}: Saved updated IDF file to {output_file_path}"

# if __name__ == '__main__':
#     # Specify how many files you want to generate.
#     num_files = 100000
#     valid_samples = generate_valid_samples(num_files, verbose=True)
    
#     # Create a list of (index, sample) tuples for processing.
#     sample_args = list(enumerate(valid_samples))
    
#     # Use ProcessPoolExecutor for parallel processing.
#     with ProcessPoolExecutor() as executor:
#         results = list(executor.map(process_sample, sample_args))
    
#     # Print results from each parallel task.
#     for r in results:
#         print(r)
    
#     # --- Record simulation parameters for each generated IDF file ---
#     # Generate the corresponding file names (these match the naming in process_sample)
#     file_names = [f"randomized_{i+1}.idf" for i in range(len(valid_samples))]
    
#     # Create a DataFrame from the valid_samples list
#     df_params = pd.DataFrame(valid_samples)
    
#     # Insert a column for the IDF file names so you can track which parameters correspond to which file
#     df_params.insert(0, 'IDF_file', file_names)
    
#     # Define the output CSV file path
#     csv_file_path = work_dir / "simulation_parameters.csv"
    
#     # Write the DataFrame to a CSV file (without the index)
#     df_params.to_csv(csv_file_path, index=False)
    
#     print(f"Simulation parameters saved to {csv_file_path}")

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
output_idf_dir = work_dir / "randomized_idfs"

# Set IDD and working dir
IDF.setiddname(idd_file_path)
os.chdir(work_dir)
output_idf_dir.mkdir(exist_ok=True)

# Uncomment below to generate/download weather files if needed
# weather_dir = work_dir / "weather_data"
# weather_dir.mkdir(exist_ok=True)
# os.chdir(weather_dir)
# import diyepw
# diyepw.create_amy_epw_files_for_years_and_wmos(
#     [2023], [725300], max_records_to_interpolate=6,
#     max_records_to_impute=48, max_missing_amy_rows=5,
#     allow_downloads=True, amy_epw_dir="."
# )
# os.chdir(work_dir)

# --- Latin Hypercube Sampling and Valid Samples Generation ---
def generate_valid_samples(num_files, verbose=True):
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

    sampler = qmc.LatinHypercube(d=14)
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
    i, params = args
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

if __name__ == '__main__':
    start = time.time()
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    # Rank 0 generates samples & cleans output dir
    if rank == 0:
        num_files = 100000
        samples = generate_valid_samples(num_files)
        # Clean output directory
        for item in output_idf_dir.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        args = list(enumerate(samples))
    else:
        args = None

    # Broadcast args and synchronize
    args = comm.bcast(args, root=0)
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
        csv_file = work_dir / "simulation_parameters.csv"
        df.to_csv(csv_file, index=False)
        end = time.time()
        print(f"Simulation parameters saved to {csv_file}")
        print(f"Total execution time: {end - start:.2f} seconds")