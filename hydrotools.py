"""
Created on Mon Sep 21 23:18:13 2020
@author: danie
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from delft3dfmpy import HyDAMO
from delft3dfmpy.converters.hydamo_to_dflowfm import roughness_gml
from delft3dfmpy.core.geometry import find_nearest_branch
from pathlib import Path
from math import isnan

from shapely.geometry import LineString, Point
from shapely.ops import snap
import pickle

hydamo = HyDAMO()

ATTRIBUTES = ["crosssections",
              "bridges",
              "culverts",
              "orifices",
              "weirs",
              "gemalen",
              "pumps"]

def _valid_pprof(prof_def):
    prof_def["slope"] = max(0.1, prof_def["slope"])
    prof_def["bottomwidth"] = max(0.5, prof_def["bottomwidth"])
    prof_def["maximumflowwidth"] = max(prof_def["bottomwidth"],
                                       prof_def["maximumflowwidth"])
    
    return(prof_def)

def _make_list(item):
    if not isinstance(item, list):
        item = [item]
    return item


def _filter(gdf, attribute_filter):
    if isinstance(attribute_filter, dict):
        for key, value in attribute_filter.items():
            value = _make_list(value)
            gdf = gdf[gdf[key].isin(value)]

        return gdf
    else:
       raise IOError('attribute_filter should be dictionary') 


def read_file(path,
              hydamo_attribute,
              index_col=None,
              keep_indices=None,
              attribute_filter=None,
              snap_to_branches=None,
              keep_columns=None,
              column_mapping=None,
              z_coord=False
              ):
        """
        Read any OGR supported feature-file to match hydamo-property.
        A mask file can be specified to clip the selection.
        Parameters
        ----------
        path : str or Path
            Path to the feature file
        hydamo_attribute : HyDAMO property
            property to map to (HyDAMO.branches, HyDAMO.crosssections)
        index_col: str
            column to be used to identify rows to keep
        keep_indices: List[str]
            values in index_col to keep after filtering & snapping
        attribute_filter: dict
            dict with lists or strings of the format {'column_name': [values to keep]}
        snap_to_branches: dict
            snap to a geodataframe with LineStrings. Keep only geometries that snap
            to a LineString with a certain attribute value.
            Format: {'branches': GeoDataFrame,
                     attribute_filter: {'column_name': [values to keep]}}
        column_mapping: dict
            dict for renaming input colunns to required columns
        Result: GeoDataFrame matching the HyDAMO property
        """
        gdf = gpd.read_file(path)
        gdf.columns = gdf.columns.str.lower()

        index_col = next(
                (k.lower() for k, v in column_mapping.items() if v.lower() == "code"),
                None)

        if index_col is None:
            index_col = "code"
            
            

        # filter by gdf_snap
        if snap_to_branches:
            distance = snap_to_branches["distance"]
            branches = snap_to_branches["branches"]
            find_nearest_branch(branches, gdf, maxdist=distance)
            gdf = gdf.loc[gdf["branch_offset"].notna()]
            gdf.loc[:, "hydromodel"] = gdf.apply(
                (lambda x: branches.loc[x["branch_id"]]["hydromodel"]),
                axis=1)

            if snap_to_branches["attribute_filter"]:
                snap_attribute_filter = {
                    key.lower(): value for key, value in snap_to_branches[
                        "attribute_filter"].items()}
                gdf = _filter(gdf, snap_attribute_filter)

        # filter by attribute
        if attribute_filter:
            attribute_filter = {
                key.lower(): value for key, value in attribute_filter.items()}
            gdf = _filter(gdf,
                          attribute_filter)

        # map to hydamo columns
        if column_mapping:
            column_mapping = {
                key.lower(): value.lower() for key, value in column_mapping.items()
                }
            gdf.rename(columns=column_mapping, inplace=True)

        # drop all columns not needed
        required_columns = getattr(hydamo, hydamo_attribute).required_columns.copy()

        if keep_columns:
            required_columns += [col.lower() for col in keep_columns]

        if hydamo_attribute == 'crosssections':
            if z_coord:
                required_columns += ['z', 'order']

        drop_cols = [
            col for col in gdf.columns if col not in required_columns + ['geometry']
            ]
        if len(drop_cols) > 0:
            gdf = gdf.drop(drop_cols, axis=1)

        return gdf


def to_file(model, hydamo_attribute, length=False, path=Path('.')):
    """Convert hydamo class to shape-file."""
    path = Path(path)
    hydamo_class = getattr(model, hydamo_attribute)
    if not hydamo_class.empty:
        data = {col: hydamo_class[col].values for col in hydamo_class.columns}

        if length:
            data = data = {**data, 'length': hydamo_class['geometry'].length.values}

        gpd.GeoDataFrame(data=data).to_file(path.joinpath(f'{hydamo_attribute}.shp'))


def snap_ends(gdf, tolerance, digits=None):
    """Snap all end-vertices within a specified tolerance."""
    sindex = gdf.sindex
    snapped = []
    for index, row in gdf.iterrows():
        # rough selection on index
        buffer_geom = row['geometry'].buffer(tolerance)
        # precise selection on distance < tolerance
        gdf_selec = gdf.iloc[list(sindex.intersection(buffer_geom.bounds))].copy()
        gdf_selec['distance'] = gdf_selec.distance(row['geometry'])
        gdf_selec = gdf_selec.loc[gdf_selec['distance'] < tolerance]
        # only snap to features that will not be modified
        gdf_selec = gdf_selec.loc[gdf_selec.index.isin(snapped)]
        # snapping to remaining objects
        geom = row['geometry']
        # round digits (optionally)
        if digits:
            geom = LineString([[round(coord, ndigits=digits) for
                               coord in coords] for coords in geom.coords])

        if not gdf_selec.empty:
            geom_coords = list(geom.coords)

            for _, row_selec in gdf_selec.iterrows():
                for dst_vert in [0, -1]:
                    for src_vert in [0, -1]:
                        geom_coords[dst_vert] = snap(
                            Point(geom_coords[dst_vert]),
                            Point(row_selec['geometry'].coords[src_vert]),
                            tolerance=1).coords[0]
            geom = LineString(geom_coords)
        # write feature in original GeoDataFrame
        gdf.loc[index, 'geometry'] = geom
        # mark index as snapped
        snapped += [index]

    return gdf


def filter_model(model, attribute_filter=None, geometry=None):
    """Filter a hydamo model on an attribute filter on branches."""
    drop_branches = []

    if attribute_filter:
        attribute_filter = {
            key.lower(): value for key, value in attribute_filter.items()}
        for key, value in attribute_filter.items():
            drop_branches += list(
                model.branches.loc[
                    model.branches[key] != value].index)

    if geometry:
        drop_branches += list(model.branches.loc[
            ~model.branches.intersects(geometry)].index)

    drop_branches = list(set(drop_branches))

    model.branches = model.branches.loc[~model.branches.index.isin(drop_branches)]
    for attribute in ATTRIBUTES:
        hydamo_class = getattr(model, attribute)
        if 'branch_id' in hydamo_class.columns:
            hydamo_class.set_data(hydamo_class.loc[
                ~hydamo_class['branch_id'].isin(drop_branches)],
                index_col="code",
                check_columns=True,
                check_geotype=True)

    return model


def export_shapes(model, path=Path('.')):
    """Export a hydamo class to shape-files."""
    path = Path(path)
    path.mkdir(exist_ok=True)
    for attribute in ATTRIBUTES:
        to_file(model, attribute, length=False, path=path)

    to_file(model, "branches", length=True, path=path)


def save_model(model, file_name=Path('model.pickle')):
    """Save the model as a pickle."""
    file_name = Path(file_name)
    parent = file_name.parent
    parent.mkdir(exist_ok=True)
    with open(file_name, 'wb') as dst:
        pickle.dump(model, dst, protocol=pickle.HIGHEST_PROTOCOL)


def load_model(file_name):
    """Load the model from a pickle."""
    with open(file_name, 'rb') as src:
        model = pickle.load(src)
    return model


def get_trapeziums(gdf,
                   index,
                   bottom_width,
                   bottom_level,
                   waterlevel_width,
                   slope_left,
                   slope_right,
                   roughnesstype,
                   roughnessvalue):
    """Return trapezium profiles for branches."""
    gdf = gdf.set_index(index)
    definitions = {}
    for idx, row in gdf.iterrows():
        slope = (row[slope_left] + row[slope_right]) / 2
        maximumflowwidth = row[waterlevel_width] + (2 * slope)
        bottomwidth = row[bottom_width]
        bottomlevel = row[bottom_level]
        definitions[idx] = dict(slope=slope,
                                bottomwidth=bottomwidth,
                                bottomlevel=bottomlevel,
                                maximumflowwidth=maximumflowwidth,
                                roughnesstype=row[roughnesstype],
                                roughnessvalue=row[roughnessvalue]
                                )
    return pd.DataFrame.from_dict(definitions, orient="index")


def add_trapeziums(dfmmodel, principe_profielen_bov_df, principe_profielen_ben_df, closed=False):
    """Add trapezium profiles on branches with missing crosssections."""
    #siebe 22-6-2021: nu twee dataframes: een voor bovenstrooms een voor benedenstoomse zijde tak
    xs = dfmmodel.crosssections
    for branch in xs.get_branches_without_crosssection():
    
        prof_def = _valid_pprof(dict(principe_profielen_bov_df.loc[branch]))
        chainage = 0.1
        definition = f"PPROUP_{branch}"        
        #siebe 22 juni 2022
        bottomlevel = prof_def["bottomlevel"]
        if not isnan(bottomlevel):
                    
            xs.add_crosssection_location(branch,
                                         chainage,
                                         definition+'_up',
                                         shift=prof_def["bottomlevel"]
                                         )

            xs.add_trapezium_definition(
                name=definition+'_up',
                slope=prof_def["slope"],
                maximumflowwidth=prof_def["maximumflowwidth"],
                bottomwidth=prof_def["bottomwidth"],
                closed=closed,
                roughnesstype=roughness_gml[int(prof_def["roughnesstype"])],
                roughnessvalue=float(prof_def["roughnessvalue"]))
        
        prof_def = _valid_pprof(dict(principe_profielen_ben_df.loc[branch]))
        chainage = dfmmodel.network.branches.loc[branch]['geometry'].length - 0.1
        definition = f"PPRODN_{branch}"        
        #siebe 22 juni 2022
        bottomlevel = prof_def["bottomlevel"]
        if not isnan(bottomlevel):
                    
            xs.add_crosssection_location(branch,
                                         chainage,
                                         definition+'_down',
                                         shift=prof_def["bottomlevel"]
                                         )
            xs.add_trapezium_definition(
                name=definition+'_down',
                slope=prof_def["slope"],
                maximumflowwidth=prof_def["maximumflowwidth"],
                bottomwidth=prof_def["bottomwidth"],
                closed=closed,
                roughnesstype=roughness_gml[int(prof_def["roughnesstype"])],
                roughnessvalue=float(prof_def["roughnessvalue"]))
        
        

    return dfmmodel


def filter_to_other_object(row, object_gdf, max_distance):
    """Filter HyDAMO-class-objects within distance to another object-class."""
    gdf = object_gdf.loc[
        object_gdf["geometry"].centroid.distance(row["geometry"]) < max_distance
        ]

    if not gdf.empty:
        gdf = gdf.loc[gdf["branch_id"] == row["branch_id"]]

    return gdf.empty

def move_end_nodes(branches_gdf, move_lines_gdf, threshold):
    #%% add start & end node of linestrings
    branches_gdf.loc[:, "start_node"] = branches_gdf["geometry"].apply(
        lambda x: Point(x.coords[0])
        )
    branches_gdf.loc[:, "end_node"] = branches_gdf["geometry"].apply(
        lambda x: Point(x.coords[-1])
        )
    
    #%% add start & end node of linestrings
    modified_rows = []
    for _, row in move_lines_gdf.iterrows():
        from_node = row["geometry"].coords[0]
        to_node = row["geometry"].coords[-1]
        from_poly = Point(from_node).buffer(threshold)
        
        # add to_node at beginning of LineString when start_node intersects from_node
        rows_select = branches_gdf[
            branches_gdf["start_node"].within(from_poly)
            ].index.to_list()
        branches_gdf.loc[rows_select, "geometry"] = branches_gdf.loc[
            rows_select, "geometry"
            ].apply(lambda x: LineString([to_node] + list(x.coords)))
        modified_rows += rows_select
    
        # extend LineString with to_node when start_node intersects to_node
        rows_select = branches_gdf[
            branches_gdf["end_node"].within(from_poly)
            ].index.to_list()
        branches_gdf.loc[rows_select, "geometry"] = branches_gdf.loc[
            rows_select, "geometry"
            ].apply(lambda x: LineString(list(x.coords) + [to_node]))
        modified_rows += rows_select
        
    #%% remove all lines with a length < treshold between new startand end_nodes
    branches_gdf.loc[modified_rows, "start_end_dist"] = branches_gdf.loc[
        modified_rows, "geometry"].apply(lambda x: Point(x.coords[0]).distance(Point(x.coords[-1])))
    
    branches_gdf = branches_gdf.loc[
        (branches_gdf["start_end_dist"] > threshold) | (branches_gdf["start_end_dist"].isna())]
    
    branches_gdf.drop(["start_node", "end_node", "start_end_dist"], axis=1, inplace=True)
    
    return branches_gdf
    
def _is_summer(datetime, summer_to_winter, winter_to_summer):

    if winter_to_summer.month < datetime.month < summer_to_winter.month:
        is_summer = True
    elif (datetime.month == winter_to_summer.month) and (datetime.day > winter_to_summer.day):
        is_summer = True
    elif (datetime.month == summer_to_winter.month) and (datetime.day < winter_to_summer.day):
        is_summer = True
    else:
        is_summer = False

    return is_summer
    
def generate_target_series(target_summer,
                           target_winter,
                           summer_to_winter=pd.Timestamp(year=1900, month=9, day=15),
                           winter_to_summer=pd.Timestamp(year=1900, month=3, day=15),
                           start_datetime=pd.Timestamp(year=1900, month=1, day=1),
                           end_datetime=pd.Timestamp(year=2100, month=1, day=1),
                           timedelta=pd.Timedelta(weeks=4)):
    timestamps = int(((end_datetime - start_datetime)/ timedelta) + 2.5)
    index = [start_datetime + timedelta * i for i in range(0,int(timestamps))]
    values = np.full(len(index), target_winter)
    summer_idx = [_is_summer(datetime, summer_to_winter, winter_to_summer) for datetime in index]
    values[summer_idx] = target_summer
    return pd.Series(values, index=index)