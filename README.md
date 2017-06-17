( Questions/Feedback? Either create an "issue" at https://github.com/fiendish/anom_exfiltrator/issues or contact me at patcherton.fixesthings@gmail.com )

# Archives Nationales d'Outre-Mer Digital Archive Exfiltrator
Exfiltrate full document images from the Archives Nationales d'Outre-Mer digital archive instead of being forced to use their Java applet.

## Motivation
ANOM gives free access (yay!) to digital copies of archive materials only through a lol-welcome-to-the-90s Java applet (boo!). Each page of each document is served up in small fragments which are then stitched together on the screen (technical note: this is just like a tile server for a [tiled web map](https://en.wikipedia.org/wiki/Tiled_web_map)). There's no good reason for them to do it that way today and many bad ones. It's archaic, likely vestigial from an era before there were better methods.

Anyway, the way they do it now makes their digital archive documents more difficult to use.
The first step to making them easier to use is exfiltrating them past the applet barrier. 

Want to throw all the document pages into a big PDF and carry it around with you? Maybe read it on the bus or airplane? Now you can with little effort. ([On Mac](https://apple.stackexchange.com/questions/11163/how-do-i-combine-two-or-more-images-to-get-a-single-pdf-file), [On Windows](http://www.howtogeek.com/248462/how-to-combine-images-into-one-pdf-file-in-windows/), [On GNU/Linux](https://gitlab.mister-muffin.de/josch/img2pdf))

## Installation / Setup
This package requires Python3 and ImageMagick. Read further for instructions on installing them first.

### Mac OS
It's easiest to install what you need to run this on MacOS with Homebrew.

1. Go to Applications > Utilities > Terminal.app
2. Inside the terminal, type `xcode-select --install` and press enter.
3. When the message pops up asking if you want to install the command line developer tools, click `Install`.
4. **Install Homebrew** by visiting <http://brew.sh> and following the instruction. (If it's not clear, you paste `/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"` into the Terminal and then follow the prompts.)
4. **Install ImageMagick** by typing `brew install imagemagick`.
5. **Install Python3** with `brew install python3`.
6. Proceed to the Usage Guide below.

### Windows
0. If you don't know whether you have 32 or 64 bit Windows, first see: <https://support.microsoft.com/en-us/kb/827218> or <http://www.howtogeek.com/howto/21726/how-do-i-know-if-im-running-32-bit-or-64-bit-windows-answers/>
1. **Install ImageMagick**. 
  - If you have 64 bit Windows, download: <https://www.imagemagick.org/download/binaries/ImageMagick-7.0.5-4-Q8-x64-dll.exe>
  - If you have 32 bit Windows, download: <https://www.imagemagick.org/download/binaries/ImageMagick-7.0.5-4-Q8-x86-dll.exe>
2. **Install Python3**.
  - If you have 64 bit Windows, download: <https://www.python.org/ftp/python/3.6.0/python-3.6.0-amd64.exe> 
  - If you have 32 bit Windows, download: <https://www.python.org/ftp/python/3.6.0/python-3.6.0.exe>
  - During the Python3 install process, make sure to activate the option to "`Add python.exe to Path`". You may need to restart your computer after installing Python3 before that starts working.
3. Proceed to the Usage Guide below.

### GNU/Linux
1. Install ImageMagick and Python3 from your distribution's package repos.
2. Proceed to the Usage Guide below.

## Usage Guide
1. Download and unzip <https://github.com/fiendish/anom_exfiltrator/archive/master.zip> to your deskop.
2. To exfiltrate an entire document (which may use a lot of space on your hard drive if the document is very large), run Exfiltrate_ANOM. Or to interactively browse one page at a time from a document, run Browse_ANOM.

## Getting URLs...
The software asks you for an ANOM URL for a document you want to view or exfiltrate. This is how you get it.

1. go to <http://anom.archivesnationales.culture.gouv.fr/>
![ANOM front page](screenshots/screen1.png)

2. Go find whatever document you're looking for.
![finding a document](screenshots/screen2.png)
![still finding a document](screenshots/screen3.png)

3. Instead of using their stupid Java applet, copy the link address for the document.
![copy the link url](screenshots/screen4.png)

5. Then paste the URL into the exfiltrator interface where it asks you.
