# TKI3: Pilot Hunze & Aa's
Pilotproject van Waterschap Hunze &amp; Aa's binnen TKI3

Welkom bij de pilot Hunze en Aa's, waarin we een D-Hydro-model bouwen voor het stroomgebied De Dellen.

Volg deze stappen	:
1. Installeer Anaconda (python IDE).
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

