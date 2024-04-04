# To use this Makefile, get a copy of my SF Release Tool
# git clone git://git.code.sf.net/p/sfreleasetools/code sfreleasetools
# or on github:
# git clone https://github.com/schlatterbeck/releasetool.git
# And point the environment variable RELEASETOOL to the checkout
ifeq (,${RELEASETOOL})
    RELEASETOOL=../releasetool
endif
LASTRELEASE:=$(shell $(RELEASETOOL)/lastrelease -n -rV)
VERSIONPY=yabasi/Version.py
VERSIONTXT=VERSION
VERSION=$(VERSIONPY) $(VERSIONTXT)
README=README.rst
PROJECT=yabasi

all: $(VERSION)

clean:
	rm -f README.html yabasi/Version.py announce_pypi VERSION
	rm -rf dist build upload upload_homepage ReleaseNotes.txt \
            yabasi.egg-info __pycache__ upload_pypi announce_pypi

.PHONY: clean

include $(RELEASETOOL)/Makefile-pyrelease
