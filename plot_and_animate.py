#!/usr/bin/env python3
import sys
import os
import argparse
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

def main():
    parser = argparse.ArgumentParser(description="Plot and animate CM1 test cases.")
    parser.add_argument('--case', choices=['straka', 'wet_microburst'], required=True,
                        help="Case to plot: 'straka' or 'wet_microburst'")
    parser.add_argument('--file', default='cm1out.nc',
                        help="NetCDF output file path (default: cm1out.nc)")
    args = parser.parse_args()
    
    nc_path = args.file
    if not os.path.exists(nc_path):
        # Check if there are multiple netCDF files (e.g., cm1out_000001.nc etc)
        # and open them as a dataset
        import glob
        files = sorted(glob.glob('cm1out_*.nc'))
        if files:
            print(f"Opening multiple files: {files}")
            ds = xr.open_mfdataset(files, combine='nested', concat_dim='time')
        else:
            print(f"Error: NetCDF file(s) not found.")
            sys.exit(1)
    else:
        print(f"Opening single NetCDF file: {nc_path}")
        ds = xr.open_dataset(nc_path)
        
    print("Dataset loaded. Variables available:")
    print(list(ds.data_vars))
    
    # 2D Cartesian slice (ny=1, so we select y=0)
    if 'y' in ds.dims:
        ds = ds.isel(y=0)
    elif 'yh' in ds.dims:
        ds = ds.isel(yh=0)
        
    # Detect coordinate names and convert to km
    x_coord = 'xh' if 'xh' in ds.coords else ('x' if 'x' in ds.coords else None)
    z_coord = 'zh' if 'zh' in ds.coords else ('z' if 'z' in ds.coords else None)
    
    if not x_coord or not z_coord:
        print("Error: Could not identify X or Z coordinates in dataset.")
        sys.exit(1)
        
    # Get arrays
    x = ds[x_coord].values
    z = ds[z_coord].values
    
    # Check units (if in meters, convert to km for plotting)
    x_factor = 1.0
    z_factor = 1.0
    x_unit = ds[x_coord].attrs.get('units', 'km')
    z_unit = ds[z_coord].attrs.get('units', 'km')
    
    if x_unit == 'm' or np.max(x) > 1000.0:
        x_factor = 0.001
        x_unit = 'km'
    if z_unit == 'm' or np.max(z) > 1000.0:
        z_factor = 0.001
        z_unit = 'km'
        
    x_km = x * x_factor
    z_km = z * z_factor
    
    # Create grid for vector plotting (subsample to avoid clutter)
    X_grid, Z_grid = np.meshgrid(x_km, z_km)
    skip_x = max(1, len(x_km) // 20)
    skip_z = max(1, len(z_km) // 15)
    
    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
    
    # We will animate frame by frame
    times = ds['time'].values
    num_frames = len(times)
    
    print(f"Generating animation with {num_frames} frames...")
    
    def update(frame_idx):
        ax.clear()
        t_sec = times[frame_idx]
        t_min = t_sec / 60.0
        
        # Get variables at this time step
        u = ds['u'].isel(time=frame_idx).values
        # Note: w is on flux grid in Z (nz+1), we interpolate to half grid (nz) for vector plotting
        w_flux = ds['w'].isel(time=frame_idx).values
        w = 0.5 * (w_flux[:-1, :] + w_flux[1:, :])
        
        # Destagger U if it's on flux grid (nx+1)
        if u.shape[1] > len(x):
            u = 0.5 * (u[:, :-1] + u[:, 1:])
            
        if args.case == 'straka':
            thpert = ds['thpert'].isel(time=frame_idx).values
            
            # Plot perturbation potential temperature (cold pool)
            im = ax.pcolormesh(x_km, z_km, thpert, cmap='RdBu_r', vmin=-15.0, vmax=2.0, shading='auto')
            if frame_idx == 0:
                fig.colorbar(im, ax=ax, label=r'$\theta$ Perturbation (K)')
                
            # Plot wind vectors
            ax.quiver(X_grid[::skip_z, ::skip_x], Z_grid[::skip_z, ::skip_x], 
                      u[::skip_z, ::skip_x], w[::skip_z, ::skip_x], 
                      color='black', alpha=0.6, scale=150)
            
            ax.set_title(f"Straka Dry Density Current | Time = {t_min:.1f} min", fontsize=14, fontweight='bold')
            ax.set_ylabel(f"Height ({z_unit})")
            ax.set_xlabel(f"Distance ({x_unit})")
            ax.set_xlim(np.min(x_km), np.max(x_km))
            ax.set_ylim(0.0, 4.0)  # Density current stays near surface (domain is 6.4km, plot lower 4km)
            
        elif args.case == 'wet_microburst':
            # Check if dbz is present, otherwise use rain mixing ratio qr
            if 'dbz' in ds.data_vars:
                var_name = 'dbz'
                cmap = 'turbo'
                vmin, vmax = 0.0, 70.0
                label = 'Radar Reflectivity (dBZ)'
                data = ds['dbz'].isel(time=frame_idx).values
            else:
                var_name = 'qr'
                cmap = 'YlGnBu'
                vmin, vmax = 0.0, 0.005 # 5 g/kg
                label = 'Rain Water Mixing Ratio (kg/kg)'
                data = ds['qr'].isel(time=frame_idx).values
                
            thpert = ds['thpert'].isel(time=frame_idx).values
            
            # Plot rain shaft
            im = ax.pcolormesh(x_km, z_km, data, cmap=cmap, vmin=vmin, vmax=vmax, shading='auto')
            if frame_idx == 0:
                fig.colorbar(im, ax=ax, label=label)
                
            # Overplot cold pool boundaries as contours
            contours = ax.contour(x_km, z_km, thpert, levels=[-6.0, -4.0, -2.0, -0.5], 
                                  colors='white', linewidths=1.5, linestyles='dashed')
            if frame_idx == 0 and len(contours.collections) > 0:
                ax.clabel(contours, inline=True, fmt='%1.1f K', fontsize=9, colors='white')
                
            # Plot wind vectors
            ax.quiver(X_grid[::skip_z, ::skip_x], Z_grid[::skip_z, ::skip_x], 
                      u[::skip_z, ::skip_x], w[::skip_z, ::skip_x], 
                      color='black', alpha=0.5, scale=200)
            
            ax.set_title(f"Convective Wet Downburst (Microburst) | Time = {t_min:.1f} min", fontsize=14, fontweight='bold')
            ax.set_ylabel(f"Height ({z_unit})")
            ax.set_xlabel(f"Distance ({x_unit})")
            ax.set_xlim(np.min(x_km), np.max(x_km))
            ax.set_ylim(0.0, 8.0)  # Plot lower 8km of the 12km domain
            
        fig.tight_layout()

    ani = animation.FuncAnimation(fig, update, frames=num_frames, interval=250)
    gif_name = f"{args.case}_animation.gif"
    ani.save(gif_name, writer='pillow')
    plt.close()
    
    print(f"Animation successfully generated and saved to: {gif_name}")
    print("To view in Jupyter, execute:")
    print("from IPython.display import Image, display")
    print(f"display(Image(filename='{gif_name}'))")

if __name__ == '__main__':
    main()
