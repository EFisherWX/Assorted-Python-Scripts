# -*- coding: utf-8 -*-
"""
Created on Sun Jan  7 16:57:34 2024

@author: evanw
"""

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.colors import BoundaryNorm
from mpl_toolkits.axes_grid1 import make_axes_locatable
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
from datetime import datetime

def findIndex(coords,x,y):
    indexList = []
    countIndex = 0
    for i in coords:
        if countIndex in [0,1]:
            difList = abs(abs(x) - abs(i))
            index = np.where(difList==np.nanmin(difList))[0][0]
        else:
            difList = abs(abs(y) - abs(i))
            index = np.where(difList==np.nanmin(difList))[0][0]
            
        indexList.append(index)
        countIndex += 1
    return indexList

model = input('NAM or HRRR?: ')
hour = input('Hour Initialized (ex. 06): ')
date = input('Date Initialized (ex. 20240107): ')

model_dict = {
    'NAM': {
        'url': f'http://nomads.ncep.noaa.gov:80/dods/nam/nam{date}/nam_conusnest_{hour}z',
        'title': 'NAM 3km'
    },
    'HRRR': {
        'url': f'http://nomads.ncep.noaa.gov:80/dods/hrrr/hrrr{date}/hrrr_sfc.t{hour}z',
        'title': 'HRRR'
    }
}

# Initialize map
fig = plt.figure(figsize=(9, 9))
fig.tight_layout()
ax = plt.axes(projection=ccrs.Mercator()) # Change CRS here as needed

# Add state and country borders using cartopy's cfeature library
ax.add_feature(cfeature.BORDERS)
ax.add_feature(cfeature.STATES, linewidth=1, zorder=12)

reader = shpreader.Reader('./Shapefiles/cb_2018_us_county_5m.shp')
counties = list(reader.geometries())
COUNTIES = cfeature.ShapelyFeature(counties, ccrs.PlateCarree())
ax.add_feature(COUNTIES, facecolor='none',linewidth=0.2, zorder=12)

colors = [(0,0,0,0),'#D7D4D5','#BFBDBE','#979495','#656365','#1566D3','#216CEC','#2A82EF','#4096F4','#51A5F4','#7FB7F6','#98D6FC','#B1F1FF','#10A011','#22B420','#37D43C','#79F675','#96F38E','#B6FAAD','#C5FFBB','#FFE77A','#FDC336','#FDA400','#FF5F00','#FF2E01','#E41205','#C60007','#A60101','#5F3E35','#7B4E47','#8D645B','#A27870','#E2BFB5','#F0DED5','#FEC7C9','#F89FA0','#F37F73','#E3605B','#D9443E','#D32D2F','#D62C27','#B52E29','#B62F29','#AD4545','#9E5D5D','#937573','#938282','#7D7B7A']
cmap = plt.cm.colors.ListedColormap(colors)
levels = [0,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,50,54,58,61,64,66,68,70,72,74,76,80,84,88,92,96,100,104,108,112,116,120,124,128,132,135,145,1000]
norm = BoundaryNorm(levels, cmap.N)

conus = [-127.11,-64.81,23.82,49.97]
southern_apps = [-85.0302,-80.3544,34.509,36.7941]
ax.set_extent(southern_apps,ccrs.PlateCarree())

# Data feed
ds = xr.open_dataset(model_dict[model]['url'])

count = 0
for time in ds.time:
    time = datetime.strptime(str(time.data)[0:13],'%Y-%m-%dT%H')
    timeString = time.strftime('%Y%m%d-%H')
    print(timeString)
    gust = ds.gustsfc[count,:,:]*2.23693629
    
    x = gust.lon
    y = gust.lat
    
    indexList = findIndex([-85.0302-0.2,-80.3544+0.2,34.509-0.2,36.7941+0.2],x,y)
    
    gust = gust[indexList[2]:indexList[3],indexList[0]:indexList[1]]
    
    x = gust.lon
    y = gust.lat
    
    cs = ax.contourf(x, y, gust, cmap=cmap, norm=norm, levels=levels, transform=ccrs.PlateCarree())
    
    fig.text(0.13,0.725,f'{model_dict[model]["title"]} Surface Wind Gust (mph)',ha='left')
    fig.text(0.85,0.725,'Valid: ' + time.strftime('%Hz %a, %b %d, %Y'),ha='right')
    fig.text(0.13,0.267,f'Init: {hour}z {(datetime.strptime(date,"%Y%m%d")).strftime("%a, %b %d, %Y")}',ha='left')
    fig.text(0.85,0.267,f'Max: {int(np.nanmax(gust))} mph',ha='right')
    
    if count == 0:
        divider = make_axes_locatable(ax)
        ax_cb = divider.new_horizontal(size="5%", pad=0.1, axes_class=plt.Axes)
        cb = plt.colorbar(cs, cax=ax_cb)
        #cb.set_ticks(tickLocList)
        #cb.set_ticklabels(['No Color','Low Color','Moderate Color','High Color','Peak Color','Past Peak',''])
        fig.add_axes(ax_cb)
        
    plt.savefig(f'./{model} Gusts/{timeString}.png',dpi=300,bbox_inches='tight')
    
    #cs.remove()
    
    for coll in cs.collections:
        coll.remove()
    
    for ttl in fig.texts:
        ttl.set_visible(False)
    
    count += 1