default:
    @just --list

test:
    swift test
    python3 -m unittest discover -s Tests/InstallerTests -v

build:
    python3 build.py

install: build
    python3 install.py

check: test build
