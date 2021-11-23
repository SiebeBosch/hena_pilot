# TKI3: Pilot Hunze & Aa's
Pilotproject van Waterschap Hunze &amp; Aa's binnen TKI3

Welkom bij de pilot Hunze en Aa's, waarin we een D-Hydro-model bouwen voor het stroomgebied De Dellen.

Volg deze stappen	:
1. Installeer Anaconda (python IDE): https://www.anaconda.com/products/individual.
2. Download de broncode (groene button [Code]) van dit script en plaats die in een map op de eigen computer
3. Zorg voor een D-HyDAMO-omgeving: https://github.com/openearth/delft3dfmpy#installation. 
In het kort: draai vanuit de Anaconda Prompt deze code vanuit de map waar de environment.yml staat:
```
conda env create -f environment.yml
```
4. Activeer de delft3dfmpy omgeving via de Anaconda Prompt (niet te verwarren met de reguliere command-prompt van Windows!):
```
conda activate delft3dfmpy
```
5. Installeer delft3dfmpy in deze omgeving
```
python -m pip install delft3dfmpy
```
6. Open Jupyter Notebook via command-prompt in de geactiveerder omgeving:
```
jupyter notebook
```
7. Selecteer modelbouw.ipynb vanuit Jupyter Notebook en voer alle code in het notebook uit

Zodra het model gereed is, staat hij in de map 'dellen'. Het model kan in D-Hydro worden ingeladen door het bestand dimr_config.xml te importeren. Creëer in D-Hydro een nieuw, leeg, project en kies Import - DIMR Configuration File (*.xml).

![image](https://user-images.githubusercontent.com/9431285/143057529-e4b2371e-c6a7-4ace-876d-13cac43add52.png)

U kunt het model ook eenvoudig draaien buiten de gebruikersinterface van D-Hydro om, door middel van de zogeheten DIMR. Verwijs hiertoe in het bestand run.bat naar de juiste locatie van het bestand run_dimr.bat in uw D-Hydro installatie. Doorgaans volstaat het aanpassen van het D-Hydro versienummer in de string "c:\Program Files\Deltares\D-HYDRO Suite 1D2D (1.0.0.53506)\plugins\DeltaShell.Dimr\kernels\x64\dimr\scripts\run_dimr.bat". Zodra dit pad goed is ingesteld kan de DIMR worden uitgevoerd door run.bat dubbel te klikken.

### Workflow:

Onderstaand diagram toont de beoogde en uiteindelijk geïmplementeerde werkwijze. 

![image](https://user-images.githubusercontent.com/9431285/143056291-d84bbff6-b992-475e-a09c-a8997f05a2b4.png)

Uit het beheerregister halen we de voor het projectgebied relevante brongegevens. Deze worden geëxporteerd naar shapefiles. Zaken als trapeziumprofielen (voor watergangen waarvoor geen ingemeten profiel beschikbaar is) alsmede tijdreeksen slaan we op in een Excel-document.

Het bestaande programma Channel Builder (Hydroconsult; geen onderdeel van dit script) wordt gebruikt om de brongegevens te valideren en waar nodig te corrigeren. De modelbouwscripts lezen de brongegevens en het Excel-document uit en verwerken dit tot een werkende modelschematisatie in D-Hydro.

De bouw van de 1D FM- en -RTC componenten wordt uitgevoerd door een drietal modelbouwscripts: In een Jupyter Notebook configureren we de bronbestanden, gegevensvelden en eventuele uitzonderlijkheden. Het Jupyter Notebook roept functies aan uit het python-script HydroTools (D2Hydro) en functies uit het Delft3Dfmpy-script van Deltares. 

De bouw van de RR-component voeren we uit met het bestaande programma Catchment Builder (Hydroconsult; geen onderdeel van dit script).

### Resultaat:

De hierboven geschetste workflow resulteert in een werkend D-Hydro model van het stroomgebied De Dellen, bestaande uit de componenten RR, FM en RTC.

![image](https://user-images.githubusercontent.com/9431285/143059481-9b2674a6-949f-4ecd-9851-ea20bc8fbbb6.png)



### Delft3dfmpy debuggen (optioneel):

1. Creëer een fork van delft3dfmpy en synchroniseer deze met je harde schijf
1. Creëer een werkende delft3dfmpy-omgeving en de-installeer delft3dfmpy (conda deactivate delft3dfmpy)
1. verwijs in het jupyter notebook naar de locatie van delft3dfmpy Zie daarin onderstaand onder Controle Bestanden de regel sys.path.append(r'....\DELFT3DFMPY_SB')

Gedurende het project heb ik gewerkt met een lokale fork van Delft3dfmpy waarin ik enkele kleine bugs had opgelost. 
Inmiddels zijn deze bugs ook opgelost in de publieke repository:
1. Parameter bedlevel voor bruggen is vervangen door shift. Dit zat nog niet in delft3dfmpy verwerkt
2. Wegschrijven structure.ini: versienummer opgehoogd van 2.0 naar 3.0 (opmerking Geert Prinsen aangaande het niet draaien via de DIMR onder D-Hydro 1.10) 
  Daarom is het voor nu raadzaam om met een lokale versie van delft3dfmpy te werken
  
Terug naar de gewone public package van delft3dfmpy?
1. Verwijder je oude environment:
```
conda remove delft3dfmpy? (nog uitzoeken hoe dit ook alweer ging)
```

3. Verwijder de prefix van je lokale fork: 
```
conda remove --all --prefix "d:\GITHUB\DELFT3DFMPY_SB\"
```
of van je oude conda install:
```
conda remove --all --prefix "C:\Users\Siebe\anaconda3\envs\delft3dfmpy"
```
1.  Installeer de reguliere delft3dfmpy weer met conda install

```
conda env create -f environment.yml
conda activate delft3dfmpy
```

