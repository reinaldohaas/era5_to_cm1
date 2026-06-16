import os
import glob
import shutil
import numpy as np
import netCDF4 as nc
import matplotlib.pyplot as plt
from PIL import Image

def animate_cm1_results(run_dir=".", output_gif="cm1_animation.gif", fps=5):
    """
    Lê os passos de tempo do arquivo NetCDF do CM1, gera figuras para cada passo
    e compila-as em um GIF animado mostrando a evolução da refletividade e precipitação.
    """
    # 1. Localizar arquivo de saída NetCDF
    nc_files = glob.glob(os.path.join(run_dir, "cm1out.nc"))
    if not nc_files:
        all_nc = glob.glob(os.path.join(run_dir, "cm1out_*.nc"))
        nc_files = sorted([f for f in all_nc if not any(x in f for x in ["stats", "metadata", "_s.nc", "_u.nc", "_v.nc", "_w.nc"])])
        
    if not nc_files:
        print("Nenhum arquivo 'cm1out.nc' ou 'cm1out_*.nc' válido encontrado em:", run_dir)
        return
    
    main_file = nc_files[-1]
    print(f"Lendo dados para animação de: {main_file}")
    ds = nc.Dataset(main_file)
    
    # 2. Extrair coordenadas e dimensões
    x = ds.variables['xh'][:] / 1000.0  # km
    y = ds.variables['yh'][:] / 1000.0  # km
    z = ds.variables['zh'][:] / 1000.0  # km
    times = ds.variables['time'][:]     # segundos
    
    num_times = len(times)
    print(f"Encontrados {num_times} passos de tempo.")
    
    X, Y = np.meshgrid(x, y)
    Xz, Z = np.meshgrid(x, z)
    ny_mid = len(y) // 2
    
    # Criar diretório temporário para frames
    temp_dir = os.path.join(run_dir, "temp_frames")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    frame_files = []
    
    # 3. Gerar frames individuais
    print("Gerando frames individuais...")
    for t_idx in range(num_times):
        t_sec = times[t_idx]
        t_min = t_sec / 60.0
        
        # Extrair variáveis no tempo t
        # Chuva acumulada (cm para mm)
        rain_mm = ds.variables['rain'][t_idx, :, :] * 10.0
        # Refletividade (dBZ)
        dbz = ds.variables['dbz'][t_idx, :, :, :]
        cref = np.max(dbz, axis=0)
        dbz_slice = dbz[:, ny_mid, :]
        
        # Vento vertical W
        w = ds.variables['w'][t_idx, :, :, :]
        if w.shape[0] > len(z):
            w = 0.5 * (w[:-1, :, :] + w[1:, :, :])
        w_slice = w[:, ny_mid, :]
        
        # Criar figura com 3 painéis horizontais
        fig, axs = plt.subplots(1, 3, figsize=(20, 6))
        
        # Painel 1: Refletividade Máxima (Horizontal)
        im1 = axs[0].pcolormesh(X, Y, cref, cmap='nipy_spectral', shading='auto', vmin=0, vmax=70)
        axs[0].set_title("Refletividade Máxima (dBZ)")
        axs[0].set_xlabel("X (km)")
        axs[0].set_ylabel("Y (km)")
        fig.colorbar(im1, ax=axs[0], label="dBZ")
        
        # Painel 2: Corte Vertical X-Z de Refletividade e W (Centro do Cânion)
        im2 = axs[1].pcolormesh(Xz, Z, dbz_slice, cmap='nipy_spectral', shading='auto', vmin=0, vmax=70)
        # Contornar vento vertical ascendente forte (W > 2 m/s) em tons de cinza/preto para destacar updrafts
        if np.max(w_slice) > 2.0:
            axs[1].contour(Xz, Z, w_slice, levels=[2.0, 5.0, 10.0], colors='white', linewidths=1.0, alpha=0.8)
        axs[1].set_title("Corte Vertical X-Z (Refletividade)")
        axs[1].set_xlabel("X (km)")
        axs[1].set_ylabel("Altura Z (km)")
        axs[1].set_ylim(0, 16)
        fig.colorbar(im2, ax=axs[1], label="dBZ (Contornos de W)")
        
        # Painel 3: Precipitação Acumulada (Horizontal)
        im3 = axs[2].pcolormesh(X, Y, rain_mm, cmap='Blues', shading='auto', vmin=0, vmax=50 if np.max(rain_mm) > 5.0 else 5.0)
        axs[2].set_title("Chuva Acumulada na Superfície (mm)")
        axs[2].set_xlabel("X (km)")
        axs[2].set_ylabel("Y (km)")
        fig.colorbar(im3, ax=axs[2], label="Precipitação (mm)")
        
        # Título geral com o tempo
        fig.suptitle(f"Simulação CM1 - Tempo: {t_min:.1f} minutos ({t_sec:.0f}s)", fontsize=16, y=0.98)
        
        plt.tight_layout()
        
        # Salvar frame
        frame_path = os.path.join(temp_dir, f"frame_{t_idx:03d}.png")
        plt.savefig(frame_path, dpi=100, bbox_inches='tight')
        plt.close(fig)
        
        frame_files.append(frame_path)
        
    ds.close()
    
    # 4. Compilar imagens em um GIF animado usando Pillow
    print(f"Compilando {len(frame_files)} frames em {output_gif}...")
    frames = [Image.open(f) for f in frame_files]
    
    # Salvar GIF
    frames[0].save(
        output_gif,
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / fps),  # milissegundos por frame
        loop=0
    )
    
    # Limpeza
    shutil.rmtree(temp_dir)
    print(f"Animação criada com sucesso: {output_gif}")

if __name__ == "__main__":
    import sys
    run_directory = sys.argv[1] if len(sys.argv) > 1 else "."
    animate_cm1_results(run_directory)
