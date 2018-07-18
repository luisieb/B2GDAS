from CRABClient.UserUtilities import config
config = config()

config.General.requestName = 'B2GDAS_SingleMuon'
config.General.workArea = 'crab_projects'
config.General.transferOutputs = True
config.General.transferLogs = True

config.JobType.pluginName = 'Analysis'
config.JobType.psetName = 'PSet.py'

config.Data.inputDataset = '/SingleMuon/Run2017B-17Nov2017-v1/MINIAOD'
config.Data.inputDBS = 'global'
#config.Data.splitting = 'LumiBased'
config.Data.splitting = 'Automatic'
#config.Data.unitsPerJob = 200
config.Data.lumiMask = 'https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions17/13TeV/ReReco/Cert_294927-306462_13TeV_EOY2017ReReco_Collisions17_JSON_v1.txt'
#config.Data.runRange = '273403-273404'

config.Site.storageSite = 'T2_DE_DESY'

config.JobType.scriptExe = 'execute_for_crab_data.sh'

config.JobType.outputFiles = ['output.root']
config.JobType.inputFiles = ['FrameworkJobReport.xml', 'execute_for_crab.py', 'b2gdas_fwlite.py', 'leptonic_nu_z_component.py', 'JECs', 'purw.root', 'MuonID_Sys.root', 'MuonIso_Sys.root', 'MuonTrigger_SF.root' , 'rootlogon.C']
