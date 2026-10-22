"""Authenticated, bounded Earth Engine exports. No credential or hard-coded user project."""
import hashlib
import json
from pathlib import Path
import pandas as pd
import ee
from .data import FEATURES,PROVENANCE,save_json,export_config_id

BOUNDARY_SOURCE='FAO/GAUL/2015/level2'
ERA5='ECMWF/ERA5_LAND/DAILY_AGGR'
S1='COPERNICUS/S1_GRD_FLOAT'
EVI='MODIS/061/MOD13A2'


def district_geometry(config):
    districts=ee.FeatureCollection(BOUNDARY_SOURCE).filter(ee.Filter.eq('ADM0_NAME','Bangladesh'))
    selected=districts.filter(ee.Filter.inList('ADM2_NAME',config['districts']))
    names=selected.aggregate_array('ADM2_NAME').getInfo()
    if sorted(names)!=sorted(config['districts']):
        raise ValueError(f'District names did not match GAUL: got {names}. Available: {districts.aggregate_array("ADM2_NAME").getInfo()}')
    return selected.geometry()


def target_projection(config,roi):
    c=ee.ImageCollection(config['smap_collection']).filterDate(config['study_start'],config['study_end_exclusive']).filterBounds(roi)
    n=c.size().getInfo()
    if not n:raise ValueError('No SMAP images in requested version/date interval. Resolve collection coverage before proceeding.')
    dates=ee.List(c.aggregate_array('system:time_start')).map(lambda t:ee.Date(t).format('YYYY-MM-dd'))
    if dates.distinct().size().getInfo()!=n:raise ValueError('Multiple target images per date; define a documented acquisition rule')
    image=ee.Image(c.first());bands=image.bandNames().getInfo()
    if not {'soil_moisture_am','retrieval_qual_flag_am'}<=set(bands):raise ValueError('Required SMAP value/QA bands missing')
    proj=image.select('soil_moisture_am').projection();info=proj.getInfo()
    grid_id=hashlib.sha256(json.dumps(info,sort_keys=True).encode()).hexdigest()[:16]
    return c,proj,grid_id,{'image_count':n,'projection':info,'grid_id':grid_id,
                          'first_date':ee.Date(c.aggregate_min('system:time_start')).format('YYYY-MM-dd').getInfo(),
                          'last_date':ee.Date(c.aggregate_max('system:time_start')).format('YYYY-MM-dd').getInfo()}


def target_cells(roi,projection,pilot_cells=None):
    coordinates=ee.Image.pixelCoordinates(projection).addBands(ee.Image.pixelLonLat())
    cells=coordinates.sample(region=roi,projection=projection,geometries=True,tileScale=4)
    def identify(f):
        return f.set({'cell_id':ee.Number(f.get('x')).format('%d').cat('_').cat(ee.Number(f.get('y')).format('%d')),
                      'lon':f.get('longitude'),'lat':f.get('latitude')})
    cells=cells.map(identify).sort('cell_id')
    return cells.limit(pilot_cells) if pilot_cells else cells


def s1_collection(config,roi):
    c=(ee.ImageCollection(S1).filterBounds(roi)
       .filterDate(ee.Date(config['study_start']).advance(-config['sar_window_days'],'day'),config['study_end_exclusive'])
       .filter(ee.Filter.eq('instrumentMode','IW')).filter(ee.Filter.eq('resolution_meters',10))
       .filter(ee.Filter.eq('orbitProperties_pass',config['orbit_pass']))
       .filter(ee.Filter.listContains('transmitterReceiverPolarisation','VV'))
       .filter(ee.Filter.listContains('transmitterReceiverPolarisation','VH')))
    if config.get('relative_orbit') is not None:
        c=c.filter(ee.Filter.eq('relativeOrbitNumber_start',int(config['relative_orbit'])))
    return c.select(['VV','VH','angle'])


def inventory(config):
    roi=district_geometry(config);target,proj,grid_id,detail=target_projection(config,roi)
    cells=target_cells(roi,proj);s1=s1_collection(config,roi)
    detail.update({'cell_count':cells.size().getInfo(),'relative_orbit_scene_counts':s1.aggregate_histogram('relativeOrbitNumber_start').getInfo(),
                   'boundary':BOUNDARY_SOURCE,'target_collection':config['smap_collection'],
                   'notice':'Counts do not establish whole-AOI coverage, data quality, or RFI cause. Inspect the exported grid.'})
    return detail,cells


def _coarsen(image,source_projection,target,stage_scale):
    """Two REAL area-weighted reductions, retaining input projection before aggregation."""
    # setDefaultProjection restores a composite's known original sampling grid;
    # it never substitutes a coarser grid for the first reduction.
    image=image.setDefaultProjection(source_projection)
    intermediate=(image.reduceResolution(reducer=ee.Reducer.mean(),maxPixels=65536)
                  .reproject(crs=target.crs(),scale=stage_scale))
    return intermediate.reduceResolution(reducer=ee.Reducer.mean(),maxPixels=65536).reproject(target)


def _masked(names,projection):
    return ee.Image.constant([0]*len(names)).rename(names).toFloat().setDefaultProjection(projection).updateMask(ee.Image.constant(0))


def build_month(config,start,end,pilot_cells=None):
    """Build server-side table; caller starts explicit export tasks in their account."""
    if config.get('relative_orbit') is None:raise ValueError('Inspect inventory and explicitly select a relative orbit before exporting')
    vendor=Path(__file__).parent/'vendor'/'terrain_flattening.py'
    exporter_id=hashlib.sha256(Path(__file__).read_bytes()+vendor.read_bytes()).hexdigest()[:20]
    roi=district_geometry(config);smap,proj,grid_id,detail=target_projection(config,roi)
    cells=target_cells(roi,proj,pilot_cells)
    raw=s1_collection(config,roi)
    if raw.size().getInfo()==0:raise ValueError('No SAR images for chosen geometry/orbit')
    from .vendor.terrain_flattening import slope_correction
    dem=ee.Image('USGS/SRTMGL1_003').select('elevation')
    rtc=slope_correction(raw,config['rtc_model'],dem,config['terrain_buffer_m'])
    # Pair identical acquisitions and masks so raw/RTC comparison does not change coverage.
    joined=ee.ImageCollection(ee.Join.saveFirst('rtc_image').apply(raw,rtc,ee.Filter.equals(leftField='system:index',rightField='system:index')))
    def pair(obj):
        r=ee.Image(obj);t=ee.Image(r.get('rtc_image'))
        common=r.select(['VV','VH']).mask().reduce(ee.Reducer.min()).And(t.select(['VV','VH']).mask().reduce(ee.Reducer.min()))
        values=r.select(['VV','VH'],['raw_vv_power','raw_vh_power']).addBands(t.select(['VV','VH'],['rtc_vv_power','rtc_vh_power']))
        age=ee.Image.constant(r.date().millis().divide(86400000)).rename('sar_day').toFloat()
        return values.addBands(age).updateMask(common).copyProperties(r,['system:time_start','system:index'])
    paired=ee.ImageCollection(joined.map(pair));sar_proj=ee.Image(raw.first()).select('VV').projection()
    modis=(ee.ImageCollection(EVI).filterBounds(roi)
           .filterDate(ee.Date(config['study_start']).advance(-config['evi_lookback_days'],'day'),config['study_end_exclusive']))
    modis_proj=ee.Image(modis.first()).select('EVI').projection()
    def clean_evi(img):
        clear=img.select('SummaryQA').eq(0)
        day=ee.Image.constant(img.date().millis().divide(86400000)).rename('evi_day').toFloat()
        return img.select('EVI').multiply(.0001).rename('evi').addBands(day).updateMask(clear).copyProperties(img,['system:time_start','system:index'])
    modis=modis.map(clean_evi)
    climate=(ee.ImageCollection(ERA5).filterBounds(roi)
             .filterDate(ee.Date(config['study_start']).advance(-14,'day'),config['study_end_exclusive']))
    climate_proj=ee.Image(climate.first()).select('temperature_2m').projection()
    lc=ee.ImageCollection('MODIS/061/MCD12Q1').filterDate(f"{config['landcover_reference_year']}-01-01",f"{config['landcover_reference_year']+1}-01-01").first()
    lc=ee.Image(lc).select('LC_Type1');forest=lc.gte(1).And(lc.lte(5)).rename('forest_fraction').toFloat()
    static=_coarsen(dem.rename('elevation_m').addBands(ee.Terrain.slope(dem).rename('slope_deg')),dem.projection(),proj,300)
    static=static.addBands(_coarsen(forest,lc.projection(),proj,1500))
    base_date=ee.Date(start);n=ee.Date(end).difference(base_date,'day').toInt()
    def one_day(offset):
        date=base_date.advance(offset,'day');day=date.millis().divide(86400000)
        targets=smap.filterDate(date,date.advance(1,'day'))
        target=ee.Image(ee.Algorithms.If(targets.size().gt(0),targets.first(),_masked(['soil_moisture_am','retrieval_qual_flag_am'],proj).set('system:index','NONE')))
        present=target.select('soil_moisture_am').mask().rename('target_present').unmask(0)
        sm=target.select('soil_moisture_am').rename('sm_raw')
        qa=target.select('retrieval_qual_flag_am').rename('sm_qa').unmask(255)
        radar=paired.filterDate(date.advance(-config['sar_window_days'],'day'),date)
        rnames=['raw_vv_power','raw_vh_power','rtc_vv_power','rtc_vh_power','sar_day']
        r=ee.Image(ee.Algorithms.If(radar.size().gt(0),radar.mean(),_masked(rnames,sar_proj)))
        r=_coarsen(r,sar_proj,proj,200)
        fraction=_coarsen(ee.Image(ee.Algorithms.If(radar.size().gt(0),radar.select('raw_vv_power').count().gt(0),ee.Image.constant(0).rename('raw_vv_power'))).toFloat().unmask(0),sar_proj,proj,200).rename('sar_valid_fraction')
        bands=[]
        for prefix in ['raw','rtc']:
            vv=r.select(prefix+'_vv_power').max(1e-12).log10().multiply(10).rename(prefix+'_vv_db')
            vh=r.select(prefix+'_vh_power').max(1e-12).log10().multiply(10).rename(prefix+'_vh_db')
            bands.extend([vv,vh,vh.subtract(vv).rename(prefix+'_vh_vv_db')])
        radar_stack=ee.Image.cat(bands).addBands(ee.Image.constant(day).subtract(r.select('sar_day')).rename('sar_age_days'))
        count_image=ee.Image(ee.Algorithms.If(radar.size().gt(0),radar.select('raw_vv_power').count(),ee.Image.constant(0))).rename('sar_count')
        radar_stack=radar_stack.addBands(_coarsen(count_image.toFloat(),sar_proj,proj,200)).addBands(fraction)
        # 16-day composites must END before target day: do not use future constituent observations.
        vegetation=modis.filterDate(date.advance(-config['evi_lookback_days'],'day'),date.advance(-16,'day')).sort('system:time_start')
        veg=ee.Image(ee.Algorithms.If(vegetation.size().gt(0),vegetation.mosaic(),_masked(['evi','evi_day'],modis_proj)))
        vf=_coarsen(veg.select('evi').mask().unmask(0).toFloat(),modis_proj,proj,2000).rename('evi_valid_fraction')
        veg=_coarsen(veg,modis_proj,proj,2000)
        veg=veg.select('evi').addBands(ee.Image.constant(day).subtract(veg.select('evi_day')).rename('evi_age_days')).addBands(vf)
        rain=[]
        for length in [1,3,7,14]:
            rain.append(climate.filterDate(date.advance(-length,'day'),date).select('total_precipitation_sum').sum().max(0).multiply(1000).rename(f'rain_{length}d_mm'))
        era=(ee.Image.cat(rain)
             .addBands(climate.filterDate(date.advance(-3,'day'),date).select('temperature_2m').mean().subtract(273.15).rename('temp_3d_c'))
             .addBands(climate.filterDate(date.advance(-1,'day'),date).select('volumetric_soil_water_layer_1').mean().rename('era5_sm_prev')))
        # ERA5 is already coarser than target. Preserve its support with nearest
        # reprojection instead of inventing fine information or coarsening to 20 km.
        era=era.setDefaultProjection(climate_proj).reproject(proj)
        phase=date.getRelative('day','year').multiply(2*3.141592653589793/365.25)
        doy=ee.Image.constant([phase.sin(),phase.cos()]).rename(['doy_sin','doy_cos']).toFloat()
        stack=sm.addBands(qa).addBands(present).addBands(radar_stack).addBands(veg).addBands(era).addBands(static).addBands(doy)
        # Only wire-format nodata; data loader restores NaN before fitting.
        stack=stack.select(['sm_raw','sm_qa','target_present']+FEATURES).toFloat().unmask(config['export_nodata'],sameFootprint=False)
        props={'date':date.format('YYYY-MM-dd'),'smap_collection':config['smap_collection'],'grid_id':grid_id,
               'smap_image_id':ee.Algorithms.If(targets.size().gt(0),ee.String(config['smap_collection']+'/').cat(ee.String(target.get('system:index'))),'NONE'),
               's1_image_ids':ee.Algorithms.If(radar.size().gt(0),radar.aggregate_array('system:index').join(';'),'NONE'),
               'evi_image_ids':ee.Algorithms.If(vegetation.size().gt(0),vegetation.aggregate_array('system:index').join(';'),'NONE'),
               'boundary_source':BOUNDARY_SOURCE,'feature_version':'chtsm-v2',
               'export_config_id':export_config_id(config),'export_code_id':exporter_id,'synthetic':False}
        return stack.sampleRegions(collection=cells,properties=['cell_id','lon','lat'],projection=proj,geometries=False,tileScale=4).map(lambda f:f.set(props))
    table=ee.FeatureCollection(ee.List.sequence(0,n.subtract(1)).map(one_day)).flatten()
    return table,detail


def start_month_export(config,start,end,folder,prefix,pilot_cells=None):
    if not pd.Timestamp(config['study_start'])<=pd.Timestamp(start)<pd.Timestamp(end)<=pd.Timestamp(config['study_end_exclusive']):
        raise ValueError('Export interval outside declared study')
    if (pd.Timestamp(end)-pd.Timestamp(start)).days>31:raise ValueError('Use monthly tasks, not a national multi-year request')
    table,detail=build_month(config,start,end,pilot_cells)
    selectors=['date','cell_id','lon','lat','sm_raw','sm_qa','target_present']+FEATURES+PROVENANCE
    task=ee.batch.Export.table.toDrive(collection=table,description=prefix,folder=folder,
                                     fileNamePrefix=prefix,fileFormat='CSV',selectors=selectors)
    task.start()
    return {'task_id':task.id,'prefix':prefix,'start':start,'end_exclusive':end,'pilot_cells':pilot_cells,'grid':detail}


def month_windows(config):
    starts=pd.date_range(config['study_start'],config['study_end_exclusive'],freq='MS')
    return [(str(a.date()),str(b.date())) for a,b in zip(starts[:-1],starts[1:])]
