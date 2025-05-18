EnergyPlus Sensitivity Analysis

A reproducible workflow for quantifying the impact of parametric uncertainty on annual energy use in a single-family house model using EnergyPlus. We use Latin Hypercube Sampling (LHS) to generate randomized model inputs, run ensembles of simulations in parallel with MPI, and then analyze convergence and uncertainty diagnostics in Python.

⸻

📂 Repository Layout

.
├── 1_eplus_sampling.py      # Generate randomized IDF files & parameter CSVs via LHS
├── 2_eplus_process.py       # Run EnergyPlus simulations in parallel (mpi4py)
├── 3_eplus_analysis.ipynb   # Jupyter notebook: load results, process, and plot diagnostics
├── data/
│   └── SingleFamilyHouse_TwoSpeed_CutoutTemperature.idf
├── weather_data/            # (optional) downloaded EPW files
├── randomized_idfs/         # output of script #1: per-seed IDF files
├── output/                  # simulation outputs: eplusmtr.csv under output/seed_<i>/
└── analysis/                # post-processing figures and CSVs


⸻

🛠 Requirements
	•	Python ≥ 3.8
	•	EnergyPlus ≥ 24.1
	•	MPI implementation (OpenMPI, MPICH, etc.)
	•	Shell with mpirun

Python packages

pip install eppy mpi4py numpy scipy pandas matplotlib seaborn geopandas

or with conda:

conda create -n eplus-env python=3.9 eppy mpi4py numpy scipy pandas matplotlib seaborn geopandas
conda activate eplus-env


⸻

🚀 Quickstart
	1.	Place IDD & skeleton IDF
Update paths in 1_eplus_sampling.py if needed.
	2.	Generate randomized IDFs
Creates 20 ensembles (seeds 1–20) of 20 000 LHS samples each:

mpirun -np 225 python 1_eplus_sampling.py

	•	Produces randomized_idfs/seed_<n>/randomized_<i>.idf
	•	Writes simulation_parameters_seed_<n>.csv

	3.	Run EnergyPlus simulations
For a single seed:

python 2_eplus_process.py --seed seed_3

Or all seeds in a loop:

for s in seed_{1..20}; do
  mpirun -np 225 python 2_eplus_process.py --seed "$s"
done

Results under output/seed_<n>/randomized_<i>/eplusmtr.csv.

	4.	Analyze & plot

jupyter lab 3_eplus_analysis.ipynb

or export HTML:

jupyter nbconvert --to html 3_eplus_analysis.ipynb



⸻

🔄 Workflow Overview
	1.	Sampling
	•	Draw 14-dimensional LHS with SciPy
	•	Transform to normal distributions around nominal means (± 5 %)
	•	Enforce physical bounds (e.g. solar transmittance ∈ [0,1], COP > 0.7)
	2.	Parallel Simulation
	•	Distribute IDFs to MPI ranks
	•	Run EnergyPlus (--annual --readvars)
	•	Collect eplusmtr.csv per run
	3.	Post-processing & Diagnostics
	•	Convert J → kWh and BTU
	•	Seasonal histograms with baseline overlay + box-whisker
	•	Convergence of mean annual electricity vs. sample size
	•	Criterion: 1.5×IQR whiskers within ± 5 % of median at 10⁵ samples

⸻

📈 Key Outputs
	•	analysis/combined_sims.csv
All seeds & simulations combined.
	•	analysis/facetgrid_with_baseline.png
Seasonal distribution + baseline line + box-whisker.
	•	analysis/convergence_boxplot_all_seeds.png
Convergence boxplots of mean annual use vs. LHS sample size.
	•	analysis/kde_with_baseline.png
PDF of total annual electricity with baseline comparison.

⸻

🎯 Reproducibility & Best Practices
	•	Lock dependencies in environment.yml or requirements.txt.
	•	Parameterize paths at top of each script.
	•	Tag EnergyPlus versions in git.
	•	Document convergence criteria in code & README.
	•	Automate figure generation via Makefile or CI.

⸻

🤝 Contributing
	1.	Fork the repo
	2.	Create feature branch
	3.	Submit PR with tests & updated docs
	4.	Ensure CI passes & figures regenerate

⸻

📜 License

This project is licensed under the MIT License. See LICENSE for details.