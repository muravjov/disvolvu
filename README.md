# Disvolvu

Disvolvu is an utility for deploying projects on *developer's machines*. For complex
projects today you have not only grab sources from various repositories, but also install
system dependencies, create test environments and so on just to begin your real coding work.

Disvolvu suggests a way to automate this routine work in way that utility `make` does.
You write a text file, called a *receipt*, where you define targetes, its dependencies
and rules how to reach targets.

## Installation

    pip install -r https://github.com/muravjov/disvolvu/raw/master/requirements.txt

## Syntax

```
$ disvolvu 
usage: disvolvu [-h] [--print-order] [--all-targets] [--report-timings]
                receipt.py TARGETS
```
