#!/usr/bin/env python3
"""
plot_skewt.py
Reads a CM1 input_sounding format file and plots a Skew-T Log-P diagram using MetPy.
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from metpy.plots import SkewT
from metpy.units import units

def plot_sounding(sounding_file, output_img):
    print(f"Reading sounding from: {sounding_file}")
    if not os.path.exists(sounding_file):
        print(f"Error: Sounding file '{sounding_file}' not found.")
        sys.exit(1)

    # Read the sounding data
    with open(sounding_file, 'r') as f:
        header = f.readline().strip().split()
        sfc_pres = float(header[0])
        sfc_theta = float(header[1])
        sfc_qv = float(header[2])
        
        data = []
        for line in f:
            if line.strip():
                data.append(list(map(float, line.strip().split())))

    df = pd.DataFrame(data, columns=['Z', 'theta', 'qv', 'U', 'V'])

    # Hydrostatic pressure integration
    g = 9.80665
    Rd = 287.04
    Cp = 1004.0
    kappa = Rd / Cp
    P0 = 1000.0

    df['qv_kg'] = df['qv'] / 1000.0
    df['theta_v'] = df['theta'] * (1.0 + 0.61 * df['qv_kg'])

    sfc_qv_kg = sfc_qv / 1000.0
    sfc_theta_v = sfc_theta * (1.0 + 0.61 * sfc_qv_kg)

    pi = np.zeros(len(df))
    current_pi = (sfc_pres / P0) ** kappa
    last_z = 0.0
    last_tv = sfc_theta_v

    for i in range(len(df)):
        dz = df['Z'].values[i] - last_z
        tv_mean = 0.5 * (df['theta_v'].values[i] + last_tv)
        dpi = - (g * dz) / (Cp * tv_mean)
        current_pi += dpi
        pi[i] = current_pi
        last_z = df['Z'].values[i]
        last_tv = df['theta_v'].values[i]

    df['P'] = P0 * (pi ** (1.0 / kappa))
    df['T_C'] = (df['theta'] * ((df['P'] / 1000.0) ** kappa)) - 273.15

    # Dewpoint temperature calculation
    epsilon = 0.622
    df['e'] = df['P'] * df['qv_kg'] / (epsilon + df['qv_kg'])
    y = np.log(df['e'] / 6.112)
    df['Td_C'] = 243.5 * y / (17.67 - y)

    print("Plotting Skew-T...")
    fig = plt.figure(figsize=(10, 10))
    skew = SkewT(fig, rotation=45)

    p_units = df['P'].values * units.hPa
    t_units = df['T_C'].values * units.degC
    td_units = df['Td_C'].values * units.degC

    # Plot profiles
    skew.plot(p_units, t_units, 'r', linewidth=2, label='Temperature (°C)')
    skew.plot(p_units, td_units, 'g', linewidth=2, label='Dewpoint (°C)')

    # Wind barbs (plot every 8th level to avoid overlap)
    decim = 8
    skew.plot_barbs(
        p_units[::decim], 
        df['U'].values[::decim] * units('m/s'), 
        df['V'].values[::decim] * units('m/s'),
        length=6,
        linewidth=0.8
    )

    # Background reference lines
    skew.plot_dry_adiabats(color='red', alpha=0.15, linewidth=0.5)
    skew.plot_moist_adiabats(color='blue', alpha=0.15, linewidth=0.5)
    skew.plot_mixing_lines(color='green', alpha=0.15, linewidth=0.5)

    # Style plot
    skew.ax.set_ylim(1050, 100)
    skew.ax.set_xlim(-30, 40)
    skew.ax.set_xlabel('Temperature (°C)')
    skew.ax.set_ylabel('Pressure (hPa)')
    plt.title(f'CM1 Input Sounding - {os.path.basename(sounding_file)}', fontsize=12, pad=15)
    plt.legend(loc='upper left')

    plt.savefig(output_img, bbox_inches='tight', dpi=150)
    print(f"Plot saved successfully to: {output_img}")

def main():
    parser = argparse.ArgumentParser(description="Plot Skew-T Log-P diagram from a CM1 sounding file.")
    parser.add_argument("sounding_file", nargs="?", default="input_sounding_data_local", help="Path to CM1 sounding file")
    parser.add_argument("-o", "--output", default="skewt.png", help="Path to output image file")
    args = parser.parse_args()
    
    plot_sounding(args.sounding_file, args.output)

if __name__ == "__main__":
    main()
