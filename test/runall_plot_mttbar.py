#! /usr/bin/env python


## _________                _____.__                            __  .__
## \_   ___ \  ____   _____/ ____\__| ____  __ ______________ _/  |_|__| ____   ____
## /    \  \/ /  _ \ /    \   __\|  |/ ___\|  |  \_  __ \__  \\   __\  |/  _ \ /    \
## \     \___(  <_> )   |  \  |  |  / /_/  >  |  /|  | \// __ \|  | |  (  <_> )   |  \
##  \______  /\____/|___|  /__|  |__\___  /|____/ |__|  (____  /__| |__|\____/|___|  /
##         \/            \/        /_____/                   \/                    \/
import sys
import array as array
from plot_mttbar import plot_mttbar

#Add more lines for missing processes!
ttjetsStr = ["--file_in", "output_ttjets.root", "--file_out", "plots_ttjets.root"]
rsgluon3TeVStr = ["--file_in", "output_rsgluon3TeV.root", "--file_out", "plots_rsgluon3TeV.root"]
singlemuStr = ["--file_in", "output_singlemuon.root", "--file_out", "plots_datamuon.root"]

#Add more lines for missing processes!
plot_mttbar( ttjetsStr )
plot_mttbar( rsgluon3TeVStr )
plot_mttbar( singlemuStr )
