### This program will be used for conducting Sobol sensitivity analysis

### Steps for conducting analysis ###
# 1) Define parameters being considered, and parametric uncertainty associated with them
# 2) Use Sobol sequence to sample the parameter space, generating a matrix of p(n+2) x p
# 3) Convert values back to parameter values
# 4) Write each row of parameter values into an idf
# 5) Run the idfs to determine the output results
# 6) Calculate sobol first order and total order indices based on these results

# Importing relevant libraries
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

