# Archives Nationales d'Outre-Mer Digital Archive Exfiltrator
Exfiltrate full document images from the Archives Nationales d'Outre-Mer digital archive instead of being forced to use their Java applet.

## Motivation
ANOM gives access to digital copies of archive materials only through a lol-welcome-to-the-90s Java applet. The documents themselves are served up as small fragments of pages which are then stitched together on the screen, just like a tile server for a [tiled web map](https://en.wikipedia.org/wiki/Tiled_web_map). 

\<rant\>

As far as I can tell, there's no good reason for them to do that. If they're saving anything at all on bandwidth, which I kinda doubt, they're losing it on some janky-ass 90s arcane storage infrastructure. There are only 3 image zoom levels judging by the applet's GET requests observed by Wireshark, and the use case for these documents is as far away from diving into google maps as you can get. Researchers would be far better served by having thumbnail, medium, and full size whole images available without hoops. Hell, it's doable without even changing the tech just by treating each layer as one big tile.

\</rant\>

Anyway, they way they do it now makes their digital archive documents rather difficult to use.
The first step to making them easier to use is getting them out.

## Dependencies
* GraphicsMagick - http://www.graphicsmagick.org/README.html
* Python3 - https://www.python.org/downloads/

## Setup
### Mac OS
It's easiest to install what you need on MacOS with Homebrew.

1. Go to Applications > Utilities > Terminal.app
2. Inside the terminal, type `xcode-select --install` and press enter.
3. When the message pops up asking if you want to install the command line developer tools, click `Install`.
4. Install Homebrew by visiting http://brew.sh and following the instruction. (If it's not clear, you paste `/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"` into the Terminal and then follow the prompts.)
4. Then install GraphicsMagick by typing `brew install graphicsmagick`.
5. Then, while you're at it, install Python3 with `brew install python3`.

### Windows
If you have 64 bit Windows, download: 

1. https://sourceforge.net/projects/graphicsmagick/files/graphicsmagick-binaries/1.3.25/GraphicsMagick-1.3.25-Q8-win64-dll.exe
2. https://www.python.org/ftp/python/3.6.0/python-3.6.0-amd64.exe

If you have 32 bit Windows, download: 

1. https://www.python.org/ftp/python/3.6.0/python-3.6.0.exe
2. https://sourceforge.net/projects/graphicsmagick/files/graphicsmagick-binaries/1.3.25/GraphicsMagick-1.3.25-Q8-win32-dll.exe


If you don't know which one you have, see: https://support.microsoft.com/en-us/kb/827218 or http://www.howtogeek.com/howto/21726/how-do-i-know-if-im-running-32-bit-or-64-bit-windows-answers/

### GNU/Linux

GraphicsMagick and Python3 are in your distribution's package repos. You don't need my help for this.

## Usage
After you've installed GraphicsMagick and Python3, get the files from this repository and run...

`python3 exfiltrate.py '<document_applet_url>' [first_page] [last_page]`

## Walkthrough...
1. go to http://anom.archivesnationales.culture.gouv.fr/
![ANOM front page](screenshots/screen1.png)

2. Click on the digital archive link
![digital archive](screenshots/screen2.png)

3. Go find whatever document you're looking for.
![example document](screenshots/screen3.png)

4. Instead of clicking on the document link to load their stupid Java applet, right-click and copy the link address.
![copy the link url](screenshots/screen4.png)

5. In a terminal with python3 installed, paste the copied link address where the above usage note says \<document_applet_url\> as shown. Don't forget to wrap it in single quotes so that your terminal doesn't choke on certain symbols.
![running the command](screenshots/screen5.png)

6. The result is a folder containing complete images of the document pages, plus a text file containing the full title.
![resulting files](screenshots/screen6.png)
