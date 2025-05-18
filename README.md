# EnergyPlus Sensitivity Analysis

A reproducible workflow for quantifying the impact of parametric uncertainty on annual energy use in a single-family house model using EnergyPlus.  We use Latin Hypercube Sampling (LHS) to generate randomized model inputs, run ensembles of simulations in parallel with MPI, and then analyze convergence and uncertainty diagnostics in Python.

---

## 📂 Repository Layout

.
├── 1_eplus_sampling.py      # Generate randomized IDF files & parameter CSVs via LHS
├── 2_eplus_process.py       # Run EnergyPlus simulations in parallel (mpi4py)
├── 3_eplus_analysis.ipynb   # Jupyter notebook: load results, process, and plot diagnostics
├── data/
│   └── SingleFamilyHouse_TwoSpeed_CutoutTemperature.idf
├── weather_data/            # (optional) downloaded EPW files
├── randomized_idfs/         # output of script #1: per-seed IDF files
├── output/                  # simulation outputs: eplusmtr.csv under output/seed_/
└── analysis/                # post-processing figures and CSVs

---

## 🛠 Requirements

- Python ≥ 3.8  
- [EnergyPlus](https://energyplus.net/) ≥ 24.1  
- MPI implementation (OpenMPI, MPICH, etc.)  
- A POSIX-compatible shell for `mpirun`  

### Python packages

```bash
pip install eppy mpi4py numpy scipy pandas matplotlib seaborn geopandas

or with conda:

conda create -n eplus-env python=3.9 eppy mpi4py numpy scipy pandas matplotlib seaborn geopandas
conda activate eplus-env


⸻

🚀 Quickstart
	1.	Download or place your IDD & skeleton IDF
Modify paths in 1_eplus_sampling.py if needed.
	2.	Generate randomized IDFs
This will produce 20 ensembles (seeds 1–20) of 20 000 LHS samples each:

mpirun -np 225 python 1_eplus_sampling.py

	•	Creates randomized_idfs/seed_<1–20>/randomized_<i>.idf
	•	Writes simulation_parameters_seed_<n>.csv in the project root

	3.	Run EnergyPlus simulations
To process a single seed (e.g. seed_3):

python 2_eplus_process.py --seed seed_3

Or to loop over all seeds via MPI:

for s in seed_{1..20}; do
  mpirun -np 225 python 2_eplus_process.py --seed $s
done

Outputs live under output/seed_<n>/randomized_<i>/eplusmtr.csv.

	4.	Analyze & plot results
Launch the notebook:

jupyter lab 3_eplus_analysis.ipynb

or render to HTML/PDF:

jupyter nbconvert --to html 3_eplus_analysis.ipynb



⸻

🔄 Workflow Overview
	1.	Sampling
	•	Use SciPy’s qmc.LatinHypercube to draw 14-dimensional LHS
	•	Transform to normal distributions around nominal means (± 5 %)
	•	Enforce physical bounds (e.g. solar transmittance ∈ [0,1], COP > 0.7)
	2.	Parallel Simulation
	•	Distribute randomized IDFs to MPI ranks
	•	Each rank runs EnergyPlus with --annual --readvars
	•	Gather eplusmtr.csv logs per simulation
	3.	Post-processing & Diagnostics
	•	Convert raw J → kWh and BTU
	•	Plot monthly histograms with baseline overlay
	•	FacetGrid of seasonal distributions + box-and-whisker summaries
	•	Global convergence of mean annual electricity across sample sizes
	•	Convergence criterion: 1.5×IQR whiskers within ± 5 % of median at 10⁵ samples

⸻

📈 Key Outputs
	•	analysis/combined_sims.csv
Aggregated simulation logs across all seeds & runs.
	•	analysis/facetgrid_with_baseline.png
Seasonal histogram + box-whisker + neglect-uncertainty line.
	•	analysis/convergence_boxplot_all_seeds.png
Boxplots of mean annual use vs. LHS sample size (seeds 1–20).
	•	analysis/kde_with_baseline.png
PDF of total annual electricity with baseline vs. uncertainty.

⸻

🎯 Reproducibility & Best Practices
	•	Lock dependencies in environment.yml or requirements.txt.
	•	Parameterize paths at top of each script for portability.
	•	Use version control tags to snapshot EnergyPlus versions.
	•	Document convergence criteria in code comments & README.
	•	Automate figure generation via Makefile or CI pipelines.

⸻

🤝 Contributing
	1.	Fork the repo
	2.	Create a feature branch
	3.	Submit a pull request with tests and updated docs
	4.	Ensure CI passes and figures regenerate without errors

⸻

📜 License

This work is released under the MIT License. See LICENSE for details.

