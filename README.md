# TKI3: Pilot Hunze & Aa's
Pilotproject van Waterschap Hunze &amp; Aa's binnen TKI3

Welkom bij de pilot Hunze en Aa's, waarin we een D-Hydro-model bouwen voor het stroomgebied De Dellen.

Volg deze stappen	:
1. Download de broncode (groene button [Code]) van dit script en plaats die in een map op de eigen computer
1. Zorg voor een D-HyDAMO-omgeving: https://github.com/openearth/delft3dfmpy#installation
1. Activeer de delft3dfmpy omgeving via de Anaconda Prompt (niet te verwarren met de reguliere command-prompt van Windows!):
```
conda activate delft3dfmpy
```
3. Open Jupyter Notebook via command-prompt in de geactiveerder omgeving:
```
jupyter notebook
```
4. Selecteer modelbouw.ipynb vanuit Jupyter Notebook en volg de notebook


## Delft3dfmpy debuggen:

1. Creëer een fork van delft3dfmpy en synchroniseer die met je harde schijf
1. Creëer een werkende delft3dfmpy-omgeving en de-installeer delft3dfmpy (conda deactivate delft3dfmpy)
1. verwijs in het jupyter notebook naar de locatie van delft3dfmpy Zie daarin onderstaand onder Controle Bestanden de regel sys.path.append(r'....\DELFT3DFMPY_SB')

Let op: ten behoeve van dit project heb ik enkele zaken in Delft3dfmpy aangepast die nog niet gecommit zijn:
1. Parameter bedlevel voor bruggen is vervangen door shift. Dit zat nog niet in delft3dfmpy verwerkt
2. Wegschrijven structure.ini: versienummer opgehoogd van 2.0 naar 3.0 (opmerking Geert Prinsen aangaande het niet draaien via de DIMR onder D-Hydro 1.10) 
  Daarom is het voor nu raadzaam om met een lokale versie van delft3dfmpy te werken
