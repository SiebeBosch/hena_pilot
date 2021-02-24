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

beheerregister = Path(r".\beheerregister").absolute().resolve()

invoerbestanden = {"modelgebied": "DeDellen_gebiedsgrens.shp",
                   "branches": "Hoofdwatergang_Dellen_singlepart.shp",
                   "profielpunten": "profielpunten_Dellen.shp",
                   "bruggen": "Brug.shp",
                   "duikers": "Duiker_Dellen.shp",
                   "sifons": "Syphon.shp",
                   "stuwen": "Stuw.shp",
                   "inlaten": "Inlaat.shp",
                   "gemalen": "Gemaal.shp",
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

for key, item in invoerbestanden.items():
    if not beheerregister.joinpath(item).exists():
        print(f"bestand voor {key} bestaat niet: {beheerregister.joinpath(item)}")
print("Paden succesvol ingesteld.")


# ## Inlezen beheerregister in HyDAMO
# 
# ### Aanmaken HyDAMO object
# 
# Alle benodigde modules worden geimporteerd en het HYDAMO object wordt aangemaakt bij het uitvoeren van onderstaand code-blok

# In[8]:


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


gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["branches"]),"branches",keep_columns=["IMGEOBRONH"],column_mapping={"OVKIDENT": "code"},)

hydamo.branches.set_data(gdf, index_col="code", check_columns=True, check_geotype=True)
hydamo.branches["ruwheidstypecode"] = 4

hydamo.branches = hydrotools.snap_ends(hydamo.branches, tolerance=1, digits=1)


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


gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["profielpunten"]),"crosssections",attribute_filter={"osmomsch": ["Z1"]},column_mapping={"CODE": "code","IWS_VOLGNR": "order","OSMOMSCH": "category","iws_hoogte": "z"},z_coord=True)

grouper = gdf.groupby("code")
profiles = dict()

for code, prof_gdf in grouper:
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

    if len(line) > 3:    
        profiles[code] = [code, LineString(line)]
    else:
        print(f"profiel met id {code} heeft maar {len(line)} coordinaat/coordinaten en wordt niet meegenomen")

profiles_gdf = gpd.GeoDataFrame.from_dict(profiles,orient="index",columns=["code","geometry"])

profiles_gdf["ruwheidstypecode"] = 4
profiles_gdf["ruwheidswaarde"] = 35
profiles_gdf["codegerelateerdobject"] = None

profiles_gdf = profiles_gdf.loc[profiles_gdf["geometry"].length < 500]

hydamo.crosssections.set_data(profiles_gdf,index_col="code",check_columns=True,check_geotype=True)

hydamo.crosssections.snap_to_branch(hydamo.branches, snap_method="intersecting")
hydamo.crosssections.dropna(axis=0, inplace=True, subset=["branch_offset"])


# ### Toevoegen geparameteriseerde profielen
# 
# Per brug moet er een profiel worden toegevoegd

# In[5]:


gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["bruggen"]),"parametrised_profiles",column_mapping={"OBJECTIDEN": "code", "KBRBHBO": "bodemhoogtebovenstrooms","KBRBHBE": "bodemhoogtebenedenstrooms","KBRBREED": "bodembreedte","KBRHOBO": "hoogteinsteeklinkerzijde",})

grouper = gdf.groupby("code")
data = {"code": [code for code, frame in grouper],"bodemhoogtebovenstrooms": [frame["bodemhoogtebovenstrooms"].values[0] for code, frame in grouper],"bodemhoogtebenedenstrooms": [frame["bodemhoogtebenedenstrooms"].values[0] for code, frame in grouper],"bodembreedte": [frame["bodembreedte"].values[0] for code, frame in grouper],"hoogteinsteeklinkerzijde": [frame["hoogteinsteeklinkerzijde"].values[0] for code, frame in grouper],"geometry": [frame["geometry"].values[0] for code, frame in grouper]}

gdf = gpd.GeoDataFrame(data)
gdf["geometry"] = gdf.apply((lambda x: LineString([[x["geometry"].x, x["geometry"].y], [x["geometry"].x+1, x["geometry"].y+1]])), axis=1)

gdf["codegerelateerdobject"] = gdf["code"].copy()
gdf["code"] = [f"PRO_{code}" for code in gdf["code"]]
gdf["hoogteinsteekrechterzijde"] = gdf["hoogteinsteeklinkerzijde"]
gdf["ruwheidswaarde"] = 15
gdf["ruwheidstypecode"] = 4
gdf["taludhellinglinkerzijde"] = 1
gdf["taludhellingrechterzijde"] = 1

hydamo.parametrised_profiles.set_data(gdf,index_col="code",check_columns=True,check_geotype=False)


# ### Toevoegen bruggen
# Per brug moet er een profiel worden toegevoegd

# In[6]:


gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["bruggen"]),"bridges",column_mapping={"OBJECTIDEN":"code","KBRLENGT": "lengte","KBRHOBO": "hoogteonderzijde"})

grouper = gdf.groupby("code")
data = {"code": [code for code, frame in grouper], "hoogteonderzijde": [frame["hoogteonderzijde"].values[0] for code, frame in grouper], "lengte": [frame["lengte"].values[0] for code, frame in grouper],"geometry": [frame["geometry"].values[0] for code, frame in grouper]}
gdf = gpd.GeoDataFrame(data)

gdf["hoogtebovenzijde"] = gdf["hoogteonderzijde"] + 1

gdf["dwarsprofielcode"] = gdf["code"]
gdf["intreeverlies"] = 0.7
gdf["uittreeverlies"] = 0.7
gdf["ruwheidstypecode"] = 4
gdf["ruwheidswaarde"] = 70

hydamo.bridges.set_data(gdf, index_col="code", check_columns=True, check_geotype=False)
hydamo.bridges.snap_to_branch(hydamo.branches, snap_method="overal", maxdist=5)
hydamo.bridges.dropna(axis=0, inplace=True, subset=["branch_offset"])


# ### Toevoegen duikers en siphons
# duikers en sifons worden als cuverts aan het HyDAMO object toegekend
# 
# ToDo
# * vorm moet naar HyDAMO codering worden omgeschreven

# In[7]:


culverts_gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["duikers"]),"culverts",column_mapping={"KDUIDENT":"code","KDULENGT":"lengte","KDUHGA1": "hoogteopening","KDUBREED": "breedteopening","KDUBOKBE": "hoogtebinnenonderkantbenedenstrooms","KDUBOKBO": "hoogtebinnenonderkantbovenstrooms","KDUVORM": "vormcode"})
#gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["duikers"]),"culverts",column_mapping={"KDUIDENT":"code","KDULENGT":"lengte","KDUHGA1": "hoogteopening","KDUBREED": "breedteopening","KDUBOKBE": "hoogtebinnenonderkantbenedenstrooms","KDUBOKBO": "hoogtebinnenonderkantbovenstrooms","KDUVORM": "vormcode"})

siphons_gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["sifons"]),"culverts",column_mapping={"OBJECTIDEN":"code","KSYBREED_L":"diameter","KSYHGA1_L":"hoogteopening","KSYBREED_L": "breedteopening","IWS_HBOKBO":"hoogtebinnenonderkantbenedenstrooms","IWS_HBOKBE":"hoogtebinnenonderkantbovenstrooms","vorm":"vormcode"})
gdf = gpd.GeoDataFrame(pd.concat([culverts_gdf,siphons_gdf], ignore_index=True))


gdf.loc[gdf['vormcode'].isnull(), 'vormcode'] = 'onbekend'
gdf.loc[:, 'vormcode'] = gdf.apply((lambda x: vorm_mapping[x['vormcode'].lower()]), axis=1)

gdf["intreeverlies"] = 0.7
gdf["uittreeverlies"] = 0.7
gdf["ruwheidswaarde"] = 70
gdf["ruwheidstypecode"] = 4

hydamo.culverts.set_data(gdf, index_col="code", check_columns=True, check_geotype=True)
hydamo.culverts.snap_to_branch(hydamo.branches, snap_method="ends", maxdist=5)
hydamo.culverts.dropna(axis=0, inplace=True, subset=["branch_offset"])

hydamo.culverts.loc[hydamo.culverts["lengte"].isna(), "lengte"] = 20


# ### Toevoegen stuwen

# In[8]:


gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["stuwen"]),"weirs",column_mapping={"KSTIDENT": "code","KSTSOORT": "soortstuwcode","KSTKRUBR": "laagstedoorstroombreedte","KSTMIKHO": "laagstedoorstroomhoogte","KSTREGEL": "soortregelbaarheidcode"})

gdf["afvoercoefficient"] = 1

hydamo.weirs.set_data(gdf, index_col="code", check_columns=True, check_geotype=True)
hydamo.weirs.snap_to_branch(hydamo.branches, snap_method="overal", maxdist=10)
hydamo.weirs.dropna(axis=0, inplace=True, subset=["branch_offset"])


# ### Toevoegen gemalen

# In[9]:


pumps_gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["gemalen"]),"pumps",column_mapping={"KGMIDENT":"code","KGMMACAP": "maximalecapaciteit"})

gemalen_gdf = pumps_gdf.copy()
pumps_gdf["codegerelateerdobject"] = pumps_gdf["code"].copy()
pumps_gdf["code"] = [f"PMP_{code}" for code in pumps_gdf["code"]]
hydamo.gemalen.set_data(gemalen_gdf,index_col="code",check_columns=True,check_geotype=True)
hydamo.gemalen.snap_to_branch(hydamo.branches, snap_method="overal", maxdist=5)
hydamo.gemalen.dropna(axis=0, inplace=True, subset=["branch_offset"])
hydamo.pumps.set_data(pumps_gdf,index_col="code",check_columns=True,check_geotype=True)
hydamo.pumps.snap_to_branch(hydamo.branches, snap_method="overal", maxdist=5)
hydamo.pumps.dropna(axis=0, inplace=True, subset=["branch_offset"])


# ### Toevoegen afsluitmiddelen

# In[10]:


gdf = pd.DataFrame({"code": [],"soortafsluitmiddelcode": [],"codegerelateerdobject": []})

hydamo.afsluitmiddel.set_data(gdf, index_col="code")


# ### Toevoegen sturing

# In[11]:


gpg_gdf = hydrotools.read_file(beheerregister.joinpath(invoerbestanden["peilgebieden"]),"sturing",column_mapping={"GPGIDENT": "code","GPGWNTPL": "streefwaarde"})

gpg_gdf["codegerelateerdobject"] = [code.replace("GPG", "") for code in gpg_gdf["code"]]
gpg_gdf = gpg_gdf[gpg_gdf["codegerelateerdobject"].isin(hydamo.gemalen["code"])]
con_gdf = hydamo.gemalen[~hydamo.gemalen["code"].isin(gpg_gdf["codegerelateerdobject"])]
con_gdf = gpd.GeoDataFrame(data={"code": con_gdf["code"].values,"geometry": con_gdf["geometry"].values})
con_gdf["codegerelateerdobject"] = con_gdf["code"]
con_gdf["streefwaarde"] = -999

gdf = gpd.GeoDataFrame(pd.concat([gpg_gdf, con_gdf], ignore_index=True))

gdf["bovenmarge"] = gdf["streefwaarde"] + 0.05
gdf["ondermarge"] = gdf["streefwaarde"] - 0.05
gdf["doelvariabelecode"] = 1

hydamo.sturing.set_data(gdf, index_col="code")


# ### Filteren
# 
# Alle branches die niet bij "Boezemmodel_v4" gooien we uit het model. Idem voor alle kunstwerken + profielen die naar deze branches zijn gesnapped. Om het resultaat te beoordelen exporteren we alles naar shape-files. We slaan het hydamo object ook op als "pickle", zodat we bovenstaande stappen niet elke keer hoeven te herhalen

# In[12]:


hydamo = hydrotools.filter_model(hydamo, attribute_filter={"IMGEOBRONH": "W0646"})
hydrotools.export_shapes(hydamo, path=Path(r"./hydamo_shp/dellen_v1"))
hydrotools.save_model(hydamo, file_name=Path(r"./hydamo_model/dellen_v1.pickle"))


# ## Converteren naar DFM
# 
# ### Aanmaken dfm-klasse

# In[13]:


dfmmodel = DFlowFMModel()


# ### Inlezen kunstwerken

# In[14]:


dfmmodel.structures.io.weirs_from_hydamo(hydamo.weirs,yz_profiles=hydamo.crosssections,parametrised_profiles=hydamo.parametrised_profiles)

dfmmodel.structures.io.culverts_from_hydamo(hydamo.culverts,hydamo.afsluitmiddel)

dfmmodel.structures.io.bridges_from_hydamo(hydamo.bridges,yz_profiles=hydamo.crosssections,parametrised_profiles=hydamo.parametrised_profiles)

dfmmodel.structures.io.orifices_from_hydamo(hydamo.orifices)

dfmmodel.structures.io.pumps_from_hydamo(pompen=hydamo.pumps,sturing=hydamo.sturing,gemalen=hydamo.gemalen)


# ### Aanmaken 1d netwerk

# In[15]:


dfmmodel.network.set_branches(hydamo.branches)
dfmmodel.network.generate_1dnetwork(one_d_mesh_distance=100.0, seperate_structures=True)


# ### Toevoegen cross-sections

# In[16]:


dfmmodel.crosssections.io.from_hydamo(dwarsprofielen=hydamo.crosssections,parametrised=hydamo.parametrised_profiles,branches=hydamo.branches)

print(f"{len(dfmmodel.crosssections.get_branches_without_crosssection())} branches are still missing a cross section.")
print(f"{len(dfmmodel.crosssections.get_structures_without_crosssection())} structures are still missing a cross section.")


# ### Wegschrijven model

# In[17]:


dfmmodel.mdu_parameters["refdate"] = 20000101
dfmmodel.mdu_parameters["tstart"] = 0.0 * 3600
dfmmodel.mdu_parameters["tstop"] = 144.0 * 1 * 3600
dfmmodel.mdu_parameters["hisinterval"] = "120. 0. 0."
dfmmodel.mdu_parameters["cflmax"] = 0.7

dimr_path = r"dummypath\run_dimr.bat"
dfmmodel.dimr_path = dimr_path
fm_writer = DFlowFMWriter(dfmmodel, output_dir="dellen", name="dellen")

fm_writer.objects_to_ldb()
fm_writer.write_all()

if Path(r".\dellen\fm\dellen.mdu").exists():
    print("Model is weggeschreven")
else:
    print("Er is geen model geschreven. Waarschijnlijk is iets fout gegaan")


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

# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:




