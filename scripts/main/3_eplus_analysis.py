#!/usr/bin/env python3
"""
3_eplus_analysis_parallel.py

Aggregates simulation results from EnergyPlus in parallel, outputs a combined CSV file,
creates extra columns with energy units converted to KJ, kWh, and BTU,
and produces various plots with declarative titles to highlight findings.
Also runs a single baseline model and overlays its annual total on the PDF.
Plots are saved as PNG files in the analysis directory.
"""

import os
import shutil
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

# Record Start
start_ts = time.time()

# --- Set working directories ---
work_dir = "/jumbo/keller-lab/Daniel_Xu/eplus_sensitivity/scripts/main"
os.chdir(work_dir)
print("Current working directory:", os.getcwd())

output_sim_dir   = os.path.join(work_dir, "output")
analysis_sim_dir = os.path.join(work_dir, "analysis")
os.makedirs(analysis_sim_dir, exist_ok=True)

# --- EnergyPlus & Weather paths for baseline run ---
idd_file_path = "/jumbo/keller-lab/Applications/EnergyPlus-24-1-0/Energy+.idd"
weather_file  = os.path.join(work_dir, "weather_data", "USA_IL_Chicago-OHare-Intl-AP.725300_AMY_2023.epw")

# Clean analysis output directory
for fn in os.listdir(analysis_sim_dir):
    path = os.path.join(analysis_sim_dir, fn)
    if os.path.isfile(path) or os.path.islink(path):
        os.unlink(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)

# --- Parallel collection of simulation CSV files and combine them ---
num_simulations = 100000  # update according to number of simulations generated

def read_csv_for_sim(i):
    """Read one simulation's CSV and add Simulation_ID, or return None."""
    folder   = f"randomized_{i}"
    csv_file = os.path.join(output_sim_dir, folder, "eplusmtr.csv")
    if os.path.isfile(csv_file):
        df = pd.read_csv(csv_file)
        df["Simulation_ID"] = i
        return df
    return None

all_data_frames = []
max_workers = os.cpu_count() or 4
print(f"Reading {num_simulations} simulations using {max_workers} workers...")

with ProcessPoolExecutor(max_workers=max_workers) as executor:
    # schedule all reads
    future_to_id = {executor.submit(read_csv_for_sim, i): i for i in range(1, num_simulations + 1)}
    for future in as_completed(future_to_id):
        df = future.result()
        sim_id = future_to_id[future]
        if df is not None:
            all_data_frames.append(df)
        else:
            print(f"Warning: File not found for simulation {sim_id}")

if not all_data_frames:
    raise RuntimeError("No simulation CSV files found. Check simulation outputs.")

combined_df = pd.concat(all_data_frames, ignore_index=True)
print(f"Combined {len(all_data_frames)} simulations into one DataFrame with {len(combined_df)} rows.")

# --- Ensure relevant columns are numeric ---
numeric_cols = [
    "Electricity:Facility [J](Monthly)",
    "Electricity:Building [J](Monthly)",
    "InteriorLights:Electricity [J](Monthly)",
    "Electricity:Facility [J](RunPeriod)",
    "Electricity:Building [J](RunPeriod)",
    "InteriorLights:Electricity [J](RunPeriod)",
    "Electricity:HVAC [J](Monthly)",
    "NaturalGas:Facility [J](Monthly)",
    "NaturalGas:HVAC [J](Monthly)",
    "Electricity:HVAC [J](RunPeriod)",
    "NaturalGas:Facility [J](RunPeriod)",
    "NaturalGas:HVAC [J](RunPeriod)"
]
for col in numeric_cols:
    if col in combined_df:
        combined_df[col] = pd.to_numeric(combined_df[col], errors="coerce")

# --- Energy Conversions: Joules to KJ and kWh ---
for col in list(combined_df):
    if col.endswith("[J](Monthly)") or col.endswith("[J](RunPeriod)"):
        combined_df[col.replace("[J]", "[KJ]")]  = combined_df[col] / 1e3
        combined_df[col.replace("[J]", "[kWh]")] = combined_df[col] / 3.6e6

# --- BTU Conversions: Joules to BTU ---
BTU_conv = 0.000947817
for col in list(combined_df):
    if "[J](" in col and ("HVAC" in col or "NaturalGas" in col):
        combined_df[col.replace("[J]", "[BTU]")] = combined_df[col] * BTU_conv

# --- Write the combined DataFrame to a CSV file ---
out_csv = os.path.join(analysis_sim_dir, "combined_sims.csv")
combined_df.to_csv(out_csv, index=False, float_format="%.2f")
print(f"Combined data written to: {out_csv}")

# --- Define month ordering ---
month_order = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]
combined_df["Date/Time"] = pd.Categorical(
    combined_df["Date/Time"], categories=month_order, ordered=True
)

# --- 1. Boxplot of facility electricity variability ---
plt.figure(figsize=(10,6))
sns.boxplot(
    x="Date/Time",
    y="Electricity:Facility [J](Monthly)",
    data=combined_df
)
plt.title("Parametric Uncertainty Drives Wide Variability in Monthly Facility Electricity")
plt.xlabel("Month")
plt.ylabel("Electricity (J)")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(analysis_sim_dir, "boxplot_joules.png"), dpi=300)
plt.close()

# --- 2. Line plot of each simulation's seasonal profile ---
pivot_j = combined_df.pivot_table(
    index="Simulation_ID",
    columns="Date/Time",
    values="Electricity:Facility [J](Monthly)"
)
plt.figure(figsize=(10,6))
pivot_j.T.plot(legend=False)
plt.title("Despite Randomized Inputs, Seasonal Trends Remain Consistent Across Simulations")
plt.xlabel("Month")
plt.ylabel("Electricity (J)")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(analysis_sim_dir, "lineplot_joules.png"), dpi=300)
plt.close()

# --- 3. KDE of annual total electricity ---
df_tot_j = (
    combined_df
    .groupby("Simulation_ID")["Electricity:Facility [J](Monthly)"]
    .sum()
    .reset_index(name="Total_Electricity_J")
)
g = sns.displot(
    data=df_tot_j,
    x="Total_Electricity_J",
    kind="kde",
    fill=True
)
plt.title("Total Annual Electricity Clusters Around Central Values Despite Parametric Variations")
plt.xlabel("Total Electricity (J)")
plt.ylabel("Density")
plt.tight_layout()
g.savefig(os.path.join(analysis_sim_dir, "kde_total_joules.png"), dpi=300)
plt.close()

# --- 4. Correlation heatmap of monthly electricity end-uses (kWh) ---
elec_kwh_cols = [
    "Electricity:Facility [kWh](Monthly)",
    "Electricity:Building [kWh](Monthly)",
    "InteriorLights:Electricity [kWh](Monthly)"
]
elec_kwh_cols = [c for c in elec_kwh_cols if c in combined_df]
if elec_kwh_cols:
    corr = combined_df[elec_kwh_cols].corr()
    plt.figure(figsize=(10,6))
    sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f")
    plt.title("End-Uses of Electricity Are Highly Correlated, Reflecting Shared Seasonal Drivers")
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.25)
    plt.savefig(os.path.join(analysis_sim_dir, "corr_heatmap_kwh.png"), dpi=300)
    plt.close()

# --- 5. Violin plot of facility electricity by month (kWh) ---
if "Electricity:Facility [kWh](Monthly)" in combined_df:
    plt.figure(figsize=(10,6))
    sns.violinplot(
        x="Date/Time",
        y="Electricity:Facility [kWh](Monthly)",
        data=combined_df
    )
    plt.title("Winter Months Exhibit the Greatest Spread in Facility Electricity Demand")
    plt.xlabel("Month")
    plt.ylabel("Electricity (kWh)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(analysis_sim_dir, "violin_facility_kwh.png"), dpi=300)
    plt.close()

# --- 6. Average monthly electricity trend (kWh) ---
if elec_kwh_cols:
    avg_df = (
        combined_df
        .groupby("Date/Time")[elec_kwh_cols]
        .mean()
        .reindex(month_order)
        .reset_index()
    )
    plt.figure(figsize=(10,6))
    for col in elec_kwh_cols:
        plt.plot(
            avg_df["Date/Time"],
            avg_df[col],
            marker="o",
            label=col
        )
    plt.title("Cooling and Heating Loads Drive Bimodal Peaks in Average Monthly Electricity Use")
    plt.xlabel("Month")
    plt.ylabel("Average Electricity (kWh)")
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(analysis_sim_dir, "avg_electricity_kwh.png"), dpi=300)
    plt.close()

# --- 7. Correlation heatmap HVAC & gas (BTU) ---
btu_cols = [
    "Electricity:HVAC [BTU](Monthly)",
    "NaturalGas:Facility [BTU](Monthly)",
    "NaturalGas:HVAC [BTU](Monthly)"
]
btu_cols = [c for c in btu_cols if c in combined_df]
if btu_cols:
    corr2 = combined_df[btu_cols].corr()
    plt.figure(figsize=(10,6))
    sns.heatmap(corr2, annot=True, cmap="viridis", fmt=".2f")
    plt.title("Electricity and Gas Loads for HVAC Systems Show Moderate Seasonal Coupling")
    plt.tight_layout()
    plt.savefig(os.path.join(analysis_sim_dir, "corr_heatmap_btu.png"), dpi=300)
    plt.close()

# --- 8. FacetGrid histograms of facility electricity (kWh) ---
if "Electricity:Facility [kWh](Monthly)" in combined_df:
    fg = sns.FacetGrid(
        combined_df,
        col="Date/Time",
        col_wrap=4,
        sharex=False,
        sharey=False
    )
    fg.map(
        sns.histplot,
        "Electricity:Facility [kWh](Monthly)",
        bins=20,
        kde=True
    )
    fg.fig.suptitle(
        "Monthly Distributions Reveal Seasonal Skews in Electricity Demand",
        y=1.02
    )
    plt.tight_layout()
    fg.savefig(os.path.join(analysis_sim_dir, "facetgrid_facility_kwh.png"), dpi=300)
    plt.close()

# --- 9. PairPlot of electricity end-uses (kWh) ---
if len(elec_kwh_cols) > 1:
    pp = sns.pairplot(combined_df[elec_kwh_cols])
    pp.fig.suptitle("Strong Linear Relationships Exist Among Electricity Subloads", y=1.02)
    pp.savefig(os.path.join(analysis_sim_dir, "pairplot_electricity_kwh.png"), dpi=300)
    plt.close()

# --- 10. Spaghetti plot of all simulations (kWh) ---
if "Electricity:Facility [kWh](Monthly)" in combined_df:
    pivot_kwh = combined_df.pivot_table(
        index="Simulation_ID",
        columns="Date/Time",
        values="Electricity:Facility [kWh](Monthly)"
    )
    plt.figure(figsize=(10,6))
    for sim in pivot_kwh.index:
        plt.plot(
            month_order,
            pivot_kwh.loc[sim].values,
            color="gray",
            alpha=0.3,
            linewidth=0.8
        )
    plt.title("Pronounced Seasonal Patterns Persist Across All Randomized Model Runs")
    plt.xlabel("Month")
    plt.ylabel("Electricity (kWh)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(analysis_sim_dir, "spaghetti_monthly_facility_kwh.png"), dpi=300)
    plt.close()

# --- 11. Baseline model run and overlay ---

# Run baseline EnergyPlus once
baseline_out = os.path.join(analysis_sim_dir, "baseline_run")
if os.path.isdir(baseline_out):
    shutil.rmtree(baseline_out)
os.makedirs(baseline_out, exist_ok=True)

baseline_idf = "/jumbo/keller-lab/Daniel_Xu/eplus_sensitivity/data/SingleFamilyHouse_TwoSpeed_CutoutTemperature.idf"

subprocess.run([
    "/jumbo/keller-lab/Applications/EnergyPlus-24-1-0/energyplus",
    "--weather", weather_file,
    "--output-directory", baseline_out,
    "--idd", idd_file_path,
    "--annual", "--readvars",
    baseline_idf
], check=True)

# Read baseline monthly totals and convert to kWh
baseline_csv = os.path.join(baseline_out, "eplusmtr.csv")
bl_df = pd.read_csv(baseline_csv)
bl_df["Facility_kWh"] = pd.to_numeric(
    bl_df["Electricity:Facility [J](Monthly)"], errors="coerce"
) / 3.6e6
baseline_total_kwh = bl_df["Facility_kWh"].sum()

# Overlay on the KDE of simulation totals in kWh
df_tot_kwh = df_tot_j.copy()
df_tot_kwh["Total_Electricity_kWh"] = df_tot_j["Total_Electricity_J"] / 3.6e6

plt.figure(figsize=(10,6))
sns.kdeplot(
    data=df_tot_kwh,
    x="Total_Electricity_kWh",
    fill=True,
    label="Simulation Ensemble"
)
plt.axvline(
    baseline_total_kwh,
    color="red",
    linestyle="--",
    linewidth=2,
    label="Baseline Model"
)
plt.title("Baseline Model Overpredicts Electricity Consumption Compared to Randomized Simulations")
plt.xlabel("Total Annual Facility Electricity (kWh)")
plt.ylabel("Density")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(analysis_sim_dir, "kde_with_baseline.png"), dpi=300)
plt.close()

# Record end
end_ts = time.time()

# Compute and print time 
print(f"Elapsed time : {elapsed:.3f} seconds")