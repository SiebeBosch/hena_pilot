#!/usr/bin/env python
# coding: utf-8

# # D-Hydro De Dellen V1
# 
# ## Introductie
# 
# Met dit notebook bouw je een D-hydromodel voor Stroomgebied De Dellen in het beheergebied van waterschap Hunze en Aa's.
# 
# Zorg dat je beschikt over een werkende Python installatie en <a href="https://github.com/openearth/delft3dfmpy#installation">D-HYDAMO omgeving</a>. Het resulterende model moet geimporteerd kunnen worden in D-HYDRO versie 0.9.7.52006 of hoger.
# 
# De verwijzing naar bestanden is geschreven in het Nederlands. De rest van de code is geschreven in het Engels. Elk code-blok is voorzien van uitleg boven het desbetreffende blok, geschreven in het Nederlands.
# 
# Download de bestanden van <a href="https://www.dropbox.com/s/xzl38m1xyl9dqpc/beheerregister.zip?dl=0">Dropbox</a> en zet deze in de folder .\beheerregister

# ## Controle bestanden
# 
# Alle bestanden die gebruikt worden in deze tutorial staan in het code-blok hieronder. Wanneer je dit codeblok uitvoert wordt de aanwezigheid van deze bestanden gecontroleerd.
# 
# 

# In[6]:


from pathlib import Path

data_path = Path(r".\data").absolute().resolve()
excelbestanden = data_path.joinpath("xlsx")

#het pad naar beheerregister_adjusted bevat de bronbestanden die al obv Channel Builder oordeel zijn verbeterd
beheerregister = Path(r".\beheerregister_adjusted").absolute().resolve()

#het pad naar beheerregister bevat de bronbestanden in onveranderde vorm en dus nog hiaten en fouten bevatten
#beheerregister = Path(r".\beheerregister").absolute().resolve()

modelbestanden = {"randvoorwaarden":"randvoorwaarden.xlsx"}

invoerbestanden = {"modelgebied": "DeDellen_gebiedsgrens.shp",
                   "branches": "Hoofdwatergang_Dellen_singlepart.shp",
                   "profielpunten": "profielpunten_Dellen.shp",
                   "bruggen": "Brug_Dellen.shp",
                   "duikers": "Duiker_Dellen.shp",
                   "sifons": "Syphon_Dellen.shp",
                   "stuwen": "Stuw_Dellen.shp",
                   "inlaten": "Inlaat_Dellen.shp",
                   "gemalen": "Gemaal_Dellen.shp",
                   "peilgebieden": "Peilgebied_Dellen.shp"}

vorm_mapping = dict(rond=1,
                    driehoekig=1,
                    rechthoekig=3,
                    eivormig=1,
                    ellips=1,
                    Paraboolvormig=1,
                    trapeziumvormig=1,
                    heul=1,
                    muil=3,
                    langwerpig=1,
                    scherp=1,
                    onbekend=99,
                    overig=99)

ruwheid_mapping = {"A1": 0.03,
                   "A2": 0.03,
                   "A2 Boot": 0.03,
                   "A3": 0.03,
                   "B1": 0.02,
                   "B2": 0.022,
                   "C1": 0.02,
                   "C2b": 0.022,
                   "DERDEN": 0.03,
                   "GEEN": 0.07}

for key, item in invoerbestanden.items():
    if not beheerregister.joinpath(item).exists():
        print(f"bestand voor {key} bestaat niet: {beheerregister.joinpath(item)}")
        
for key, item in modelbestanden.items():
    if not excelbestanden.joinpath(item).exists():
        print(f"bestand voor {key} bestaat niet: {excelbestanden.joinpath(item)}")
        
print("Paden succesvol ingesteld.")


# ## Inlezen beheerregister in HyDAMO
# 
# ### Aanmaken HyDAMO object
# 
# Alle benodigde modules worden geimporteerd en het HYDAMO object wordt aangemaakt bij het uitvoeren van onderstaand code-blok

# In[8]:

import sys
sys.path.append(r'd:\GITHUB\DELFT3DFMPY_SB')

from delft3dfmpy import DFlowFMModel, HyDAMO, Rectangular, DFlowFMWriter
from delft3dfmpy import DFlowRRModel, DFlowRRWriter
from delft3dfmpy.datamodels.common import ExtendedGeoDataFrame
import hydrotools
import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

hydamo = HyDAMO(extent_file=str(beheerregister.joinpath(invoerbestanden["modelgebied"])))


# ### Toevoegen waterlopen
# 
# De waterlopen (branches) worden toegevoegd met volgend code-blok:
# * de branches worden toegekend aan het hydamo-object
# * een HyDAMO ruwheidscode (4 = manning) wordt toegekend
# * de eindpunten van de branches worden gesnapped binnen een tolerantie van 1m. De coordinaten worden ook afgerond op 1m.

# In[9]:


# gdf = gpd.read_file(beheerregister.joinpath(invoerbestanden["branches"]))
# gdf.columns = gdf.columns.str.lower()
# print(gdf.columns)

gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["branches"]),
                           hydamo_attribute="branches",
                           index_col="ovkident",
                           keep_columns=["code",
                                         "bodembreedte",
                                         "bodemhoogte_bov",
                                         "bodemhoogte_ben",
                                         "bovenbreedte",
                                         "taludhellinglinkerzijde",
                                         "avvtalur",
                                         "taludhellingrechterzijde",
                                         "werkcode",
                                         "objectid"],
                           column_mapping={"ovkident": "code",
                                           "avvboddr": "bodembreedte",
                                           "avvhobos": "bodemhoogte_bov",
                                           "avvhobes": "bodemhoogte_ben",
                                           "iws_bovenb": "bovenbreedte",
                                           "avvtalul": "taludhellinglinkerzijde",
                                           "avvtalur": "taludhellingrechterzijde"}
                           )

gdf.loc[:, "ruwheidstypecode"] = 2
gdf.loc[:, "ruwheidswaarde"] = gdf.apply((lambda x: ruwheid_mapping[x["werkcode"]]), axis=1)

#print(beheerregister.joinpath(invoerbestanden["branches"]))
#print("kolommen in geodataframe: " + gdf.columns)

#hydamo.branches = hydrotools.snap_ends(hydamo.branches, tolerance=1, digits=1)

# verplaatsen eindpunten
#move_lines_gdf = gpd.read_file(data_path.joinpath("shp","verplaats_eind_nodes.shp"))
#gdf = hydrotools.move_end_nodes(gdf, move_lines_gdf, threshold=1)

hydamo.branches.set_data(gdf, index_col="code", check_columns=True, check_geotype=True)

#hydamo.branches = hydrotools.snap_ends(hydamo.branches, tolerance=1, digits=1)

#hydamo.branches = hydamo.branches.loc[~hydamo.branches.index.isin(["OAF016902",
 #                                                                  "OAF016901"])]


# ### Toevoegen yz-profielen
# De yz-profielen worden ingeladen:
# * De profielpunten worden geopend
# * de punten worden geordend en geconverteerd naar polylinen met een xyz coordinaten
# * toekennen ruwheid (manning = 35)
# * lijnen langer dan 500m worden weggegooid, omdat er soms kademuren PRO_TYPE = PRO hebben gekregen
# * lijnen worden toegekend aan het HyDAMO object
# * lijnen die niet snappen met de branches, worden weggegooid
# 
# ToDo:
# * verbeteren toekenning ruwheid

# In[10]:


principe_profielen_bov_df = hydrotools.get_trapeziums(gdf,
                                                  "code",
                                                  "bodembreedte",
                                                  "bodemhoogte_bov",
                                                  "bovenbreedte",
                                                  "taludhellinglinkerzijde",
                                                  "taludhellingrechterzijde",
                                                  "ruwheidstypecode",
                                                  "ruwheidswaarde")

principe_profielen_ben_df = hydrotools.get_trapeziums(gdf,
                                                  "code",
                                                  "bodembreedte",
                                                  "bodemhoogte_ben",
                                                  "bovenbreedte",
                                                  "taludhellinglinkerzijde",
                                                  "taludhellingrechterzijde",
                                                  "ruwheidstypecode",
                                                  "ruwheidswaarde")

principe_profielen_bov_df.to_csv(excelbestanden.joinpath("principe_profielen_bovenstrooms.csv"))
principe_profielen_ben_df.to_csv(excelbestanden.joinpath("principe_profielen_benedenstrooms.csv"))

# In[5]:


gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["profielpunten"]),
                           "crosssections",
                           attribute_filter={"osmomsch": ["Z1"]},  #we nemen alleen profielen van het type Z1 (vaste bodem) 
                           column_mapping={"CODE": "code",
                                           "IWS_VOLGNR": "order",
                                           "OSMOMSCH": "category",
                                           "iws_hoogte": "z"},
                           z_coord=True
                           )
print(gdf["code"])
grouper = gdf.groupby("code")
profiles = dict()

for code, prof_gdf in grouper:
    if len(prof_gdf) > 1: 
        prof_gdf = prof_gdf.sort_values("order")  #Staan ook punten met zelfde order
        first_point = prof_gdf.iloc[0]["geometry"]
        cum_dist = -1
        line = []
        for idx, (_, row) in enumerate(prof_gdf.iterrows()):
            geom = row["geometry"]
            distance = geom.distance(first_point)
            if distance > cum_dist:
                cum_dist = distance
                line += [(geom.x, geom.y, row["z"])]

        profiles[code] = [code, LineString(line)]
    else:
        print(f"Waarschuwing: {code} bevat slechts één punt")
profiles_gdf = gpd.GeoDataFrame.from_dict(profiles,
                                          orient="index",
                                          columns=["code",
                                                   "geometry"]
                                          )

profiles_gdf["ruwheidstypecode"] = 4
profiles_gdf["ruwheidswaarde"] = 35
profiles_gdf["codegerelateerdobject"] = None

profiles_gdf = profiles_gdf.loc[profiles_gdf["geometry"].length < 500]

hydamo.crosssections.set_data(profiles_gdf,
                              index_col="code",
                              check_columns=True,
                              check_geotype=True)

hydamo.crosssections.snap_to_branch(hydamo.branches, snap_method="intersecting")
hydamo.crosssections.dropna(axis=0, inplace=True, subset=["branch_offset"])

# ### Toevoegen bruggen
# Per brug moet er een profiel worden toegevoegd

# In[6]:


gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["bruggen"]),
                           "parametrised_profiles",
                           column_mapping={
                                           "KBRIDENT":"code",
                                           "KBRBHBO": "bodemhoogtebovenstrooms",
                                           "KBRBHBE": "bodemhoogtebenedenstrooms",
                                           "KBRBREED": "bodembreedte",
                                           "KBRHOBO": "hoogteinsteeklinkerzijde",
                                           })

grouper = gdf.groupby("code")
data = {"code": [code for code, frame in grouper],
        "bodemhoogtebovenstrooms": [frame["bodemhoogtebovenstrooms"].values[0]
                                    for code, frame in grouper],
        "bodemhoogtebenedenstrooms": [frame["bodemhoogtebenedenstrooms"].values[0]
                                      for code, frame in grouper],
        "bodembreedte": [frame["bodembreedte"].values[0]
                         for code, frame in grouper],
        "hoogteinsteeklinkerzijde": [frame["hoogteinsteeklinkerzijde"].values[0]
                                     for code, frame in grouper],
        "geometry": [frame["geometry"].values[0] for code, frame in grouper]
        }

gdf = gpd.GeoDataFrame(data)
gdf["geometry"] = gdf.apply((lambda x: LineString([[x["geometry"].x,
                                                    x["geometry"].y],
                                                  [x["geometry"].x+1,
                                                   x["geometry"].y+1]])),
                            axis=1)

gdf["codegerelateerdobject"] = gdf["code"].copy()
gdf["code"] = [f"PRO_{code}" for code in gdf["code"]]
gdf["hoogteinsteekrechterzijde"] = gdf["hoogteinsteeklinkerzijde"]
gdf["ruwheidswaarde"] = 15
gdf["ruwheidstypecode"] = 4
gdf["taludhellinglinkerzijde"] = 1
gdf["taludhellingrechterzijde"] = 1

#vervang nan-waarde voor bodembreedte door  defaultwaarde 1
gdf.loc[gdf["bodembreedte"].isna(), "bodembreedte"] = 1

hydamo.parametrised_profiles.set_data(gdf,
                                      index_col="code",
                                      check_columns=True,
                                      check_geotype=False)

# ### Toevoegen duikers en siphons
# duikers en sifons worden als cuverts aan het HyDAMO object toegekend
# 
# ToDo
# * vorm moet naar HyDAMO codering worden omgeschreven

# In[7]:


gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["bruggen"]),
                           "bridges",
                           column_mapping={
                                           "KBRIDENT":"code",
                                           "KBRLENGT": "lengte",
                                           "KBRHOBO": "hoogtebovenzijde",
                                           "KBRBHBO": "hoogteonderzijde"})

grouper = gdf.groupby("code")
data = {"code": [code for code, frame in grouper],
        "hoogteonderzijde": [frame["hoogteonderzijde"].values[0] for code, frame in grouper],
        "hoogtebovenzijde": [frame["hoogtebovenzijde"].values[0] for code, frame in grouper], 
        "lengte": [frame["lengte"].values[0] for code, frame in grouper],
        "geometry": [frame["geometry"].values[0] for code, frame in grouper]
        }
gdf = gpd.GeoDataFrame(data)

#gdf["hoogtebovenzijde"] = gdf["hoogteonderzijde"] + 1

gdf["dwarsprofielcode"] = gdf["code"]
gdf["intreeverlies"] = 0.7
gdf["uittreeverlies"] = 0.7
gdf["ruwheidstypecode"] = 4
gdf["ruwheidswaarde"] = 70

hydamo.bridges.set_data(gdf, index_col="code", check_columns=True, check_geotype=False)
hydamo.bridges.snap_to_branch(hydamo.branches, snap_method="overal", maxdist=5)
hydamo.bridges.dropna(axis=0, inplace=True, subset=["branch_offset"])
print("Aantal bruggen binnen snapping distance: " + str(len(hydamo.bridges)))
hydamo.bridges.dropna(axis=0, inplace=True, subset=["hoogteonderzijde"])
print("Aantal bruggen toegevoegd aan het model: " + str(len(hydamo.bridges)))


# ### Toevoegen stuwen

# In[8]:


culverts_gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["duikers"]),
                                    "culverts",
                                    column_mapping={
                                                    "KDUIDENT": "code",
                                                    "KDULENGT": "lengte",
                                                    "KDUHGA1": "hoogteopening",
                                                    "KDUBREED": "breedteopening",
                                                    "KDUBOKBE": "hoogtebinnenonderkantbenedenstrooms",
                                                    "KDUBOKBO": "hoogtebinnenonderkantbovenstrooms",
                                                    "KDUVORM": "vormcode"})

siphons_gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["sifons"]),
                                   "culverts",
                                   column_mapping={
                                                   "KSYIDENT": "code",
                                                   "IWS_LENGTE": "lengte",
                                                   "KSYHGA1": "hoogteopening",
                                                   "KSYBREED": "breedteopening",
                                                   "IWS_HBOKBE":"hoogtebinnenonderkantbenedenstrooms",
                                                   "IWS_HBOKBO":"hoogtebinnenonderkantbovenstrooms",
                                                   "KSYVORM":"vormcode"})

gdf = gpd.GeoDataFrame(pd.concat([culverts_gdf,siphons_gdf], ignore_index=True))

gdf.loc[gdf['vormcode'].isnull(), 'vormcode'] = 'onbekend'
gdf.loc[:, 'vormcode'] = gdf.apply((lambda x: vorm_mapping[x['vormcode'].lower()]), axis=1)

gdf["intreeverlies"] = 0.7
gdf["uittreeverlies"] = 0.7
gdf["ruwheidswaarde"] = 70
gdf["ruwheidstypecode"] = 4

hydamo.culverts.set_data(gdf, index_col="code", check_columns=True, check_geotype=True)
hydamo.culverts.snap_to_branch(hydamo.branches, snap_method="ends", maxdist=5)

print("Number of culverts in datasource is " + str(len(hydamo.culverts)))
hydamo.culverts.dropna(axis=0, inplace=True, subset=["branch_offset"])
print("Number of culverts withing snapping range is " + str(len(hydamo.culverts)))
hydamo.culverts.dropna(axis=0, inplace=True, subset=["hoogtebinnenonderkantbovenstrooms"])
hydamo.culverts.dropna(axis=0, inplace=True, subset=["hoogtebinnenonderkantbenedenstrooms"])
print("Number of culverts written to model is " + str(len(hydamo.culverts)))

hydamo.culverts.loc[hydamo.culverts["hoogteopening"].isna(), "hoogteopening"] = 0.5
hydamo.culverts.loc[hydamo.culverts["breedteopening"].isna(), "breedteopening"] = 0.5
hydamo.culverts.loc[hydamo.culverts["lengte"].isna(), "lengte"] = 20



# ### Toevoegen gemalen

# In[9]:


gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["stuwen"]),
                           "weirs",
                           column_mapping={"kstident": "code",
                                           "kstsoort": "soortstuwcode",
                                           "kstkrubr": "laagstedoorstroombreedte",
                                           "kstmikho": "laagstedoorstroomhoogte",
                                           "kstregel": "soortregelbaarheidcode"})

gdf["afvoercoefficient"] = 1

hydamo.weirs.set_data(gdf, index_col="code", check_columns=True, check_geotype=True)
hydamo.weirs.snap_to_branch(hydamo.branches, snap_method="overal", maxdist=10)
hydamo.weirs.dropna(axis=0, inplace=True, subset=["branch_offset"])


# ### Toevoegen afsluitmiddelen

# In[10]:


pumps_gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["gemalen"]),
                                 "pumps",
                                 column_mapping={
                                     "KGMIDENT": "code",
                                     "KGMMACAP": "maximalecapaciteit"})

gemalen_gdf = pumps_gdf.copy()
pumps_gdf["codegerelateerdobject"] = pumps_gdf["code"].copy()
pumps_gdf["code"] = [f"PMP_{code}" for code in pumps_gdf["code"]]
hydamo.gemalen.set_data(gemalen_gdf,
                        index_col="code",
                        check_columns=True,
                        check_geotype=True)
hydamo.gemalen.snap_to_branch(hydamo.branches, snap_method="overal", maxdist=5)
hydamo.gemalen.dropna(axis=0, inplace=True, subset=["branch_offset"])
hydamo.pumps.set_data(pumps_gdf,
                      index_col="code",
                      check_columns=True,
                      check_geotype=True)
hydamo.pumps.snap_to_branch(hydamo.branches, snap_method="overal", maxdist=5)
hydamo.pumps.dropna(axis=0, inplace=True, subset=["branch_offset"])


# ### Toevoegen sturing

# In[11]:


gdf = pd.DataFrame({"code": [],
                    "soortafsluitmiddelcode": [],
                    "codegerelateerdobject": []})

hydamo.afsluitmiddel.set_data(gdf, index_col="code")


# ### Filteren
# 
# Alle branches die niet bij "Boezemmodel_v4" gooien we uit het model. Idem voor alle kunstwerken + profielen die naar deze branches zijn gesnapped. Om het resultaat te beoordelen exporteren we alles naar shape-files. We slaan het hydamo object ook op als "pickle", zodat we bovenstaande stappen niet elke keer hoeven te herhalen

# In[12]:


gpg_gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["peilgebieden"]),
                                 "sturing",
                                 column_mapping={"GPGIDENT": "code",
                                                 "GPGZMRPL": "streefwaarde"
                                                 })

gpg_gdf["codegerelateerdobject"] = [code.replace("GPG", "") for code in gpg_gdf["code"]]
gpg_gdf = gpg_gdf[gpg_gdf["codegerelateerdobject"].isin(hydamo.gemalen["code"])]
con_gdf = hydamo.gemalen[~hydamo.gemalen["code"].isin(gpg_gdf["codegerelateerdobject"])]
con_gdf = gpd.GeoDataFrame(data={"code": con_gdf["code"].values,
                                 "geometry": con_gdf["geometry"].values})
con_gdf["codegerelateerdobject"] = con_gdf["code"]
con_gdf["streefwaarde"] = -999

gdf = gpd.GeoDataFrame(pd.concat([gpg_gdf, con_gdf], ignore_index=True))

gdf["bovenmarge"] = gdf["streefwaarde"] + 0.05
gdf["ondermarge"] = gdf["streefwaarde"] - 0.05
gdf["doelvariabelecode"] = 1

hydamo.sturing.set_data(gdf, index_col="code")

# ## Converteren naar DFM
# 
# ### Aanmaken dfm-klasse

# In[13]:


hydamo = hydrotools.filter_model(hydamo, attribute_filter={"OBJECTID": 1})
#hydrotools.export_shapes(hydamo, path=Path(r"./hydamo_shp/dellen"))
hydrotools.save_model(hydamo, file_name=Path(r"./hydamo_model/dellen.pickle"))


# ### Inlezen kunstwerken

# In[14]:


dfmmodel = DFlowFMModel()
drrmodel = DFlowRRModel()

# ### Aanmaken 1d netwerk

# In[15]:


dfmmodel.structures.io.weirs_from_hydamo(hydamo.weirs,
                                         yz_profiles=hydamo.crosssections,
                                         parametrised_profiles=hydamo.parametrised_profiles)

dfmmodel.structures.io.culverts_from_hydamo(hydamo.culverts,
                                            hydamo.afsluitmiddel)

dfmmodel.structures.io.bridges_from_hydamo(hydamo.bridges,
                                           yz_profiles=hydamo.crosssections,
                                           parametrised_profiles=hydamo.parametrised_profiles)

for lateral in hydamo.laterals.itertuples():
    dfmmodel.external_forcings.laterals[lateral.code] = {
        'branchid': lateral.branch_id,
        'branch_offset':str(lateral.branch_offset)
    }
    drrmodel.external_forcings.add_boundary_node(lateral.code, lateral.X, lateral.Y)


dfmmodel.structures.io.orifices_from_hydamo(hydamo.orifices)

dfmmodel.structures.io.pumps_from_hydamo(pompen=hydamo.pumps,
                                         sturing=hydamo.sturing,
                                         gemalen=hydamo.gemalen)

# In[16]
dfmmodel.network.set_branches(hydamo.branches)
dfmmodel.network.generate_1dnetwork(one_d_mesh_distance=100.0, seperate_structures=True)





# In[17]:
# ### Toevoegen cross-sections

dfmmodel.crosssections.io.from_hydamo(
    dwarsprofielen=hydamo.crosssections,
    parametrised=hydamo.parametrised_profiles,
    branches=hydamo.branches
)

print(f"{len(dfmmodel.crosssections.get_branches_without_crosssection())} branches are still missing a cross section.")
print(f"{len(dfmmodel.crosssections.get_structures_without_crosssection())} structures are still missing a cross section.")


# ## Importeren in de D-Hydro suite
# 
# Open het model nu in D-Hydro:
# 1. Open een "Empty Project"
# 2. In de "Home" ribbon, ga naar "Import" en selecteer "Flow Flexible Mesh Model"
# 3. Selecteer het bestand "boezemmodel.mdu" in ".\dfm_model\fm\boezemmodel.mdu"
# 4. Wacht tot het model is geimporteerd.....
# 
# Het geimporteerde model is nu zichtbaar in de D-Hydro suite
# <img src="png/boezemmodel.png"/>

# In[18]:
if len(dfmmodel.crosssections.get_branches_without_crosssection()) > 0:        
    print("adding trapezium profiles on branches with missing crosssections.")
    #siebe 22-6-2022: onderscheid boven- en benedenstrooms profiel. Vanaf nu twee dataframes meegeven
    # Bram 4-7-2021 maximum Flowwidth wordt 300 in output met closed=False!? -> closed=True
    dfmmodel = hydrotools.add_trapeziums(dfmmodel, principe_profielen_bov_df, principe_profielen_ben_df, False)

print(f"{len(dfmmodel.crosssections.get_branches_without_crosssection())} number of branches remain with no cross section due to missing data.")

# In[19]:

# Bram 4-7-2021: Ronde profielen werkt niet -> Ook in GUI lukt het niet 
# om de dwarsdoorsnede door validatie heen te krijgen.
# Verder lijkt D-FM moeite te hebben met gedeelte dwarsprofielen ('shared definitions')
# Deze routine maakt daarom unieke definities aan per dwarsdoorsnede locatie

crs_def_id = 0 # start uniek ID dwarsdoorsnede definitie

# loop door branches_id's met missende crs
for branch_id in dfmmodel.crosssections.get_branches_without_crosssection(): 
    
    # als de branch in de culvert branch lijst staat (branch heeft culvert)
    if branch_id in hydamo.culverts.branch_id.to_list(): 

        culvert_idx = hydamo.culverts.branch_id.to_list().index(branch_id) # index location van de duiker (niet nodig?)
        culvert = hydamo.culverts.iloc[[culvert_idx]]
        
        # lengtes van duiker en watergang
        culvert_length = culvert['lengte'][0]
        branch_length = dfmmodel.network.branches.geometry[branch_id].length
        
        if culvert_length > 0.5 * branch_length: # check of de duiker meer dan 50% van de watergang beslaat
        
            # get culvert attributes
            culvert_diameter = culvert['hoogteopening'][0]
            roughnesstype = int(culvert['ruwheidstypecode'][0])
            roughness = culvert['ruwheidswaarde'][0]
            bob_boven = round(culvert['hoogtebinnenonderkantbovenstrooms'][0],3)
            bob_beneden = round(culvert['hoogtebinnenonderkantbenedenstrooms'][0],3)

            # maak unieke namen voor dwarsdoorsnede profiel definities
            crs_def_boven_name = f'rect_{crs_def_id}'
            crs_def_beneden_name = f'rect_{crs_def_id+1}'
            crs_def_id += 2

            # Voeg vierkante profiel definities toe
            dfmmodel.crosssections.add_rectangle_definition(name= crs_def_boven_name, 
                                                         height = culvert_diameter, 
                                                         width = culvert_diameter, 
                                                         closed = False,
                                                         roughnesstype = roughnesstype, 
                                                         roughnessvalue = roughness)
            
            dfmmodel.crosssections.add_rectangle_definition(name= crs_def_beneden_name, 
                                                         height = culvert_diameter, 
                                                         width = culvert_diameter, 
                                                         closed = False,
                                                         roughnesstype = roughnesstype, 
                                                         roughnessvalue = roughness)


            # Voeg dwarsdoorsnede locaties toe
            dfmmodel.crosssections.add_crosssection_location(branchid = branch_id, 
                                                             chainage = 0.1, 
                                                             definition = crs_def_boven_name, 
                                                             shift = bob_boven)
            
            dfmmodel.crosssections.add_crosssection_location(branchid = branch_id,
                                                             chainage = round((branch_length-0.1),4), 
                                                             definition = crs_def_beneden_name, 
                                                             shift = bob_beneden)

            print(f'added crs for branch {branch_id} based on culvert {culvert["code"][0]}')

print(f"{len(dfmmodel.crosssections.get_branches_without_crosssection())} number of branches remain with no cross section due to missing data.")
print('Still missing:', '\n'.join(dfmmodel.crosssections.get_branches_without_crosssection()))

## if branch contains culvert
## if abs(length(branch) - (length(culvert))) <= 100 then
##    we zitten in een kunstwerkvak
##    maak rond profiel conform duikerprofile
##    push rond profile naar dfmodel middels een dataframe


# In[20]:
emptybranches = dfmmodel.crosssections.get_branches_without_crosssection()
print("Branches before removing branches without cross sections: " + str(len(dfmmodel.network.branches)))

#for emptybranch in emptybranches:
#    if emptybranch not in hydamo.culverts.branch_id.to_list() + hydamo.weirs.branch_id.to_list():
#        hydamo.branches.drop(emptybranch, inplace=True)
#        dfmmodel.network.branches.drop(emptybranch, inplace=True)
    
#emptybranches = dfmmodel.crosssections.get_branches_without_crosssection()
print("Branches after removing: " + str(len(dfmmodel.network.branches)))

#dfmmodel.network.set_branches(hydamo.branches)
#dfmmodel.network.generate_1dnetwork(one_d_mesh_distance=100.0, seperate_structures=True)


# In[21]:
rvw_df = pd.read_excel(excelbestanden.joinpath(modelbestanden["randvoorwaarden"]))

for _,row in rvw_df.iterrows():
    branch_id = row["BRANCH_ID"]
    pt = hydamo.branches.loc[branch_id]["geometry"].coords[int(row["COORD"])]
    series = pd.Series(data=[-4.0, -4.0],
                       index=[pd.Timestamp("2000-01-01"),
                              pd.Timestamp("2100-01-01")]
                       )

# In[22]:

dimr_path = r"c:\Program Files (x86)\Deltares\D-HYDRO Suite 1D2D (Beta) (0.9.9.52575)\plugins\DeltaShell.Dimr\kernels\x64\dimr\scripts\run_dimr.bat"
start_datetime = pd.Timestamp('2000-01-01 00:00:00')
end_datetime = start_datetime + pd.Timedelta(days=6)

dfmmodel.mdu_parameters["refdate"] = int(start_datetime.strftime("%Y%m%d"))
dfmmodel.mdu_parameters["tstart"] = 0.0 * 3600
dfmmodel.mdu_parameters["tstop"] = 10 * 24 * 3600
dfmmodel.mdu_parameters["hisinterval"] = "600. 0. 0."
dfmmodel.mdu_parameters["mapinterval"] = "600. 0. 0."
dfmmodel.mdu_parameters["wrirst_bnd"] = 0
dfmmodel.mdu_parameters["cflmax"] = 0.7
dfmmodel.mdu_parameters["outputdir"] = "output_initialisatie"
dfmmodel.dimr_path = dimr_path

fm_writer = DFlowFMWriter(dfmmodel, output_dir=r"dellen", name="dellen")

fm_writer.objects_to_ldb()
fm_writer.write_all()

drrmodel.d3b_parameters['Timestepsize'] = 300
drrmodel.d3b_parameters['StartTime'] = start_datetime.strftime("%Y/%m/%d;%H:%M:%S") # should be equal to refdate for D-HYDRO
drrmodel.d3b_parameters['EndTime'] = end_datetime.strftime("%Y/%m/%d;%H:%M:%S")
drrmodel.d3b_parameters['RestartIn'] = 0
drrmodel.d3b_parameters['RestartOut'] = 0
drrmodel.d3b_parameters['RestartFileNamePrefix'] ='Test'
drrmodel.d3b_parameters['UnsaturatedZone'] = 1
drrmodel.d3b_parameters['UnpavedPercolationLikeSobek213']=-1
drrmodel.d3b_parameters['VolumeCheckFactorToCF']=100000
drrmodel.dimr_path = dimr_path

rr_writer = DFlowRRWriter(drrmodel,
                          output_dir=r"dellen",
                          name="dellen")
rr_writer.write_coupling()


# In[23]:


#dfmmodel.mdu_parameters["refdate"] = 20000101
#dfmmodel.mdu_parameters["tstart"] = 0.0 * 3600
#dfmmodel.mdu_parameters["tstop"] = 144.0 * 1 * 3600
#dfmmodel.mdu_parameters["hisinterval"] = "120. 0. 0."
#dfmmodel.mdu_parameters["cflmax"] = 0.7


#dimr_path = r"dummypath\run_dimr.bat"
#dfmmodel.dimr_path = dimr_path
#fm_writer = DFlowFMWriter(dfmmodel, output_dir="dellen", name="dellen")

#fm_writer.objects_to_ldb()
#fm_writer.write_all()



if Path(r".\dellen\fm\dellen.mdu").exists():
    print("Model is weggeschreven")
else:
    print("Er is geen model geschreven. Waarschijnlijk is iets fout gegaan")

# In[ ]:




# In[ ]:




# In[ ]:



