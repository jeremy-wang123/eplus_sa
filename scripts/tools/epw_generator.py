import os
import diyepw

# Get the current working directory and store it
scripts_dir = os.getcwd()

# Create the output directory if it does not exist
os.makedirs("weather_data", exist_ok=True)

# Changing to this directory
os.chdir("weather_data")

diyepw.create_amy_epw_files_for_years_and_wmos(
  [2022,2023,2024],
  [726440],
  max_records_to_interpolate=6,
  max_records_to_impute=48,
  max_missing_amy_rows=20,
  allow_downloads=True,
)

# Change back to the scripts directory
os.chdir(scripts_dir)