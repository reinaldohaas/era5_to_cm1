#!/usr/bin/env python3
import sys
import os
import argparse

def parse_namelist(file_path):
    sections = {}
    current_section = None
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        sys.exit(1)
        
    with open(file_path, 'r') as f:
        lines = f.readlines()
        
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('&'):
            current_section = stripped[1:].split()[0]
            sections[current_section] = []
        elif stripped == '/':
            if current_section:
                sections[current_section].append('/')
                current_section = None
        else:
            if current_section:
                sections[current_section].append(line)
                
    return sections

def update_key(section_lines, key, new_value):
    # Search for key = ...
    for idx, line in enumerate(section_lines):
        stripped = line.strip()
        # Find key followed by = or spaces and =
        if '=' in stripped:
            parts = stripped.split('=')
            current_key = parts[0].strip()
            if current_key.lower() == key.lower():
                # Replace value
                # Check indentation
                indent = len(line) - len(line.lstrip())
                section_lines[idx] = " " * indent + f"{key} = {new_value},\n"
                return True
    
    # If not found, insert before the closing '/'
    for idx, line in enumerate(section_lines):
        if line.strip() == '/':
            section_lines.insert(idx, f"  {key} = {new_value},\n")
            return True
            
    return False

def write_namelist(sections, file_path):
    with open(file_path, 'w') as f:
        # Write section by section
        for sec_name, lines in sections.items():
            f.write(f" &{sec_name}\n")
            for line in lines:
                if line.strip() == '/':
                    f.write(" /\n\n")
                else:
                    f.write(line)

def main():
    parser = argparse.ArgumentParser(description="Setup CM1 test cases.")
    parser.add_argument('--case', choices=['straka', 'wet_microburst'], required=True,
                        help="Case to configure: 'straka' (dry density current) or 'wet_microburst' (convective wet downburst)")
    args = parser.parse_args()
    
    # Use the default namelist.input in CM1/run/config_files/namelist.input as a base if it exists
    base_namelist = "config_files/namelist.input"
    target_namelist = "namelist.input"
    
    if not os.path.exists(base_namelist):
        # Fallback to current namelist.input if config_files/namelist.input is missing
        base_namelist = "namelist.input"
        
    print(f"Reading base configuration from: {base_namelist}")
    sections = parse_namelist(base_namelist)
    
    if args.case == 'straka':
        print("Configuring case: Straka Dry Density Current (2D)")
        # Section param0
        update_key(sections['param0'], 'nx', '256')
        update_key(sections['param0'], 'ny', '1')
        update_key(sections['param0'], 'nz', '64')
        update_key(sections['param0'], 'procfiles', '.false.')
        
        # Section param1
        update_key(sections['param1'], 'dx', '100.0')
        update_key(sections['param1'], 'dy', '100.0')
        update_key(sections['param1'], 'dz', '100.0')
        update_key(sections['param1'], 'dtl', '0.500')
        update_key(sections['param1'], 'timax', '900.0')   # 15 minutes
        update_key(sections['param1'], 'tapfrq', '60.0')   # Output every 1 minute
        update_key(sections['param1'], 'statfrq', '10.0')
        
        # Section param2
        update_key(sections['param2'], 'iinit', '5')        # Straka density current
        update_key(sections['param2'], 'isnd', '1')         # Dry adiabatic sounding
        update_key(sections['param2'], 'imoist', '0')       # Dry simulation
        update_key(sections['param2'], 'axisymm', '0')      # 2D Cartesian
        update_key(sections['param2'], 'wbc', '2')          # Open boundary X left
        update_key(sections['param2'], 'ebc', '2')          # Open boundary X right
        update_key(sections['param2'], 'sbc', '1')          # Periodic Y (does not matter for ny=1)
        update_key(sections['param2'], 'nbc', '1')
        update_key(sections['param2'], 'sgsmodel', '1')     # Subgrid turbulence model
        
        # Section param8 (parameters for bubble)
        # iinit=5 uses hardcoded ric=0.0, zc=3000.0, bhrad=4000.0, bvrad=2000.0, bptpert=-15.0 in init3d.F.
        # So we don't need to change var parameters for iinit=5
        
        # Section param9 (Output variables)
        update_key(sections['param9'], 'output_format', '2')
        update_key(sections['param9'], 'output_filetype', '1')
        update_key(sections['param9'], 'output_thpert', '1')
        update_key(sections['param9'], 'output_coldpool', '1')
        update_key(sections['param9'], 'output_u', '1')
        update_key(sections['param9'], 'output_w', '1')
        
        # Section param20 (Immersed boundaries)
        update_key(sections['param20'], 'do_ib', '.false.') # Disable windtunnel IB
        update_key(sections['param20'], 'ib_init', '0')

    elif args.case == 'wet_microburst':
        print("Configuring case: Convective Wet Downburst (2D)")
        # Section param0
        update_key(sections['param0'], 'nx', '400')         # 40 km domain
        update_key(sections['param0'], 'ny', '1')           # 2D Cartesian
        update_key(sections['param0'], 'nz', '60')           # 12 km vertical domain (dz=200m)
        update_key(sections['param0'], 'procfiles', '.false.')
        
        # Section param1
        update_key(sections['param1'], 'dx', '100.0')
        update_key(sections['param1'], 'dy', '100.0')
        update_key(sections['param1'], 'dz', '200.0')
        update_key(sections['param1'], 'dtl', '1.000')
        update_key(sections['param1'], 'timax', '2700.0')  # 45 minutes
        update_key(sections['param1'], 'tapfrq', '180.0')  # Output every 3 minutes
        update_key(sections['param1'], 'statfrq', '30.0')
        
        # Section param2
        update_key(sections['param2'], 'iinit', '1')        # Warm bubble trigger
        update_key(sections['param2'], 'isnd', '5')         # Weisman-Klemp sounding
        update_key(sections['param2'], 'imoist', '1')       # Moist simulation
        update_key(sections['param2'], 'ptype', '5')        # Morrison double-moment microphysics
        update_key(sections['param2'], 'axisymm', '0')
        update_key(sections['param2'], 'wbc', '2')          # Open boundary X left
        update_key(sections['param2'], 'ebc', '2')          # Open boundary X right
        update_key(sections['param2'], 'sgsmodel', '1')
        
        # Section param8 (warm bubble centerx/centery are handled dynamically in param.F)
        # We can adjust bubble radius or temp in param8 if needed, but defaults in init3d.F (bptpert=3K, radii=1.5km) are standard and work great.
        
        # Section param9 (Output variables)
        update_key(sections['param9'], 'output_format', '2')
        update_key(sections['param9'], 'output_filetype', '1')
        update_key(sections['param9'], 'output_thpert', '1')
        update_key(sections['param9'], 'output_dbz', '1')    # Reflectivity
        update_key(sections['param9'], 'output_q', '1')      # Rain, cloud mixing ratios
        update_key(sections['param9'], 'output_u', '1')
        update_key(sections['param9'], 'output_w', '1')
        
        # Section param20 (Immersed boundaries)
        update_key(sections['param20'], 'do_ib', '.false.')
        update_key(sections['param20'], 'ib_init', '0')

    print(f"Writing updated configuration to: {target_namelist}")
    write_namelist(sections, target_namelist)
    print("Namelist successfully configured!")

if __name__ == "__main__":
    main()
