from CRABClient.UserUtilities import config
config = config()

config.General.requestName = 'B2GDAS_diboson'
config.General.workArea = 'crab_projects'
config.General.transferOutputs = True
config.General.transferLogs = True

config.JobType.pluginName = 'Analysis'
config.JobType.psetName = 'PSet.py'

#config.Data.inputDataset = '/TTToSemiLeptonic_TuneCP5_PSweights_13TeV-powheg-pythia8/RunIIFall17MiniAOD-94X_mc2017_realistic_v10-v1/MINIAODSIM'
config.Data.inputDataset = '/WW_TuneCP5_13TeV-pythia8/RunIIFall17MiniAOD-94X_mc2017_realistic_v10-v1/MINIAODSIM'
config.Data.inputDBS = 'global'
config.Data.splitting = 'FileBased'
config.Data.unitsPerJob = 20

config.Site.storageSite = 'T2_DE_DESY'

config.JobType.scriptExe = 'execute_for_crab.sh'

config.JobType.outputFiles = ['output.root']
config.JobType.inputFiles = ['FrameworkJobReport.xml', 'execute_for_crab.py', 'b2gdas_fwlite.py', 'leptonic_nu_z_component.py', 'JECs', 'purw.root', 'MuonID_Sys.root', 'MuonIso_Sys.root', 'MuonTrigger_SF.root' , 'rootlogon.C']
