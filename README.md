B2GDAS
======


CMS Data Analysis School (CMSDAS) exercise for the
Beyond Two Generations Physics Analysis Group (B2G PAG)

To run :

`module use -a /afs/desy.de/group/cms/modulefiles/`

`module load cmssw`

`export SCRAM_ARCH=slc6_amd64_gcc630` *if using BASH*

`cmsenv`

`cmsrel CMSSW_9_4_8`

`cd CMSSW_9_4_8/src`

`git clone https://github.com/reimersa/B2GDAS.git Analysis/B2GDAS`

`cd Analysis/B2GDAS`

`scram b -j 10`

`cd test`

`python b2gdas_fwlite.py --input=inputfiles/ttsemilep.txt --output=ttsemilep.root --maxevents 10000`


After this initial setup, the following lines should be executed in the CMSSW_9_4_8/src directory.

`module use -a /afs/desy.de/group/cms/modulefiles/`

`module load cmssw`

`export SCRAM_ARCH=slc6_amd64_gcc630`

`cmsenv`

