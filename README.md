# Archives Nationales d'Outre-Mer Digital Archive Exfiltrator
Exfiltrate full document images from the Archives Nationales d'Outre-Mer digital archive instead of being forced to use their Java applet.

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
![ANOM front page](screenshots/screen4.png)

5. In a terminal with python3 installed, paste the copied link address where the above usage note says \<document_applet_url\> as shown.
![ANOM front page](screenshots/screen5.png)
