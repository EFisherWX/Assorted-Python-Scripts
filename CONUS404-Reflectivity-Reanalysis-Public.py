import numpy as np
import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
from datetime import datetime

# This script will take some time to run
# Data is available back to October 1979
# Please adjust the following rows as desired before running:
# Inputs - 51, 52, 56, 133
# Outputs - 141

def createMap(extent):
    # Initialize map
    fig = plt.figure(figsize=(9, 9))
    fig.tight_layout()
    ax = plt.axes(projection=ccrs.Mercator()) # Change CRS here as needed
    
    # Add state and country borders using cartopy's cfeature library
    ax.add_feature(cfeature.BORDERS)
    ax.add_feature(cfeature.STATES, linewidth=0.6, zorder=12)

    # Add county borders from a GitHub dataset - uncomment lines 40 - 43 if desired
    # reader = shpreader.Reader('https://raw.githubusercontent.com/EFisher828/geojson-store/main/CONUS%20Counties.geojson')
    # counties = list(reader.geometries())
    # COUNTIES = cfeature.ShapelyFeature(counties, ccrs.PlateCarree())
    # ax.add_feature(COUNTIES, facecolor='none',linewidth=0.05, zorder=12)
    
    # Set desired map extent
    ax.set_extent(extent,ccrs.PlateCarree())
    
    return ax, fig

# Define color palettes
colors_rain = [(0.1,0.1,0.1,0),'#00FB4C','#00E445','#00CD3E','#00B537','#009E2E','#018628','#016F20','#005518','#FFFF50','#FCD347','#FBA141','#FF763B','#FF272B','#D80E3A','#B6093D','#900649','#C90DA9','#FF04DC']
colors_snow = [(0.1,0.1,0.1,0),'#02FEFE','#00EAFD','#01D3FD','#03BFFC','#00AAFC','#0092FC','#0275F2','#0459E8','#073AD6','#0D23C4','#0A1DBB','#05159B','#291099','#490C92','#AC0F8B','#CC0D8F','#FF0C80']
cmap_rain = plt.cm.colors.ListedColormap(colors_rain)
cmap_snow = plt.cm.colors.ListedColormap(colors_snow)
levels_rain = [0,0.1,0.25,0.5,1,1.5,2,2.5,3,4,5,6,8,10,12,16,20,24,28,100]
levels_snow = [0,0.1,0.25,0.5,0.75,1,1.5,2,2.5,3,3.5,4,5,6,8,10,12,14,100]

# Create a BoundaryNorm to map values to colormap boundaries
norm_rain = BoundaryNorm(levels_rain, cmap_rain.N, clip=True)
norm_snow = BoundaryNorm(levels_snow, cmap_snow.N, clip=True)

# Define desired time frame - Inclusive on both ends and MUST capture entire days to match COOP reports (i.e., starts with hour 00 and ends with hour 23)
start_time = '1993-03-12 00:00'
end_time = '1993-03-14 23:00'

# Define the desired extent of the map
# IMPORTANT NOTE - you may have to adjust the y coordinates of the fig.text elements to match a new extent
extent = [-94.05,-66.07,30.13,47.69]

# Create and define the map axis and figure         
ax, fig = createMap(extent)

# Define the time range in hours using the start and end time
time_range = pd.date_range(start=start_time, end=end_time, freq='H')

# Iterate through the hours in time_range
for timestamp in time_range:
    print(f'{round((list(time_range).index(timestamp)/len(list(time_range)))*100)}%')
    # Convert time to datetime object and split into year, month, day, and hour
    testDate_dt = datetime.strptime(str(timestamp)[:-3],"%Y-%m-%d %H:00")
    year = testDate_dt.strftime('%Y')
    month = testDate_dt.strftime('%m')
    day = testDate_dt.strftime('%d')
    hour = testDate_dt.strftime('%H')
    
    # Determine the water of the desired date range
    if int(month) > 6:
        wYear = str(int(year)+1)
    else:
        wYear = year
    
    # Fetch the CONUS404 data from a UCAR THREDDS server
    url = f'https://thredds.rda.ucar.edu/thredds/dodsC/files/g/ds559.0/wy{wYear}/{year}{month}/wrf2d_d01_{year}-{month}-{day}_{hour}:00:00.nc'
    ds = xr.open_dataset(url)
            
    # Define the accumulated precip variable
    accPrecip = ds.PREC_ACC_NC[0,250:-200,700:]
    
    # Define the fraction of frozen precipitation variable
    frozenFrac = ds.SR[0,250:-200,700:]
    
    # If frozen frac > 0.5, snow. Else, rain. Not perfect, but good enough...
    accPrecip_snow = accPrecip.where(frozenFrac >= 0.5, 0)
    accPrecip_rain = accPrecip.where(frozenFrac < 0.5, 0)
    
    # Define surface pressure variable
    pressure = ds.PSFC[0,250:-200,700:]
    
    # Define surface geopotential height variable
    height = ds.Z[0,250:-200,700:]
    
    # Define surface air temperature
    temperature = ds.TK[0,250:-200,700:]
    
    # Calculate mean sea level pressure
    mslp = (pressure*np.exp(height/(29.3*temperature)))/100
        
    # Extract valid time from file using datetime library
    validTime = datetime.strptime(ds.Times.data[0].decode(),"%Y-%m-%d_%H:%M:%S")
    
    # Format the date as needed for use later in script
    formattedDate = validTime.strftime('%b. %d, %Y %Hz')
    fileDate = validTime.strftime("%Y%m%d%H")
    
    # Define wind variables
    uWind = ds.U[0,250:-200,700:].data
    vWind = ds.V[0,250:-200,700:].data
    
    # Define lat/lon variables
    lat = ds.XLAT[250:-200,700:].data
    lon = ds.XLONG[250:-200,700:].data
    
    # Add colored snow depth contours to the map
    cs_rain = ax.contourf(lon, lat, accPrecip_rain, cmap=cmap_rain, norm=norm_rain, levels=levels_rain, zorder=0, transform=ccrs.PlateCarree())
    cs_snow = ax.contourf(lon, lat, accPrecip_snow, cmap=cmap_snow, norm=norm_snow, levels=levels_snow, zorder=1, transform=ccrs.PlateCarree())
    
    # Add black, dashed MSLP contours to the map
    cp = ax.contour(lon, lat, mslp, levels=np.arange(960,1035,5), colors="black", linewidths=0.8, linestyles="dashed", transform=ccrs.PlateCarree())
    
    # Add labels within MSLP contours
    cl = ax.clabel(cp, inline=1, fontsize=7) 
    
    # Add text to the map
    fig.text(0.888,0.172,'Source: CONUS404',fontsize=8,ha='right')
    fig.text(0.13,0.172,'Created by Your Name Here',fontsize=8)
    fig.text(0.13,0.822,"1-Hour Precip Rate (mm/hr), MSLP (hPa), & Sfc Wind (kt)", fontsize=10, fontweight='bold') #0.845 if no colorbar
    fig.text(0.888,0.822,formattedDate,ha="right")
    
    # Add wind barbs to map. [::-10,::-10] adds every tenth barb to avoid overcrowding the map
    cw = ax.barbs(lon[::-20,::-20], lat[::-20,::-20], uWind[::-20,::-20], vWind[::-20,::-20], length=4, color="#3d3d3d", linewidth=0.3, transform=ccrs.PlateCarree())
    
    # Save the map - make sure you adjust the filepath as desired
    plt.savefig(f'./Exports/Composite-Reflectivity/CONUS/{fileDate}-mix.png', bbox_inches="tight", dpi=200)
    
    # Remove the rain contours
    for coll1 in cs_rain.collections:
        coll1.remove()
        
    # Remove the snow contours
    for coll2 in cs_snow.collections:
        coll2.remove()
        
    # Remove the mslp contours
    for coll3 in cp.collections:
        coll3.remove()
        
    # Remove the wind barbs
    cw.remove()
    
    #Remove the wind barb labels
    for label in cl:
        label.remove()
                
    # Remove all text on the figure
    for txt in fig.texts:
        txt.set_visible(False)