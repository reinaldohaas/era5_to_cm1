#!/usr/bin/env python3
"""
era5_to_sounding.py
Downloads ERA5 reanalysis data from Copernicus Climate Data Store (CDS)
and processes it into a CM1 input_sounding file.
"""

import os
import sys
import argparse
import numpy as np
import xarray as xr
import cdsapi

# Constants
G = 9.80665  # Standard gravity m/s^2
R_D = 287.04  # Gas constant for dry air J/(kg K)
C_P = 1004.0  # Specific heat of dry air at constant pressure J/(kg K)
KAPPA = R_D / C_P  # 0.285896

def check_cdsapirc():
    """Verify that the .cdsapirc credential file exists."""
    home_dir = os.path.expanduser("~")
    cdsapirc_path = os.path.join(home_dir, ".cdsapirc")
    if not os.path.exists(cdsapirc_path):
        print("=" * 60)
        print("ERROR: Copernicus CDS API configuration file (.cdsapirc) not found.")
        print(f"Please create a file at: {cdsapirc_path}")
        print("with the following content (2 lines):")
        print("-" * 60)
        print("url: https://cds.climate.copernicus.eu/api")
        print("key: YOUR_PERSONAL_ACCESS_TOKEN")
        print("-" * 60)
        print("To get your Personal Access Token:")
        print("1. Register/Login at https://cds.climate.copernicus.eu/")
        print("2. Go to your user profile page to copy the token.")
        print("=" * 60)
        sys.exit(1)

def get_variable(dataset, possible_names):
    """Find and return a variable from an xarray dataset using a list of possible names."""
    for name in possible_names:
        if name in dataset:
            return dataset[name]
    raise KeyError(f"Could not find any of the variables {possible_names} in the dataset. Available: {list(dataset.keys())}")

def download_era5(lat, lon, date_str, time_str, out_pl_file, out_sl_file):
    """Downloads pressure level and single level data for the specified box."""
    c = cdsapi.Client()
    
    # Define bounding box (0.5 degree square around target point)
    # format: [North, West, South, East]
    area = [
        lat + 0.25,
        lon - 0.25,
        lat - 0.25,
        lon + 0.25
    ]
    
    year, month, day = date_str.split('-')
    
    # Request pressure levels
    print(f"Requesting pressure levels for coordinates ({lat}, {lon}) on {date_str} at {time_str}...")
    c.retrieve(
        'reanalysis-era5-pressure-levels',
        {
            'product_type': 'reanalysis',
            'format': 'netcdf',
            'variable': [
                'geopotential', 'temperature', 'specific_humidity',
                'u_component_of_wind', 'v_component_of_wind'
            ],
            'pressure_level': [
                '1', '2', '3', '5', '7', '10', '20', '30', '50', '70',
                '100', '125', '150', '175', '200', '225', '250', '300',
                '350', '400', '450', '500', '550', '600', '650', '700',
                '750', '775', '800', '825', '850', '875', '900', '925',
                '950', '975', '1000'
            ],
            'year': year,
            'month': month,
            'day': day,
            'time': time_str,
            'area': area,
        },
        out_pl_file
    )
    print(f"Pressure levels downloaded to {out_pl_file}")
    
    # Request single levels (surface)
    print(f"Requesting single levels for coordinates ({lat}, {lon}) on {date_str} at {time_str}...")
    c.retrieve(
        'reanalysis-era5-single-levels',
        {
            'product_type': 'reanalysis',
            'format': 'netcdf',
            'variable': [
                '2m_temperature', '2m_dewpoint_temperature', 'surface_pressure',
                'geopotential', '10m_u_component_of_wind', '10m_v_component_of_wind'
            ],
            'year': year,
            'month': month,
            'day': day,
            'time': time_str,
            'area': area,
        },
        out_sl_file
    )
    print(f"Single levels downloaded to {out_sl_file}")

def process_sounding(pl_file, sl_file, lat, lon, output_sounding):
    """Processes downloaded netCDF files and creates CM1 sounding file."""
    print("Processing datasets...")
    
    # Open datasets
    ds_pl = xr.open_dataset(pl_file)
    ds_sl = xr.open_dataset(sl_file)
    
    # Extract nearest point
    pt_pl = ds_pl.sel(latitude=lat, longitude=lon, method='nearest').squeeze()
    pt_sl = ds_sl.sel(latitude=lat, longitude=lon, method='nearest').squeeze()
    
    # 1. Surface parameters
    sp_pa = float(get_variable(pt_sl, ['sp', 'surface_pressure']).values)
    t2m_k = float(get_variable(pt_sl, ['t2m', '2m_temperature']).values)
    d2m_k = float(get_variable(pt_sl, ['d2m', '2m_dewpoint_temperature']).values)
    sfc_geopot = float(get_variable(pt_sl, ['z', 'geopotential']).values)
    u10 = float(get_variable(pt_sl, ['u10', '10m_u_component_of_wind']).values)
    v10 = float(get_variable(pt_sl, ['v10', '10m_v_component_of_wind']).values)
    
    sfc_pres_mb = sp_pa / 100.0
    sfc_theta = t2m_k * ((1000.0 / sfc_pres_mb) ** KAPPA)
    
    # Calculate surface mixing ratio from 2m dew point
    # Tetens equation for actual vapor pressure e (in hPa)
    td_c = d2m_k - 273.15
    e_sfc = 6.112 * np.exp((17.67 * td_c) / (td_c + 243.5))
    w_sfc = (0.6220 * e_sfc) / (sfc_pres_mb - e_sfc)
    sfc_qv = w_sfc * 1000.0  # to g/kg
    
    sfc_height_asl = sfc_geopot / G
    print(f"Surface elevation: {sfc_height_asl:.1f} m ASL")
    print(f"Surface pressure: {sfc_pres_mb:.2f} mb")
    print(f"Surface potential temp: {sfc_theta:.2f} K")
    print(f"Surface mixing ratio: {sfc_qv:.2f} g/kg")
    
    # 2. Pressure level parameters
    t_pl = get_variable(pt_pl, ['t', 'temperature'])
    q_pl = get_variable(pt_pl, ['q', 'specific_humidity'])
    u_pl = get_variable(pt_pl, ['u', 'u_component_of_wind'])
    v_pl = get_variable(pt_pl, ['v', 'v_component_of_wind'])
    z_pl = get_variable(pt_pl, ['z', 'geopotential'])
    
    levels = pt_pl.level.values  # in hPa
    
    sounding_data = []
    
    # Add surface line as the first level (height AGL = 0)
    sounding_data.append((0.0, sfc_theta, sfc_qv, u10, v10))
    
    # Loop through pressure levels
    for i, p_lev in enumerate(levels):
        geopot = float(z_pl[i].values)
        z_asl = geopot / G
        z_agl = z_asl - sfc_height_asl
        
        # Skip levels below ground
        if z_agl <= 0:
            continue
            
        t_k = float(t_pl[i].values)
        q_kg_kg = float(q_pl[i].values)
        u_val = float(u_pl[i].values)
        v_val = float(v_pl[i].values)
        
        theta_val = t_k * ((1000.0 / p_lev) ** KAPPA)
        
        # specific humidity (q) to mixing ratio (w) in g/kg
        w_val = q_kg_kg / (1.0 - q_kg_kg)
        qv_val = w_val * 1000.0
        
        sounding_data.append((z_agl, theta_val, qv_val, u_val, v_val))
        
    # Sort levels by height AGL ascending (since pressure levels list goes 1 to 1000 hPa)
    sounding_data.sort(key=lambda x: x[0])
    
    # Write to input_sounding file
    with open(output_sounding, 'w') as f:
        # Header line: surface_pressure(mb) surface_potential_temp(K) surface_mixing_ratio(g/kg)
        f.write(f"{sfc_pres_mb:12.6f} {sfc_theta:12.6f} {sfc_qv:12.6f}\n")
        
        # Data lines: height_agl(m) theta(K) qv(g/kg) u(m/s) v(m/s)
        for data in sounding_data:
            f.write(f"{data[0]:12.6f} {data[1]:12.6f} {data[2]:12.6f} {data[3]:12.6f} {data[4]:12.6f}\n")
            
    print(f"Sounding file successfully written to: {output_sounding}")
    print(f"Generated {len(sounding_data)} levels in the sounding profile.")
    
    # Close files
    ds_pl.close()
    ds_sl.close()

def main():
    parser = argparse.ArgumentParser(description="Generate CM1 input_sounding file from ERA5 reanalysis.")
    parser.add_argument("--lat", type=float, default=-27.102765, help="Latitude of target location")
    parser.add_argument("--lon", type=float, default=-49.624542, help="Longitude of target location")
    parser.add_argument("--date", type=str, default="2020-12-17", help="Date in YYYY-MM-DD format")
    parser.add_argument("--time", type=str, default="03:00", help="Time in HH:MM format (UTC)")
    parser.add_argument("--output", type=str, default="input_sounding", help="Output file path")
    parser.add_argument("--no-download", action="store_true", help="Skip downloading, use existing files")
    
    args = parser.parse_args()
    
    pl_file = "era5_pressure_levels.nc"
    sl_file = "era5_single_levels.nc"
    
    if not args.no_download:
        check_cdsapirc()
        download_era5(args.lat, args.lon, args.date, args.time, pl_file, sl_file)
        
    if os.path.exists(pl_file) and os.path.exists(sl_file):
        process_sounding(pl_file, sl_file, args.lat, args.lon, args.output)
    else:
        print(f"Error: Missing required netCDF files. Run without --no-download to fetch them.")
        sys.exit(1)

if __name__ == "__main__":
    main()
