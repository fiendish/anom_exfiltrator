# Archives Nationales d'Outre-Mer Digital Archive Exfiltrator
Exfiltrate full document images from the Archives Nationales d'Outre-Mer digital archive instead of being forced to use their Java applet.

## Motivation
ANOM gives access to digital copies of archive materials only through a lol-welcome-to-the-90s Java applet. The documents themselves are served up as small fragments of pages which are then stitched together on the screen, just like a tile server for a [tiled web map](https://en.wikipedia.org/wiki/Tiled_web_map).

This makes their digital archive documents rather difficult to use.
The first step to making them easier to use is getting them out.

## Usage
`python3 exfiltrate.py '<document_applet_url>' [first_page] [last_page]`

### Walkthrough...
1. go to http://anom.archivesnationales.culture.gouv.fr/
![ANOM front page](screenshots/screen1.png)

2. Click on the digital archive link
![digital archive](screenshots/screen2.png)

3. Go find whatever document you're looking for.
![example document](screenshots/screen3.png)

4. Instead of clicking on the document link to load their stupid Java applet, right-click and copy the link address.
![copy the link url](screenshots/screen4.png)

5. In a terminal with python3 installed, paste the copied link address where the above usage note says \<document_applet_url\> as shown.
![running the command](screenshots/screen5.png)

6. The result is a folder containing complete images of the document pages, plus a text file containing the full title.
![resulting files](screenshots/screen6.png)
