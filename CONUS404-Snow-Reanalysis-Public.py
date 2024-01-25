import json
import requests
import numpy as np
import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.colors import BoundaryNorm
from mpl_toolkits.axes_grid1 import make_axes_locatable
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
from datetime import datetime

# This script will take some time to run
# Data is available back to October 1979
# Please change the following rows before running:
# Inputs - 114, 115, 119, 147
# Features - 173
# Outputs - 198

def createMap(extent):
    # Initialize map
    fig = plt.figure(figsize=(9, 9))
    fig.tight_layout()
    ax = plt.axes(projection=ccrs.Mercator()) # Change CRS here as needed
    
    # Add state and country borders using cartopy's cfeature library
    ax.add_feature(cfeature.BORDERS)
    ax.add_feature(cfeature.STATES, linewidth=0.6, zorder=12)

    # Add county borders from a GitHub dataset
    reader = shpreader.Reader('https://raw.githubusercontent.com/EFisher828/geojson-store/main/CONUS%20Counties.geojson')
    counties = list(reader.geometries())
    COUNTIES = cfeature.ShapelyFeature(counties, ccrs.PlateCarree())
    ax.add_feature(COUNTIES, facecolor='none',linewidth=0.1, zorder=12)
    
    # Set desired map extent
    ax.set_extent(extent,ccrs.PlateCarree())
    
    return ax, fig

def fetchCOOP(start_time,end_time,extent):
    # Define the bounding box using the extent and create a ACIS API request URL
    bboxStr = f'{extent[0]},{extent[2]},{extent[1]},{extent[3]}'
    startDateStr = start_time.split(' ')[0]
    endDateStr = end_time.split(' ')[0]
    url = f'https://data.rcc-acis.org/MultiStnData?bbox={bboxStr}&sdate={startDateStr}&edate={endDateStr}&elems=snow&output=json'
    
    # Fetch data from the URL
    response = requests.get(url)
    
    data = json.loads(response.text)['data']
    
    dataCOOP = []
    
    # Process COOP data - for station in data array
    for key in data:
        lon = float(key['meta']['ll'][0])
        lat = float(key['meta']['ll'][1])
        
        # Initially assume there is some missing data
        noMissing = False 
        
        day = 0
        # For daily report in station data
        for report in key['data']:
            try:
                report = report[0]
                # If there is a missing day of data, skip this station
                if report == 'M':
                    break
                # If there is a trace observed, count it as 0.0001
                elif report == 'T':
                    report = 0.0001
                # Else, the data must be a float
                else:
                    report = float(report)
                
                # If it is the first day in the record, initialize the running sum
                if day == 0:
                    snowSum = report
                # Else, append to the running sum
                else:
                    snowSum += report
                
                day += 1
                
                # If it's the last day in the record and no missing values have been found, noMissing = True
                if day == len(key['data']):
                    noMissing = True
            except:
                print("Something went wrong with this COOP station's data")
        
        # If there are no missing values for this station
        if noMissing == True:
            # If only combination of 0s and Ts were reported, sum is T
            if snowSum != 0 and snowSum < 0.1:
                snowSum = 'T'
            else:
                # Only allow decimals for values less than 1, else round to the nearest integer
                if snowSum < 1:
                    snowSum = str(round(snowSum,1))
                else:
                    snowSum = str(round(snowSum))
            
            # If the data sum is not zero, add it to the list that will go on the map 
            if snowSum != '0.0':
                dataCOOP.append([snowSum, lon, lat])
        
    return dataCOOP

# Define desired time frame - Inclusive on both ends and MUST capture entire days to match COOP reports
start_time = '1989-12-22 00:00'
end_time = '1989-12-24 23:00'

# Define the desired extent of the map
# IMPORTANT NOTE - you may have to adjust the y coordinates of the plt.text elements to match a new extent
extent = [-85.13,-74.74,31.59,37.19]

# Fetch the COOP snowfall data for the desired dates and extent
dataCOOP = fetchCOOP(start_time,end_time,extent)

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
        
    # Define snow to liquid ratio and use calculate hourly accumulated snow
    slr = 12
    snow = (ds.SNOW_ACC_NC/25.4)*slr
            
    # Define the latitude and longitude grid
    lon = snow.XLONG
    lat = snow.XLAT
    
    # Determine whether running sum exists and add snow data accordingly
    if str(timestamp)[:-3] == start_time:
        totalSnow = snow.data
    else:
        totalSnow += snow.data

# Create and define the map axis and figure         
ax, fig = createMap(extent)

# Define the color ramp for the data (capped at 24", but remove # on colors and levels line to extend)
colors = [(0,0,0,0),'#e9e9e9','#b3dff5','#87c4ff','#4d8fff','#3a5dff','#2e34cc','#cec5f0','#aea1ef','#9b71ef','#6738c4','#45306e','#faa3a7']#,'#ef7390','#e94e77']
cmap = plt.cm.colors.ListedColormap(colors)
levels = [0,0.0001,0.5,1,2,3,4,6,8,10,12,18,24,36]#,48,1000]
norm = BoundaryNorm(levels, cmap.N)

# Plot total snowfall on a map
cs = ax.contourf(lon.data,lat.data,totalSnow[0],cmap=cmap,norm=norm,levels=levels,transform=ccrs.PlateCarree())

# Update text as desired
fig.text(0.13,0.75,f'Total Snowfall ({slr}:1 SLR)- December 22-24, 1989', fontsize=10, fontweight='bold')
fig.text(0.87,0.75,'Source: CONUS404, COOP', fontsize=10, ha='right', fontweight='bold')
fig.text(0.5,0.244,'This is an automated map, and shaded areas are reanalysis estimates. Likewise, COOP reports have not been verified.',fontsize=8,ha='center')

# Set the colorbar location
divider = make_axes_locatable(ax)
ax_cb = divider.new_horizontal(size="3%", pad=0.1, axes_class=plt.Axes)
cb = plt.colorbar(cs, cax=ax_cb)

# Set the colorbar tick labels
cb.set_ticks([0.0001,0.5,1,2,3,4,6,8,10,12,18,24])
cb.set_ticklabels(['T','0.5"','1"','2"','3"','4"','6"','8"','10"','12"','18"','24"'])

# Iterate through the COOP reports and add to map
for station in dataCOOP:
    snowReport = station[0]
    x = station[1]
    y = station[2]
    # If data is slightly offset within extent add to map - ensures doesn't spill out of map container
    if np.logical_and(x>extent[0]+0.1,x<extent[1]-0.1) and np.logical_and(y>extent[2]+0.1,y<extent[3]-0.1):
        plt.text(x,y,snowReport,transform=ccrs.PlateCarree(),va='center',ha='center',color='white',fontsize=7,fontweight='bold',path_effects=[pe.withStroke(linewidth=3, foreground="black")], zorder=100)

fig.add_axes(ax_cb)

# Save the map
plt.savefig('./Exports/Dec-22-24-1989-Snowfall-Automated.png', bbox_inches='tight', dpi=300)

