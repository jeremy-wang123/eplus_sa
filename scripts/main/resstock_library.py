# This is a library of all functions that are called when generating samples for resstock priors

# package imports
import numpy as np
import pandas as pd
import os
from scipy import stats
from scipy.stats import gamma, norm, truncnorm
from scipy.interpolate import interp1d

# configs 
resstock_dir = "/jumbo/keller-lab/Jeremy_Wang/resstock"
housing_characteristics_dir = os.path.join(resstock_dir, "project_national", "housing_characteristics")

# function for extracting and cleaning TSV files
def extract_and_clean (filename):
    df = pd.read_csv(os.path.join(housing_characteristics_dir, filename), sep='\t')

    # removing missing columns
    dep_cols = [c for c in df.columns if c.startswith("Dependency=")]
    filtered = df[
        (~df[dep_cols].eq("Not Available").any(axis=1)) &
        (df[dep_cols].notna().all(axis=1))
    ]
    return filtered

# extracting heating probabilities
def extract_heating_probs():
    # reading heating_setpoint file
    heating_setpoint = extract_and_clean("Heating Setpoint.tsv")

    # skeleton IDF constraints
    climate_zone = "5A" # chicago 
    building_type = "Single-Family Detached" 
    HVAC_heating_type = "Ducted Heat Pump"

    # filter by constraints
    mask = (
        (heating_setpoint['Dependency=ASHRAE IECC Climate Zone 2004'] == climate_zone) &
        (heating_setpoint['Dependency=Geometry Building Type RECS'] == building_type) &
        (heating_setpoint['Dependency=HVAC Heating Type'] == HVAC_heating_type) # &
        # (heating_setpoint['Dependency=HVAC Has Zonal Electric Heating'] == 'No')
        )

    heating_filtered = heating_setpoint[mask]

    # delete misinputted dataset
    heating_filtered = heating_filtered[heating_filtered['Dependency=Tenure'] != 'Not Available']

    # Get option columns
    opt_cols = [c for c in heating_filtered.columns if c.startswith('Option=')]

    # Weight by source_weight
    heating_weights = heating_filtered['source_weight'].values
    heating_weights = heating_weights / heating_weights.sum()

    # Weighted average across tenure types
    heating_weighted_probs = pd.Series(
        np.average(heating_filtered[opt_cols].values, axis=0, weights=heating_weights),
        index=opt_cols
    )

    ### convert setpoints from fahrenheit to celsius
    # Convert option names from F to C
    def f_to_c(f):
        return (f - 32) * 5/9

    # Extract numeric F values from option names
    heating_f_values = np.array([float(c.replace('Option=', '').replace('F', '')) 
                        for c in opt_cols])

    # Convert to Celsius
    heating_c_values = f_to_c(heating_f_values)

    heating_prior = pd.DataFrame()
    heating_prior["Temp"] = heating_c_values
    heating_prior["Prob"] = heating_weighted_probs.values

    return heating_prior

# extracting cooling probabilities
def extract_cooling_probs():
    # reading cooling_setpoint file
    cooling_setpoint = extract_and_clean("Cooling Setpoint.tsv")

    # skeleton IDF constraints
    climate_zone = "5A" # chicago 
    building_type = "Single-Family Detached" 
    HVAC_cooling_type = "Ducted Heat Pump"

    # filter by constraints
    mask = (
        (cooling_setpoint['Dependency=ASHRAE IECC Climate Zone 2004'] == climate_zone) &
        (cooling_setpoint['Dependency=Geometry Building Type RECS'] == building_type) &
        (cooling_setpoint['Dependency=HVAC Cooling Type'] == HVAC_cooling_type)
        )
    cooling_filtered = cooling_setpoint[mask]
    cooling_filtered = cooling_filtered[cooling_filtered['Dependency=Tenure'] != 'Not Available']
    cooling_filtered = cooling_filtered.drop(columns=['Option=Void'], errors='ignore')

    # Get option columns
    opt_cols = [c for c in cooling_filtered.columns if c.startswith('Option=')]

    # Weight by source_weight
    cooling_weights = cooling_filtered['source_weight'].values
    cooling_weights = cooling_weights / cooling_weights.sum()
    # Weighted average across tenure types
    cooling_weighted_probs = pd.Series(
        np.average(cooling_filtered[opt_cols].values, axis=0, weights=cooling_weights),
        index=opt_cols
    )

    ### convert setpoints from fahrenheit to celsius
    # Convert option names from F to C
    def f_to_c(f):
        return (f - 32) * 5/9

    # Extract numeric F values from option names
    cooling_f_values = np.array([float(c.replace('Option=', '').replace('F', '')) 
                        for c in opt_cols])

    # Convert to Celsius
    cooling_c_values = f_to_c(cooling_f_values)

    cooling_prior = pd.DataFrame()
    cooling_prior["Temp"] = cooling_c_values
    cooling_prior["Prob"] = cooling_weighted_probs.values

    return cooling_prior

# extracting gap information to return mean and std params 
def extract_gap_info(seed):
    sd_frac = 0.05
    # extract key params used for inverse CDF transformation onto the gamma fit
    cooling_shape, cooling_loc_g, cooling_scale_g = fit_data(extract_cooling_probs(), seed=seed)
    heating_shape, heating_loc_g, heating_scale_g = fit_data(extract_heating_probs(), seed=seed)

    # extracting "mean" and "std" from the gamma distribution
    heating_mean = heating_shape * heating_scale_g + heating_loc_g
    cooling_mean = cooling_shape * cooling_scale_g + cooling_loc_g

    # multiply by the standard fraction 
    gap_mean = cooling_mean - heating_mean
    gap_std = gap_mean * sd_frac

    return gap_mean, gap_std

# extracting people priors
def extract_people_prior():
    # reading file
    people_filtered = extract_and_clean("Occupants.tsv")

    # IDF constraints
    building_type = "Single-Family Detached" 
    census_division = "East North Central"
    bedrooms = "3" # assume 3 bedrooms because IDF specifies that number of occupants

    # Note: Not controlling for income, metro status, or tenure status

    # mask
    mask = (
        (people_filtered['Dependency=Geometry Building Type RECS'] == building_type) &
        (people_filtered['Dependency=Census Division'] == census_division) & 
        (people_filtered['Dependency=Bedrooms'] == bedrooms)
    )

    people_filtered = people_filtered[mask]

    # Get option columns
    opt_cols = [c for c in people_filtered.columns if c.startswith('Option=')]

    # Weight by source_weight
    people_weights = people_filtered['source_weight'].values
    people_weights = people_weights / people_weights.sum()

    # Weighted average across dependency types
    people_weighted_probs = pd.Series(
        np.average(people_filtered[opt_cols].values, axis=0, weights=people_weights),
        index=opt_cols
    )

    people_values = np.array([
        float(c.replace("Option=", "").replace("+", ""))  # remove 'Option=' and '+'
        for c in opt_cols
    ])

    people_prior = pd.DataFrame()
    people_prior["People"] = people_values
    people_prior["Prob"] = people_weighted_probs.values

    return people_prior

# extracting infiltration rate probabilities
def extract_infil_prior():
    infil_filtered = extract_and_clean("Infiltration.tsv")

    # IDF Constraints
    climate_zone = "5A" # Chicago  
    floor_area = ["1500-1999","2000-2499"] # consider floor areas ranging from 1500 - 2499 ft^2

    mask = (
        (infil_filtered['Dependency=ASHRAE IECC Climate Zone 2004'] == climate_zone) &
        ((infil_filtered['Dependency=Geometry Floor Area'] == floor_area[0]) | (infil_filtered['Dependency=Geometry Floor Area'] == floor_area[1]))
    )

    infil_filtered = infil_filtered[mask]

    opt_cols = [c for c in infil_filtered.columns if c.startswith("Option=")]

    # weight by sampling probability
    infil_probs = pd.Series(
        np.average(
            infil_filtered[opt_cols].values,
            axis=0,
            weights=infil_filtered["sampling_probability"]
        ),
        index=opt_cols
    )

    # unit conversations 
    CC = 22.2 # conversion coefficient
    FA = 186 # Floor Area m^2
    H = 3 # Height  m 

    ACH50_values = np.array([float(c.replace('Option=', '').replace('ACH50', '')) 
                        for c in opt_cols])

    Q_values = (ACH50_values * (FA * H))/(3600*CC) # converting into m^3/s

    infil_prior = pd.DataFrame()
    infil_prior["Q"] = Q_values
    infil_prior["Prob"] = infil_probs.values
    
    return infil_prior

# extract lighting probabilities
def extract_lighting_probs():
    lighting = extract_and_clean("Lighting.tsv")

    # constraints
    state = "IL"
    building_type = "Single-Family Detached"

    mask = (
        (lighting['Dependency=State'] == state) & 
        (lighting['Dependency=Geometry Building Type RECS'] == building_type)
    )

    lighting = lighting[mask]

    # Get option columns
    opt_cols = [c for c in lighting.columns if c.startswith('Option=')]

    # Weight by source_weight
    lighting_weights = lighting['source_weight'].values
    lighting_weights = lighting_weights / lighting_weights.sum()

    # Weighted average across dependency types
    lighting_weighted_probs = pd.Series(
        np.average(lighting[opt_cols].values, axis=0, weights=lighting_weights),
        index=opt_cols
    )
    # calculating kwh/yr for interior lighting (assume this encapsulates all lighting energy use)
    # Use the same equation for interior as attic and garage

    # constants
    ffa = 2000 # floor area in ft^2
    l_hw = 0.8*(ffa*0.542+334) # interior plug in lighting, kwh/yr
    er_cfl = 0.27 # efficiency rating of CFL
    er_led = 0.3 # efficiency rating of LED
    er_lf = 0.17 # efficiency rating of linear fluorescent
    f_lf = 0 # fraction of linear fluorescent lighting, which we will assume is 0 for simplicity

    # calculate kwh/yr for each lighting type
    def calculate_lighting_kwh(f_inc, f_cfl, f_led):
        SAF = 1.1*f_inc**4 - 1.9*f_inc**3 + 1.5*f_inc**2 - 0.7*f_inc + 1 # smart replacement algorithm factor

        lighting_kwh_yr = l_hw * (((f_inc+0.34)+(f_cfl-0.21)*er_cfl + f_led*er_led + (f_lf-0.13)*er_lf)*SAF*0.9 + 0.1)
        # hours of usage per day
        hours_per_day = 2.7 
        lighting_watts = lighting_kwh_yr * 1000 / (365*hours_per_day) # convert to watts

        return lighting_watts

    lighting_inc = calculate_lighting_kwh(f_inc = 1, f_cfl = 0, f_led = 0)
    lighting_cfl = calculate_lighting_kwh(f_inc = 0, f_cfl = 1, f_led = 0)
    lighting_led = calculate_lighting_kwh(f_inc = 0, f_cfl = 0, f_led = 1)

    lighting_lookup = {
        "Option=100% Incandescent": lighting_inc,
        "Option=100% CFL": lighting_cfl,
        "Option=100% LED": lighting_led
    }

    lighting_weighted_probs = lighting_weighted_probs.reset_index()
    lighting_weighted_probs.columns = ["lighting_option", "probability"]

    lighting_weighted_probs["watts"] = (
        lighting_weighted_probs["lighting_option"]
        .map(lighting_lookup)
    )

    return lighting_weighted_probs 

# extracting solar transmittance probabilities
def extract_solar_probs():
    solar_transmittance = extract_and_clean("Windows.tsv")

    # constraints
    climate_zone = "5A"
    building_type = "Single-Family Detached"

    mask = (
        (solar_transmittance['Dependency=ASHRAE IECC Climate Zone 2004'] == climate_zone) &
        (solar_transmittance['Dependency=Geometry Building Type RECS'] == building_type)  # & 
        # (burner_filtered['Dependency=HVAC Has Shared System'] == "Heating and Cooling")
    )

    solar_transmittance = solar_transmittance[mask]
    solar_transmittance = solar_transmittance.drop(columns=['Option=Void'], errors='ignore')

    # Get option columns
    opt_cols = [c for c in solar_transmittance.columns if c.startswith('Option=')]

    # Weight by source_weight
    solar_weights = solar_transmittance['source_weight'].values
    solar_weights = solar_weights / solar_weights.sum()

    # Weighted average across dependency types
    solar_weighted_probs = pd.Series(
        np.average(solar_transmittance[opt_cols].values, axis=0, weights=solar_weights),
        index=opt_cols
    )

    # inputting lookup table
    windows_df = pd.DataFrame({
        "window_option": solar_weighted_probs.index,

        "SHGC": [
            0.67,
            0.60,
            0.56,
            0.50,
            0.52,
            0.75,
            0.68,
            0.64,
            0.58,
            0.31
        ],

        "window_type": [
            "double",
            "double",
            "double",
            "double",
            "double",
            "single",
            "single",
            "single",
            "single",
            "triple"  
        ]
    })

    # Conversions from SHGC to solar transmittance
    def shgc_to_solar_transmittance(shgc, window_type):
        # Single-pane / high-U equation
        if window_type == "single":

            if shgc < 0.7206:
                ts = (
                    0.939998 * shgc**2
                    + 0.20332 * shgc
                )
            else:
                ts = (
                    1.30415 * shgc
                    - 0.30515
                )

        # Double-pane or better equation
        else:
            if shgc <= 0.15:
                ts = 0.41040 * shgc
            else:
                ts = (
                    0.085775 * shgc**2
                    + 0.963954 * shgc
                    - 0.084958
                )
        return ts

    windows_df["solar_transmittance"] = windows_df.apply(
        lambda row: shgc_to_solar_transmittance(
            row["SHGC"],
            row["window_type"]
        ),
        axis=1
    )

    # Add solar transmittance lookup table
    solar_lookup = dict(
        zip(
            windows_df["window_option"],
            windows_df["solar_transmittance"]
        )
    )

    # Convert weighted probabilities Series into DataFrame
    solar_weighted_probs = solar_weighted_probs.reset_index()
    solar_weighted_probs.columns = [
        "window_option",
        "probability"
    ]

    # Add solar transmittance column
    solar_weighted_probs["solar_transmittance"] = (
        solar_weighted_probs["window_option"]
        .map(solar_lookup)
    )

    return solar_weighted_probs

### Gamma and mixed normal distribution fits
# fit data from weighted probabilites to a gamma distribution
def fit_data(prior, seed):
    # load data
    x = prior.iloc[:, 0].values
    w = prior.iloc[:, 1].values
    # normalize weights
    w = w / w.sum()

    # create seeded RNG
    rng = np.random.default_rng(seed)

    # Gamma distribution fit
    samples = rng.choice(x, size=10000, p=w)
    ### Gamma distribution fit
    # samples = np.random.choice(x, size=10000, p=w)
    shape, loc_g, scale_g = gamma.fit(samples, floc=0)

    return shape, loc_g, scale_g

# creating mixed normal distributions for each lighting option, then summing them together according to their probabilities to get a final distribution, which we can then sample from using the inverse CDF method
def fit_mixed_normal(probs):
    sd_frac = 0.05

    weights = probs["probability"].values
    means = probs["watts"].values

    weights = weights / weights.sum()

    stds = sd_frac * means
    x_grid = np.linspace(0, 2500, 10000)

    cdf = np.zeros_like(x_grid)

    for w, mu, sd in zip(weights, means, stds):
        cdf += w * norm.cdf(x_grid, loc=mu, scale=sd)
    inv_cdf_lighting = interp1d(
        cdf,
        x_grid,
        bounds_error=False,
        fill_value=(x_grid[0], x_grid[-1])
    )

    return inv_cdf_lighting

### inverse CDF Transformation functions
# inverse CDF transformation for Gamma function
# probs is the weighted probability dataframe, seed is the seed for gamma fit
def gamma_inverse_cdf(uniform_sample, seed, probs):
    shape, loc, scale = fit_data(probs, seed=seed)
    transformed_samples = gamma.ppf(uniform_sample, a=shape, loc=loc, scale=scale)
    return transformed_samples

# inverse CDF for normal distribution
# means and parameter_std dictionary, param is parameter name
def normal_inverse_cdf(uniform_sample, means, parameter_std, param):
    mean = means[param]
    std = parameter_std[param]
    transformed_samples = norm.ppf(uniform_sample, loc=mean, scale=std)
    return transformed_samples

# inverse CDF Transformations for truncated normal (only used for gap)
def truncated_normal_inverse_cdf(uniform_sample, mean, std, lower_bound, upper_bound):
    # convert physical bounds to standard-normal bounds
    a = (lower_bound - mean) / std
    b = (upper_bound - mean) / std

    transformed_samples = truncnorm.ppf(
        uniform_sample,
        a,
        b,
        loc=mean,
        scale=std
    )
    return transformed_samples

# inverse CDF transformation for mixed normal (only used for lighting)
def mixed_normal_inverse_cdf(uniform_sample, probs):
    inv_cdf_lighting = fit_mixed_normal(probs)
    transformed_samples = inv_cdf_lighting(uniform_sample)
    return transformed_samples

