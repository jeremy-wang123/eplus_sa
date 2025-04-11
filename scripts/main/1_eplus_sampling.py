#!/usr/bin/env python3
"""
generate_randomized_idfs.py

Generates randomized EnergyPlus IDF files by sampling parameters via Latin Hypercube Sampling.
It also downloads (or creates) weather files required for the simulations.
"""

# --- Import necessary libraries ---
from eppy import modeleditor
from eppy.modeleditor import IDF
import pandas as pd
import numpy as np
import os
import shutil
from datetime import datetime, timedelta
import requests
import subprocess
import esoreader
import diyepw
from scipy.stats import norm, qmc

# --- Set global paths and configurations ---
# EnergyPlus IDD file path (update as needed)
idd_file_path = "/jumbo/keller-lab/Applications/EnergyPlus-24-1-0/Energy+.idd"
IDF.setiddname(idd_file_path)

# Skeleton IDF file provided by EnergyPlus (update this path if needed)
skeleton_idf_path = "../../data/SingleFamilyHouse_TwoSpeed_CutoutTemperature.idf"

# Set desired working directory for the scripts and outputs
work_dir = "/jumbo/keller-lab/Daniel_Xu/eplus_sensitivity/scripts/main"
os.chdir(work_dir)
print("Current working directory:", os.getcwd())

# --- Create and populate weather data directory ---
weather_dir = os.path.join(work_dir, "weather_data")
os.makedirs(weather_dir, exist_ok=True)
os.chdir(weather_dir)

# Create EPW weather file(s) using the diyepw package
diyepw.create_amy_epw_files_for_years_and_wmos(
    [2023],
    [725300],
    max_records_to_interpolate=6,
    max_records_to_impute=48,
    max_missing_amy_rows=5,
    allow_downloads=True,
    amy_epw_dir='./'
)

# Return to the main working directory
os.chdir(work_dir)

# --- Prepare directory for randomized IDF files ---
output_idf_dir = os.path.join(work_dir, "randomized_idfs")
os.makedirs(output_idf_dir, exist_ok=True)

# Clean up any existing files in the output directory
for filename in os.listdir(output_idf_dir):
    file_path = os.path.join(output_idf_dir, filename)
    if os.path.isfile(file_path) or os.path.islink(file_path):
        os.unlink(file_path)
    elif os.path.isdir(file_path):
        shutil.rmtree(file_path)

# --- Define the function that updates the IDF based on Latin Hypercube Sampling ---
def update_building_parameters_lhs(skeleton_idf_path, idd_file_path, output_idf_dir, num_files=10, verbose=True):
    def update_schedule_field(schedule, field_index, new_setpoint, verbose=True):
        try:
            float(schedule.fieldvalues[field_index])
            schedule.fieldvalues[field_index] = str(round(new_setpoint, 2))
            if verbose:
                print(f"Updated schedule field index {field_index} to {round(new_setpoint, 2)}°C")
        except (ValueError, TypeError):
            if verbose:
                print(f"Field at index {field_index} is not numeric; skipping update.")

    # Set the EnergyPlus IDD file path
    IDF.setiddname(idd_file_path)
    if verbose:
        print(f"IDD set from: {idd_file_path}")

    # Define means and standard deviations
    mean_heating_sp = 22.0          # °C
    mean_cooling_sp = 26.6          # °C
    sd_frac = 0.05
    sd_heating_sp = sd_frac * mean_heating_sp 
    sd_cooling_sp = sd_frac * mean_cooling_sp
    gap_mean = mean_cooling_sp - mean_heating_sp       
    gap_sd = np.sqrt(sd_heating_sp**2 + sd_cooling_sp**2)  # ~1.73°C

    mean_people_per_area = 3.0      
    mean_infil_flow_rate = 0.01     
    mean_watts_equip = 500          
    mean_watts_lights = 1000        
    mean_heating_COP = 4.0          
    mean_fan_efficiency = 0.7       
    mean_pressure_rise = 400.0      
    mean_solar_transmittance = 0.837  
    mean_burner_eff = 0.8           
    mean_vent_flow_rate = 0.131944  

    sd_people_per_area = sd_frac * mean_people_per_area
    sd_infil_flow_rate = sd_frac * mean_infil_flow_rate
    sd_mean_watts_equip = sd_frac * mean_watts_equip
    sd_mean_watts_lights = sd_frac * mean_watts_lights
    sd_heating_COP = sd_frac * mean_heating_COP
    sd_fan_efficiency = sd_frac * mean_fan_efficiency
    sd_pressure_rise = sd_frac * mean_pressure_rise
    sd_solar_transmittance = sd_frac * mean_solar_transmittance
    sd_burner_eff = sd_frac  
    sd_vent_flow_rate = sd_frac * mean_vent_flow_rate

    # Set up Latin Hypercube Sampling for 14 parameters
    total_dims = 14
    sampler = qmc.LatinHypercube(d=total_dims)
    n_points = num_files * 2  # oversample
    sample_matrix = sampler.random(n=n_points)

    valid_samples = []
    for row in sample_matrix:
        new_heating_sp = norm.ppf(row[0], loc=mean_heating_sp, scale=sd_heating_sp)
        new_gap = norm.ppf(row[1], loc=gap_mean, scale=gap_sd)
        if new_gap < 3:
            new_gap = 3.0
        new_cooling_sp = new_heating_sp + new_gap

        new_people = norm.ppf(row[2], loc=mean_people_per_area, scale=sd_people_per_area)
        new_infil_living = norm.ppf(row[3], loc=mean_infil_flow_rate, scale=sd_infil_flow_rate)
        new_infil_garage = norm.ppf(row[4], loc=mean_infil_flow_rate, scale=sd_infil_flow_rate)
        new_infil_attic = norm.ppf(row[5], loc=mean_infil_flow_rate, scale=sd_infil_flow_rate)
        new_watts_equip = norm.ppf(row[6], loc=mean_watts_equip, scale=sd_mean_watts_equip)
        new_watts_lights = norm.ppf(row[7], loc=mean_watts_lights, scale=sd_mean_watts_lights)
        new_heating_COP = norm.ppf(row[8], loc=mean_heating_COP, scale=sd_heating_COP)
        new_fan_efficiency = norm.ppf(row[9], loc=mean_fan_efficiency, scale=sd_fan_efficiency)
        new_pressure_rise = norm.ppf(row[10], loc=mean_pressure_rise, scale=sd_pressure_rise)
        new_solar_transmittance = norm.ppf(row[11], loc=mean_solar_transmittance, scale=sd_solar_transmittance)
        new_solar_transmittance = np.clip(new_solar_transmittance, 0, 1)
        new_burner_eff = norm.ppf(row[12], loc=mean_burner_eff, scale=sd_burner_eff)
        new_burner_eff = np.clip(new_burner_eff, 0.7, 0.9)
        new_vent_flow_rate = norm.ppf(row[13], loc=mean_vent_flow_rate, scale=sd_vent_flow_rate)

        if new_heating_sp <= 0 or new_cooling_sp <= 0 or new_people < 0 or \
           new_infil_living < 0 or new_infil_garage < 0 or new_infil_attic < 0 or \
           new_watts_equip < 0 or new_watts_lights < 0 or new_heating_COP <= 0 or \
           new_fan_efficiency <= 0 or new_pressure_rise <= 0 or new_vent_flow_rate < 0:
            continue

        valid_samples.append({
            'heating_setpoint': new_heating_sp,
            'cooling_setpoint': new_cooling_sp,
            'people_per_area': new_people,
            'infil_flow_rate_living': new_infil_living,
            'infil_flow_rate_garage': new_infil_garage,
            'infil_flow_rate_attic': new_infil_attic,
            'watts_equip': new_watts_equip,
            'watts_lights': new_watts_lights,
            'heating_COP': new_heating_COP,
            'fan_efficiency': new_fan_efficiency,
            'pressure_rise': new_pressure_rise,
            'solar_transmittance': new_solar_transmittance,
            'burner_eff': new_burner_eff,
            'vent_flow_rate': new_vent_flow_rate
        })
        if len(valid_samples) >= num_files:
            break

    if len(valid_samples) < num_files:
        print("Warning: Could not generate the desired number of valid samples.")

    if verbose:
        print(f"Generated {len(valid_samples)} valid Latin hypercube sample(s).")

    # Update and save IDF files
    for i, params in enumerate(valid_samples):
        if verbose:
            print(f"\n--- Iteration {i+1}/{len(valid_samples)} ---")
        idf = IDF(skeleton_idf_path)
        if verbose:
            print(f"Loaded skeleton IDF file: {skeleton_idf_path}")

        try:
            heating_schedule = idf.getobject('SCHEDULE:COMPACT', 'Dual Heating Setpoints')
            update_schedule_field(heating_schedule, 6, params['heating_setpoint'], verbose)
        except Exception as e:
            if verbose:
                print("Error updating Dual Heating Setpoints:", e)
        try:
            cooling_schedule = idf.getobject('SCHEDULE:COMPACT', 'Dual Cooling Setpoints')
            update_schedule_field(cooling_schedule, 6, params['cooling_setpoint'], verbose)
        except Exception as e:
            if verbose:
                print("Error updating Dual Cooling Setpoints:", e)

        try:
            people_object = idf.getobject('PEOPLE', 'LIVING ZONE People')
            people_object.fieldvalues[5] = params['people_per_area']
            if verbose:
                print(f"Updated PEOPLE object with value: {params['people_per_area']:.6f}")
        except Exception as e:
            if verbose:
                print("Error updating PEOPLE object:", e)

        try:
            infil_obj_living = idf.getobject('ZONEINFILTRATION:DESIGNFLOWRATE', 'LIVING ZONE Infil 1')
            infil_obj_living.fieldvalues[5] = params['infil_flow_rate_living']
            if verbose:
                print(f"Updated Living Zone infiltration to: {params['infil_flow_rate_living']:.6e} m³/s")
        except Exception as e:
            if verbose:
                print("Error updating Living Zone infiltration:", e)
        try:
            infil_obj_garage = idf.getobject('ZONEINFILTRATION:DESIGNFLOWRATE', 'GARAGE ZONE Infil 1')
            infil_obj_garage.fieldvalues[5] = params['infil_flow_rate_garage']
            if verbose:
                print(f"Updated Garage Zone infiltration to: {params['infil_flow_rate_garage']:.6e} m³/s")
        except Exception as e:
            if verbose:
                print("Error updating Garage Zone infiltration:", e)
        try:
            infil_obj_attic = idf.getobject('ZONEINFILTRATION:DESIGNFLOWRATE', 'ATTIC ZONE Infil 1')
            infil_obj_attic.fieldvalues[5] = params['infil_flow_rate_attic']
            if verbose:
                print(f"Updated Attic Zone infiltration to: {params['infil_flow_rate_attic']:.6e} m³/s")
        except Exception as e:
            if verbose:
                print("Error updating Attic Zone infiltration:", e)

        try:
            equipment_object = idf.getobject('ELECTRICEQUIPMENT', 'LIVING ZONE ElecEq')
            equipment_object.Design_Level = params['watts_equip']
            if verbose:
                print(f"Updated equipment power to {params['watts_equip']:.1f} W")
        except Exception as e:
            if verbose:
                print("Error updating ELECTRICEQUIPMENT object:", e)
        try:
            lighting_object = idf.getobject('LIGHTS', 'LIVING ZONE Lights')
            lighting_object.Lighting_Level = params['watts_lights']
            if verbose:
                print(f"Updated lighting power to {params['watts_lights']:.1f} W")
        except Exception as e:
            if verbose:
                print("Error updating LIGHTS object:", e)

        try:
            heating_coil = idf.getobject('COIL:HEATING:DX:MULTISPEED', 'Heat Pump DX Heating Coil 1')
            heating_coil.Speed_1_Gross_Rated_Heating_COP = params['heating_COP']
            heating_coil.Speed_2_Gross_Rated_Heating_COP = params['heating_COP']
            if verbose:
                print(f"Updated heating coil COP to: {params['heating_COP']:.3f}")
        except Exception as e:
            if verbose:
                print("Error updating heating coil COP:", e)

        try:
            fan = idf.getobject('FAN:ONOFF', 'Supply Fan 1')
            fan.fieldvalues[4] = str(round(params['pressure_rise'], 1))
            fan.fieldvalues[3] = str(round(params['fan_efficiency'], 3))
            if verbose:
                print(f"Updated fan to pressure rise: {params['pressure_rise']:.1f} Pa and efficiency: {params['fan_efficiency']:.3f}")
        except Exception as e:
            if verbose:
                print("Error updating fan parameters:", e)

        try:
            window_glazing = idf.getobject('WINDOWMATERIAL:GLAZING', 'CLEAR 3MM')
            window_glazing.fieldvalues[4] = str(round(params['solar_transmittance'], 3))
            if verbose:
                print(f"Updated window glazing solar transmittance to: {params['solar_transmittance']:.3f}")
        except Exception as e:
            if verbose:
                print("Error updating window solar transmittance:", e)

        try:
            heater = idf.getobject('COIL:HEATING:FUEL', 'Supp Heating Coil 1')
            heater.fieldvalues[4] = str(round(params['burner_eff'], 3))
            if verbose:
                print(f"Updated burner efficiency to: {params['burner_eff']:.3f}")
        except Exception as e:
            if verbose:
                print("Error updating burner efficiency:", e)

        try:
            vent_obj = idf.getobject('ZONEVENTILATION:DESIGNFLOWRATE', 'LIVING ZONE Ventl 1')
            vent_obj.fieldvalues[5] = str(round(params['vent_flow_rate'], 6))
            if verbose:
                print(f"Updated ventilation flow rate to: {params['vent_flow_rate']:.6f} m³/s")
        except Exception as e:
            if verbose:
                print("Error updating ventilation flow rate:", e)

        output_file_path = os.path.join(output_idf_dir, f"randomized_{i+1}.idf")
        idf.save(output_file_path)
        if verbose:
            print(f"Saved updated IDF file to: {output_file_path}")

# --- Generate randomized IDF files ---
if __name__ == '__main__':
    # For example, generate 100 randomized files.
    update_building_parameters_lhs(skeleton_idf_path, idd_file_path, output_idf_dir, num_files=100, verbose=True)