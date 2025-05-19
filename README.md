# Improving Uncertainty Characterization in Home Energy Projections

This repository supports the analysis and reproducibility of the undergraduate honors thesis titled **"Improving Uncertainty Characterization in Home Energy Projections"** by Daniel Xu at Dartmouth College. The study leverages Latin Hypercube Sampling and EnergyPlus simulations to examine how uncertainty in input parameters affects residential energy demand projections.

## Overview

Energy modeling plays a vital role in informing building decarbonization strategies. However, simplified assumptions and reduced-form prototypes can obscure how variation in key parameters—such as thermostat setpoints, infiltration rates, and HVAC efficiencies—affects projected energy use. This study develops an open-source, parallelized simulation workflow using EnergyPlus to quantify these uncertainties and assess potential prototype-induced biases.

## Repository Structure

```
├── 1_eplus_sampling.py       # Generates randomized IDFs using Latin Hypercube Sampling
├── 2_eplus_process.py        # Runs parallelized EnergyPlus simulations for a given seed
├── 3_eplus_analysis.ipynb    # Aggregates and visualizes simulation results
├── data/                     # Contains input skeleton IDFs and weather files
├── output/                   # Stores simulation results for each randomized configuration
├── analysis/                 # Contains analysis outputs and figures
```

## Getting Started

### Prerequisites

Set up a Python environment (e.g., via Conda):

```bash
conda env create -f environment.yml
conda activate eplus
```

Install [EnergyPlus v24.1.0](https://github.com/NREL/EnergyPlus/releases/tag/v24.1.0) and ensure it is callable from your system environment.

### Parallelization and HPC Notes

This project is MPI-compatible and designed to leverage high-performance computing (HPC) for scalable simulation. It was developed and run on Dartmouth College’s Thayer Babylon HPC clusters (225 cores), which provides multi-node access and job queuing via MPI.
	•	The simulation scripts are parallelized with MPI for Python (mpi4py).
	•	At least 64 CPU cores are strongly recommended to ensure timely convergence of simulation batches.
	•	On HPC systems, use mpirun (https://mpi4py.readthedocs.io/en/stable/) to launch parallel jobs.

### Required Python Packages

- `pandas`
- `numpy`
- `scipy`
- `matplotlib`
- `seaborn`
- `eppy`
- `mpi4py`
- `jupyter`
- `diyepw`

### 1. Sampling: Generate Randomized IDFs

```bash
mpirun -np <num_cores> python 1_eplus_sampling.py
```

- Uses Latin Hypercube Sampling on 14 key parameters.
- Outputs IDFs to structured directories for each sample and seed.

### 2. Simulation: Run EnergyPlus Simulations

Run for each seed in parallel (e.g., for `seed_1`):

```bash
mpirun -np <num_cores> python 2_eplus_process.py --seed seed_1
```

- Requires a hostfile or resource manager for HPC clusters.
- Outputs stored in `output/seed_1/randomized_<id>/`.

### 3. Analysis: Aggregate and Visualize Outputs

```bash
jupyter notebook 3_eplus_analysis.ipynb
```

- Aggregates results across simulations.
- Converts units to kWh/BTU and produces plots.
- Assesses uncertainty, sensitivity, and prototype bias.

## Reproducibility Commitments

This repository follows best practices for reproducible computational research:

- **Open-source:** All scripts are publicly available.
- **Modular scripts:** Each stage of the workflow (sampling, simulation, analysis) is separate and clearly documented.
- **Version control:** All scripts and inputs are tracked via Git.
- **Automation-ready:** Supports large-scale parallel execution and batch processing.
- **Data integrity:** Handles missing/empty output files gracefully.
- **Transparency:** Parameters, assumptions, and statistical distributions are clearly described and configurable.

## Citation

If you use this codebase, please cite the thesis:

```
Xu, D. (2025). Improving Uncertainty Characterization in Home Energy Projections. Honors Thesis, Program in Quantitative Social Science, Dartmouth College.
```

## License

This project is licensed under the MIT License. See `LICENSE` for details.

## Acknowledgments

This work was supported by:
- Professor Klaus Keller (Primary Advisor)
- Adam Pollack and Hunter Snyder (Advisors)
- Dartmouth Undergraduate Advising & Research (UGAR)
- Arthur L. Irving Institute for Energy & Society

For more details, see the accompanying thesis PDF and results in the `/analysis` directory.








