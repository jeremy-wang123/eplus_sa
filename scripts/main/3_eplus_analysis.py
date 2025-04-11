#!/usr/bin/env python3
"""
analysis.py

Aggregates simulation results from EnergyPlus, outputs a combined CSV file,
and produces plots for analysis including box plots, line plots, and KDE plots.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# --- Set working directories ---
work_dir = "/jumbo/keller-lab/Daniel_Xu/eplus_sensitivity/scripts/main"
os.chdir(work_dir)
print("Current working directory:", os.getcwd())

output_sim_dir = os.path.join(work_dir, "output")
analysis_sim_dir = os.path.join(work_dir, "analysis")
os.makedirs(analysis_sim_dir, exist_ok=True)

# Clean analysis output directory
for filename in os.listdir(analysis_sim_dir):
    file_path = os.path.join(analysis_sim_dir, filename)
    if os.path.isfile(file_path) or os.path.islink(file_path):
        os.unlink(file_path)
    elif os.path.isdir(file_path):
        import shutil
        shutil.rmtree(file_path)

# --- Collect simulation CSV files and combine them ---
all_data_frames = []
num_simulations = 100  # update according to the number of simulations generated

for i in range(1, num_simulations+1):
    folder_name = f"randomized_{i}"
    csv_file = os.path.join(output_sim_dir, folder_name, "eplusmtr.csv")
    if os.path.isfile(csv_file):
        temp_df = pd.read_csv(csv_file)
        temp_df["Simulation_ID"] = i
        all_data_frames.append(temp_df)
    else:
        print(f"File not found: {csv_file}")

if not all_data_frames:
    raise ValueError("No simulation CSV files were found. Please check your simulation outputs.")

combined_df = pd.concat(all_data_frames, ignore_index=True)

# Write combined DataFrame to a CSV file
output_csv_path = os.path.join(analysis_sim_dir, 'combined_sims.csv')
combined_df["Electricity:Facility [J](Monthly)"] = pd.to_numeric(
    combined_df["Electricity:Facility [J](Monthly)"],
    errors="coerce"
)
combined_df.to_csv(output_csv_path, index=False)
print(f"Combined data written to: {output_csv_path}")

# --- Plot 1: Box Plot - Distribution of Facility Electricity by Month ---
plt.figure(figsize=(10, 6))
sns.boxplot(x='Date/Time', y='Electricity:Facility [J](Monthly)', data=combined_df)
plt.title('Distribution of Facility Electricity by Month (All Simulations)')
plt.xlabel('Month')
plt.ylabel('Facility Electricity (J)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# --- Plot 2: Line Plot - Each Simulation's Monthly Electricity Use ---
month_order = ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"]
combined_df["Date/Time"] = pd.Categorical(
    combined_df["Date/Time"],
    categories=month_order,
    ordered=True
)
pivoted = combined_df.pivot_table(
    index='Simulation_ID',
    columns='Date/Time',
    values='Electricity:Facility [J](Monthly)'
)
plt.figure(figsize=(10, 6))
pivoted.T.plot(legend=False)
plt.title('Electricity:Facility by Month for All Simulations')
plt.xlabel('Month')
plt.ylabel('Facility Electricity (J)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# --- Plot 3: KDE Plot of Total Electricity Usage ---
df_summed = combined_df.groupby("Simulation_ID")["Electricity:Facility [J](Monthly)"].sum().reset_index(name="Total_Electricity")
sns.displot(data=df_summed, x="Total_Electricity", kind="kde", fill=True)
plt.title("Probability Distribution of Total Electricity Usage (All Simulations)")
plt.xlabel("Total Electricity (J)")
plt.ylabel("Density")
plt.show()