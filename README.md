# ERA5 to CM1 input_sounding Generator

Este projeto contém um script em Python para baixar dados de reanálise do **ERA5** (níveis de pressão e variáveis de superfície) da **Copernicus Climate Data Store (CDS)** e gerar um arquivo de sondagem vertical `input_sounding` formatado especificamente para o modelo **CM1 (Cloud Model 1)**.

## Requisitos

Os pacotes necessários já estão instalados no seu ambiente virtual principal (`c:\Users\haas\github\.venv`). São eles:
* `cdsapi`
* `xarray`
* `netCDF4`
* `numpy`

## Configuração do Copernicus CDS API

Para fazer o download automático dos dados do ERA5, você precisará de uma conta no Copernicus CDS e salvar suas credenciais.

1. Acesse e registre-se no site: [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/)
2. Vá para a sua página de perfil do usuário e copie a chave de API (Personal Access Token).
3. Crie um arquivo chamado `.cdsapirc` na pasta home do seu usuário:
   * **Windows**: `C:\Users\haas\.cdsapirc`
   * **Linux/macOS**: `~/.cdsapirc`
4. Adicione as seguintes duas linhas ao arquivo `.cdsapirc` (substituindo `<SUA-CHAVE-API>` pela chave copiada):
   ```text
   url: https://cds.climate.copernicus.eu/api
   key: <SUA-CHAVE-API>
   ```

*Nota: Certifique-se de aceitar os **Termos de Uso** (Terms and Conditions) do conjunto de dados ERA5 na interface web do CDS antes de tentar baixá-los via API.*

## Como Executar

Abra o terminal e execute o script. Por padrão, ele está configurado para buscar os dados de **17 de dezembro de 2020 às 03:00 UTC** para as coordenadas de **Rio do Sul / SC**:

```bash
# Ativar o ambiente virtual (se necessário)
& c:\Users\haas\github\.venv\Scripts\Activate.ps1

# Executar com as configurações padrão
python era5_to_sounding.py
```

### Argumentos Personalizados

Você pode alterar a data, hora, coordenadas ou o arquivo de saída usando argumentos de linha de comando:

```bash
python era5_to_sounding.py --lat -27.102765 --lon -49.624542 --date 2020-12-17 --time 03:00 --output input_sounding_custom
```

### Parâmetros do Script:
* `--lat`: Latitude do local desejado (Padrão: `-27.102765`).
* `--lon`: Longitude do local desejado (Padrão: `-49.624542`).
* `--date`: Data no formato `AAAA-MM-DD` (Padrão: `2020-12-17`).
* `--time`: Horário UTC no formato `HH:MM` (Padrão: `03:00`).
* `--output`: Nome do arquivo de saída (Padrão: `input_sounding`).
* `--no-download`: Se você já tiver os arquivos `era5_pressure_levels.nc` e `era5_single_levels.nc` baixados, use este argumento para processar a sondagem sem fazer uma nova requisição.

## Detalhes Físicos e Conversões

O script realiza as seguintes transformações nos dados do ERA5 para atender às especificações do CM1:

1. **Altitude acima do nível do solo ($z_{AGL}$)**:
   O geopotencial ($\Phi$) do ERA5 em níveis de pressão é convertido para altitude geométrica sobre o nível do mar ($z_{ASL} = \Phi / 9.80665$). Em seguida, subtrai-se a altitude do relevo ($z_{sfc}$) calculada a partir do geopotencial de superfície na reanálise, garantindo que a sondagem comece a partir do solo ($z_{AGL} = 0$).
2. **Temperatura Potencial ($\theta$)**:
   $$\theta = T \cdot \left(\frac{1000}{P}\right)^{0.285896}$$
3. **Razão de Mistura da Água ($q_v$)**:
   * Para os níveis de pressão, a umidade específica ($q$) é convertida para razão de mistura: $q_v = \frac{q}{1-q} \cdot 1000$ (em g/kg).
   * Para a superfície, a temperatura do ponto de orvalho a 2 metros ($T_{d,2m}$) é convertida para pressão de vapor e então calculada a razão de mistura de superfície em g/kg.
4. **Alinhamento da Superfície**:
   A primeira linha do perfil vertical ($z_{AGL} = 0$) é preenchida com as variáveis de superfície (temperatura potencial calculada a partir do termômetro a 2m, umidade de 2m e ventos a 10 metros para as componentes U e V). Os níveis de pressão que ficam abaixo da cota do relevo são descartados automaticamente.
