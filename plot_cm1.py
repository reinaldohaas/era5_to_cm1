import os
import glob
import numpy as np
import netCDF4 as nc
import matplotlib.pyplot as plt

def plot_cm1_results(run_dir=".", output_image="cm1_plots.png"):
    """
    Localiza os arquivos NetCDF gerados pelo CM1, extrai os campos físicos
    e plota mapas horizontais (Precipitação e Refletividade Máxima) e cortes
    verticais (X-Z) da tempestade através do centro do domínio.
    """
    # Encontra arquivos cm1out_*.nc
    nc_files = sorted(glob.glob(os.path.join(run_dir, "cm1out_*.nc")))
    if not nc_files:
        print("Nenhum arquivo 'cm1out_*.nc' encontrado no diretório:", run_dir)
        print("Certifique-se de que a simulação rodou com sucesso e os arquivos de saída estão presentes.")
        return
    
    print(f"Encontrados {len(nc_files)} arquivos de saída do CM1.")
    
    # Abre o último arquivo de saída para ler o estado acumulado final
    last_file = nc_files[-1]
    print(f"Processando arquivo de saída: {last_file}")
    ds = nc.Dataset(last_file)
    
    # Extração de Coordenadas (convertendo metros para km)
    x = ds.variables['xh'][:] / 1000.0
    y = ds.variables['yh'][:] / 1000.0
    z = ds.variables['zh'][:] / 1000.0  # Grade vertical
    
    X, Y = np.meshgrid(x, y)
    
    # 1. Precipitação Acumulada na Superfície (em mm)
    # No CM1 com outunits=1 (MKS), a chuva é salva em 'cm'. Convertemos multiplicando por 10.
    rain_cm = ds.variables['rain'][0, :, :]
    rain_mm = rain_cm * 10.0
    
    # 2. Refletividade do Radar (dBZ) - Calculamos a Refletividade Máxima da coluna (Cref)
    dbz = ds.variables['dbz'][0, :, :, :]  # Shape: (z, y, x)
    cref = np.max(dbz, axis=0)            # Máximo vertical
    
    # 3. Velocidade Vertical (W)
    w = ds.variables['w'][0, :, :, :]      # Shape: (z_face, y, x)
    # Interpola W das faces para o centro da célula vertical para alinhar com dbz e z
    if w.shape[0] > len(z):
        w = 0.5 * (w[:-1, :, :] + w[1:, :, :])
    
    # Fatia vertical X-Z no centro geométrico de Y
    ny_mid = len(y) // 2
    dbz_slice = dbz[:, ny_mid, :]
    w_slice = w[:, ny_mid, :]
    
    # Grade para o corte vertical X-Z
    Xz, Z = np.meshgrid(x, z)
    
    # --- Montagem dos Gráficos ---
    fig, axs = plt.subplots(2, 2, figsize=(15, 12))
    
    # Painel 1: Refletividade Máxima na Coluna (dBZ)
    im1 = axs[0, 0].pcolormesh(X, Y, cref, cmap='nipy_spectral', shading='auto', vmin=0, vmax=70)
    axs[0, 0].set_title("Refletividade Máxima na Coluna (dBZ)")
    axs[0, 0].set_xlabel("X (km)")
    axs[0, 0].set_ylabel("Y (km)")
    fig.colorbar(im1, ax=axs[0, 0], label="Refletividade (dBZ)")
    
    # Painel 2: Precipitação Acumulada
    im2 = axs[0, 1].pcolormesh(X, Y, rain_mm, cmap='Blues', shading='auto', vmin=0)
    axs[0, 1].set_title("Precipitação Acumulada na Superfície (mm)")
    axs[0, 1].set_xlabel("X (km)")
    axs[0, 1].set_ylabel("Y (km)")
    fig.colorbar(im2, ax=axs[0, 1], label="Precipitação (mm)")
    
    # Painel 3: Corte Vertical X-Z (Refletividade)
    im3 = axs[1, 0].pcolormesh(Xz, Z, dbz_slice, cmap='nipy_spectral', shading='auto', vmin=0, vmax=70)
    axs[1, 0].set_title(f"Corte Vertical X-Z (Refletividade) no centro Y={y[ny_mid]:.1f}km")
    axs[1, 0].set_xlabel("X (km)")
    axs[1, 0].set_ylabel("Altura Z (km)")
    axs[1, 0].set_ylim(0, 16)  # Foco na troposfera (até 16 km)
    fig.colorbar(im3, ax=axs[1, 0], label="Refletividade (dBZ)")
    
    # Painel 4: Corte Vertical X-Z (Velocidade Vertical W)
    im4 = axs[1, 1].pcolormesh(Xz, Z, w_slice, cmap='RdBu_r', shading='auto', vmin=-15, vmax=15)
    axs[1, 1].set_title(f"Corte Vertical X-Z (Vento Vertical W) no centro Y={y[ny_mid]:.1f}km")
    axs[1, 1].set_xlabel("X (km)")
    axs[1, 1].set_ylabel("Altura Z (km)")
    axs[1, 1].set_ylim(0, 16)
    fig.colorbar(im4, ax=axs[1, 1], label="W (m/s)")
    
    plt.tight_layout()
    plt.savefig(output_image, dpi=150, bbox_inches='tight')
    print(f"Gráficos salvos com sucesso em: {output_image}")
    
    ds.close()

if __name__ == "__main__":
    import sys
    run_directory = sys.argv[1] if len(sys.argv) > 1 else "."
    plot_cm1_results(run_directory)
