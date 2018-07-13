#! /usr/bin/env python
import ROOT, copy, sys, logging
from array import array
from DataFormats.FWLite import Events, Handle

############################################
# Jet Energy Corrections / Resolution tools


jet_energy_resolution = [
  (0.000, 0.522, 1.1595, 0.0645),
  (0.522, 0.783, 1.1948, 0.0652),
  (0.783, 1.131, 1.1464, 0.0632),
  (1.131, 1.305, 1.1609, 0.1025),
  (1.305, 1.740, 1.1278, 0.0986),
  (1.740, 1.930, 1.1000, 0.1079),
  (1.930, 2.043, 1.1426, 0.1214),
  (2.043, 2.322, 1.1512, 0.1140),
  (2.322, 2.500, 1.2963, 0.2371),
  (2.500, 2.853, 1.3418, 0.2091),
  (2.853, 2.964, 1.7788, 0.2008),
  (2.964, 3.139, 1.1869, 0.1243),
  (3.139, 5.191, 1.1922, 0.1488)
]


def createJEC(jecSrc, jecLevelList, jetAlgo):
    log = logging.getLogger('JEC')
    log.info('Getting jet energy corrections for %s jets', jetAlgo)
    jecParameterList = ROOT.vector('JetCorrectorParameters')()
    # Load the different JEC levels (the order matters!)
    for jecLevel in jecLevelList:
        log.debug('  - %s jet corrections', jecLevel)
        jecParameter = ROOT.JetCorrectorParameters('%s_%s_%s.txt' % (jecSrc, jecLevel, jetAlgo));
        jecParameterList.push_back(jecParameter)
    # Chain the JEC levels together
    return ROOT.FactorizedJetCorrector(jecParameterList)


def getJEC(jecSrc, uncSrc, jet, area, rho, nPV): # get JEC and uncertainty for an *uncorrected* jet
    # Give jet properties to JEC source
    jecSrc.setJetEta(jet.Eta())
    jecSrc.setJetPt(jet.Perp())
    jecSrc.setJetE(jet.E())
    jecSrc.setJetA(area)
    jecSrc.setRho(rho)
    jecSrc.setNPV(nPV)
    jec = jecSrc.getCorrection() # get jet energy correction

    # Give jet properties to JEC uncertainty source
    uncSrc.setJetPhi(jet.Phi())
    uncSrc.setJetEta(jet.Eta())
    uncSrc.setJetPt(jet.Perp() * jec)
    corrDn = 1. - uncSrc.getUncertainty(0) # get jet energy uncertainty (down)

    uncSrc.setJetPhi(jet.Phi())
    uncSrc.setJetEta(jet.Eta())
    uncSrc.setJetPt(jet.Perp() * jec)
    corrUp = 1. + uncSrc.getUncertainty(1) # get jet energy uncertainty (up)

    return (jec, corrDn, corrUp)


def getJER(jetEta, sysType):
    """
    Here, jetEta should be the jet pseudorapidity, and sysType is:
        nominal : 0
        down    : -1
        up      : +1
    """

    if sysType not in [0, -1, 1]:
        raise Exception('ERROR: Unable to get JER! use type=0 (nom), -1 (down), +1 (up)')

    for (etamin, etamax, scale_nom, scale_uncert) in jet_energy_resolution:
        if etamin <= abs(jetEta) < etamax:
            if sysType < 0:
                return scale_nom - scale_uncert
            elif sysType > 0:
                return scale_nom + scale_uncert
            else:
                return scale_nom
    raise Exception('ERROR: Unable to get JER for jets at eta = %.3f!' % jetEta)




############################################
# Command line parsing

def getUserOptions(argv):
    from optparse import OptionParser
    parser = OptionParser()

    def add_option(option, **kwargs):
        parser.add_option('--' + option, dest=option, **kwargs)

    add_option('input',              default='',
        help='Name of file with list of input files')

    add_option('output',             default='output.root',
        help='Name of output file')

    add_option('verbose',            default=False, action='store_true',
        help='Print debugging info')

    add_option('maxevents',          default=-1,
        help='Number of events to run. -1 is all events')

    add_option('isCrabRun',          default=False, action='store_true',
        help='Use this flag when running with crab on the grid')

    add_option('disableTree',        default=False, action='store_true',
        help='Disable Tree creation')

    add_option('disablePileup',      default=False, action='store_true',
        help='Disable pileup reweighting')

    add_option('isData',             default=False, action='store_true',
        help='Enable processing as data')

    add_option('trigProc',           default='HLT',
        help='Name of trigger process')

    add_option('trigProcMETFilters', default='PAT',
        help='Name of trigger process for MET filters')

    add_option('bdisc',              default='pfDeepCSVJetTags:probb',
        help='Name of b jet discriminator')

    add_option('minMuonPt',          default=55.,   type='float',
        help='Minimum PT for muons')

    add_option('maxMuonEta',         default=2.4,   type='float',
        help='Maximum muon pseudorapidity')

    add_option('minAK4Pt',           default=30.,   type='float',
        help='Minimum PT for AK4 jets')

    add_option('maxAK4Rapidity',     default=2.4,   type='float',
        help='Maximum AK4 rapidity')

    add_option('minAK8Pt',           default=400.,  type='float',
        help='Minimum PT for AK8 jets')

    add_option('maxAK8Rapidity',     default=2.4,   type='float',
        help='Maximum AK8 rapidity')

    (options, args) = parser.parse_args(argv)
    argv = []

    print '===== Command line options ====='
    print options
    print '================================'
    return options


def getInputFiles(options):
    result = []
    with open(options.input, 'r') as fpInput:
        for lfn in fpInput:
            lfn = lfn.strip()
            if lfn:
                if not options.isCrabRun:
                    pfn = 'file:/pnfs/desy.de/cms/tier2/' + lfn
                else:
                    #pfn = 'root://cmsxrootd-site.fnal.gov/' + lfn
                    pfn = 'root://xrootd-cms.infn.it/' + lfn
                print 'Adding ' + pfn
                result.append(pfn)
    return result


def b2gdas_fwlite(argv):
    ## _____________      __.____    .__  __             _________ __          _____  _____ 
    ## \_   _____/  \    /  \    |   |__|/  |_  ____    /   _____//  |_ __ ___/ ____\/ ____\
    ##  |    __) \   \/\/   /    |   |  \   __\/ __ \   \_____  \\   __\  |  \   __\\   __\ 
    ##  |     \   \        /|    |___|  ||  | \  ___/   /        \|  | |  |  /|  |   |  |   
    ##  \___  /    \__/\  / |_______ \__||__|  \___  > /_______  /|__| |____/ |__|   |__|   
    ##      \/          \/          \/             \/          \/                           

    options = getUserOptions(argv)
    ROOT.gROOT.Macro("rootlogon.C")

    muons, muonLabel = Handle("std::vector<pat::Muon>"), "slimmedMuons"
    electrons, electronLabel = Handle("std::vector<pat::Electron>"), "slimmedElectrons"
    photons, photonLabel = Handle("std::vector<pat::Photon>"), "slimmedPhotons"
    taus, tauLabel = Handle("std::vector<pat::Tau>"), "slimmedTaus"
    #jets, jetLabel = Handle("std::vector<pat::Jet>"), "slimmedJets"
    jets, jetLabel = Handle("std::vector<pat::Jet>"), "slimmedJetsPuppi"
    ak8jets, ak8jetLabel = Handle("std::vector<pat::Jet>"), "slimmedJetsAK8"
    #ak8jets, ak8jetLabel = Handle("std::vector<pat::Jet>"), "slimmedJetsAK8PFPuppiSoftDropPacked_SubJets"
    mets, metLabel = Handle("std::vector<pat::MET>"), "slimmedMETs"
    vertices, vertexLabel = Handle("std::vector<reco::Vertex>"), "offlineSlimmedPrimaryVertices"
    pileups, pileuplabel = Handle("std::vector<PileupSummaryInfo>"), "slimmedAddPileupInfo"
    rhos, rhoLabel = Handle("double"), "fixedGridRhoAll"
    gens, genLabel = Handle("std::vector<reco::GenParticle>"), "prunedGenParticles"
    genInfo, genInfoLabel = Handle("GenEventInfoProduct"), "generator"
    # Enterprising students could figure out the LHE weighting for theoretical uncertainties
    #lheInfo, lheInfoLabel = Handle("LHEEventProduct"), "externalLHEProducer"
    triggerBits, triggerBitLabel = Handle("edm::TriggerResults"), ("TriggerResults","", options.trigProc)
    metfiltBits, metfiltBitLabel = Handle("edm::TriggerResults"), ("TriggerResults","", options.trigProcMETFilters)


#TODO find more triggers? Electron triggers?
    trigsToRun = ["HLT_Mu50_v"]
    
    ##   ___ ___ .__          __                                             
    ##  /   |   \|__| _______/  |_  ____   ________________    _____   ______
    ## /    ~    \  |/  ___/\   __\/  _ \ / ___\_  __ \__  \  /     \ /  ___/
    ## \    Y    /  |\___ \  |  | (  <_> ) /_/  >  | \// __ \|  Y Y  \\___ \ 
    ##  \___|_  /|__/____  > |__|  \____/\___  /|__|  (____  /__|_|  /____  >
    ##        \/         \/             /_____/            \/      \/     \/

    f = ROOT.TFile(options.output, "RECREATE")
    f.cd()

    # Actually to make life easy, we're going to make "N-dimensional histograms" aka Ntuples
    if not options.disableTree:
        TreeSemiLept = ROOT.TTree("TreeSemiLept", "TreeSemiLept")

        SemiLeptTrig = ROOT.vector('int')()
        TreeSemiLept.Branch('SemiLeptTrig', "std::vector<int>",  SemiLeptTrig)

        def bookFloatBranch(name, default):
            tmp = array('f', [default])
            TreeSemiLept.Branch(name, tmp, '%s/F' % name)
            return tmp
        def bookIntBranch(name, default):
            tmp = array('i', [default])
            TreeSemiLept.Branch(name, tmp, '%s/I' % name)
            return tmp
        def bookLongIntBranch(name, default):
            tmp = array('l', [default])
            TreeSemiLept.Branch(name, tmp, '%s/L' % name)
            return tmp

        # Event weights
        GenWeight             = bookFloatBranch('GenWeight', 0.)
        PUWeight              = bookFloatBranch('PUWeight', 0.)
        # Fat jet properties
        FatJetBDisc           = bookFloatBranch('FatJetBDisc', -1.)
        FatJetDeltaPhiLep     = bookFloatBranch('FatJetDeltaPhiLep', -1.) 
        FatJetEnergy          = bookFloatBranch('FatJetEnergy', -1.)
        FatJetEta             = bookFloatBranch('FatJetEta', -1.)
        FatJetJECDnSys        = bookFloatBranch('FatJetJECDnSys', -1.)
        FatJetJECUpSys        = bookFloatBranch('FatJetJECUpSys', -1.)
        FatJetJERDnSys        = bookFloatBranch('FatJetJERDnSys', -1.)
        FatJetJERUpSys        = bookFloatBranch('FatJetJERUpSys', -1.)
        FatJetMass            = bookFloatBranch('FatJetMass', -1.)
        FatJetMassSoftDrop    = bookFloatBranch('FatJetMassSoftDrop', -1.)
        FatJetPhi             = bookFloatBranch('FatJetPhi', -1.)
        FatJetPt              = bookFloatBranch('FatJetPt', -1.)
        FatJetRap             = bookFloatBranch('FatJetRap', -1.)
        FatJetSDBDiscB        = bookFloatBranch('FatJetSDBDiscB', -1.)
        FatJetSDBDiscW        = bookFloatBranch('FatJetSDBDiscW', -1.)
        FatJetSDsubjetBmass   = bookFloatBranch('FatJetSDsubjetBmass', -1.)
        FatJetSDsubjetBpt     = bookFloatBranch('FatJetSDsubjetBpt', -1.)
        FatJetSDsubjetWmass   = bookFloatBranch('FatJetSDsubjetWmass', -1.)
        FatJetSDsubjetWpt     = bookFloatBranch('FatJetSDsubjetWpt', -1.)
        FatJetTau21           = bookFloatBranch('FatJetTau21', -1.)
        FatJetTau32           = bookFloatBranch('FatJetTau32', -1.)
        # Lepton properties
        LeptonDRMin           = bookFloatBranch('LeptonDRMin', -1.)
        LeptonEnergy          = bookFloatBranch('LeptonEnergy', -1.)
        LeptonEta             = bookFloatBranch('LeptonEta', -1.)
        LeptonIDWeight        = bookFloatBranch('LeptonIDWeight', 0.)
        LeptonIDWeightUnc     = bookFloatBranch('LeptonIDWeightUnc', 0.)
        LeptonIsoWeight       = bookFloatBranch('LeptonIsoWeight', 0.)
        LeptonIsoWeightUnc    = bookFloatBranch('LeptonIsoWeightUnc', 0.)
        LeptonTrigWeight      = bookFloatBranch('LeptonTrigWeight', 0.)
        LeptonTrigWeightUnc   = bookFloatBranch('LeptonTrigWeightUnc', 0.)
        LeptonIso             = bookFloatBranch('LeptonIso', -1.)
        LeptonPhi             = bookFloatBranch('LeptonPhi', -1.)
        LeptonPt              = bookFloatBranch('LeptonPt', -1.)
        LeptonPtRel           = bookFloatBranch('LeptonPtRel', -1.)
        LeptonType            = bookIntBranch('LeptonType', -1)
        # Nearest AK4 Jet properties
        NearestAK4JetBDisc    = bookFloatBranch('NearestAK4JetBDisc', -1.)
        NearestAK4JetEta      = bookFloatBranch('NearestAK4JetEta', -1.)
        NearestAK4JetJECDnSys = bookFloatBranch('NearestAK4JetJECDnSys', -1.)
        NearestAK4JetJECUpSys = bookFloatBranch('NearestAK4JetJECUpSys', -1.)
        NearestAK4JetJERDnSys = bookFloatBranch('NearestAK4JetJERDnSys', -1.)
        NearestAK4JetJERUpSys = bookFloatBranch('NearestAK4JetJERUpSys', -1.)
        NearestAK4JetMass     = bookFloatBranch('NearestAK4JetMass', -1.)
        NearestAK4JetPhi      = bookFloatBranch('NearestAK4JetPhi', -1.)
        NearestAK4JetPt       = bookFloatBranch('NearestAK4JetPt', -1.)
        # Semi leptonic event properties
        SemiLepMETphi         = bookFloatBranch('SemiLepMETphi', -1.)
        SemiLepMETpt          = bookFloatBranch('SemiLepMETpt', -1.)
        SemiLepNvtx           = bookIntBranch('SemiLepNvtx', -1)
        SemiLeptWeight        = bookFloatBranch('SemiLeptWeight', 0.)
        # Event information
        SemiLeptEventNum      = bookLongIntBranch('SemiLeptEventNum', -1)
        SemiLeptLumiNum       = bookIntBranch('SemiLeptLumiNum', -1)
        SemiLeptRunNum        = bookIntBranch('SemiLeptRunNum', -1)

    # and also make a few 1-d histograms
    h_mttbar_true = ROOT.TH1F("h_mttbar_true", "True m_{t#bar{t}};m_{t#bar{t}} (GeV)", 200, 0, 6000)

    h_ptLep = ROOT.TH1F("h_ptLep", "Lepton p_{T};p_{T} (GeV)", 100, 0, 1000)
    h_etaLep = ROOT.TH1F("h_etaLep", "Lepton #eta;#eta", 120, -6, 6 )
    h_met = ROOT.TH1F("h_met", "Missing p_{T};p_{T} (GeV)", 100, 0, 1000)
    h_ptRel = ROOT.TH1F("h_ptRel", "p_{T}^{REL};p_{T}^{REL} (GeV)", 100, 0, 100)
    h_dRMin = ROOT.TH1F("h_dRMin", "#Delta R_{MIN};#Delta R_{MIN}", 100, 0, 5.0)
    h_2DCut = ROOT.TH2F("h_2DCut", "2D Cut;#Delta R;p_{T}^{REL}", 20, 0, 5.0, 20, 0, 100 )

    h_ptAK4 = ROOT.TH1F("h_ptAK4", "AK4 Jet p_{T};p_{T} (GeV)", 300, 0, 3000)
    h_etaAK4 = ROOT.TH1F("h_etaAK4", "AK4 Jet #eta;#eta", 120, -6, 6)
    h_yAK4 = ROOT.TH1F("h_yAK4", "AK4 Jet Rapidity;y", 120, -6, 6)
    h_phiAK4 = ROOT.TH1F("h_phiAK4", "AK4 Jet #phi;#phi (radians)",100,-ROOT.Math.Pi(),ROOT.Math.Pi())
    h_mAK4 = ROOT.TH1F("h_mAK4", "AK4 Jet Mass;Mass (GeV)", 100, 0, 1000)
    h_BDiscAK4 = ROOT.TH1F("h_BDiscAK4", "AK4 b discriminator;b discriminator", 100, 0, 1.0)

    h_ptAK8 = ROOT.TH1F("h_ptAK8", "AK8 Jet p_{T};p_{T} (GeV)", 300, 0, 3000)
    h_etaAK8 = ROOT.TH1F("h_etaAK8", "AK8 Jet #eta;#eta", 120, -6, 6)
    h_yAK8 = ROOT.TH1F("h_yAK8", "AK8 Jet Rapidity;y", 120, -6, 6)
    h_phiAK8 = ROOT.TH1F("h_phiAK8", "AK8 Jet #phi;#phi (radians)",100,-ROOT.Math.Pi(),ROOT.Math.Pi())
    h_mAK8 = ROOT.TH1F("h_mAK8", "AK8 Jet Mass;Mass (GeV)", 100, 0, 1000)
    h_msoftdropAK8 = ROOT.TH1F("h_msoftdropAK8", "AK8 Softdrop Jet Mass;Mass (GeV)", 100, 0, 1000)
    h_minmassAK8 = ROOT.TH1F("h_minmassAK8", "AK8 CMS Top Tagger Min Mass Paring;m_{min} (GeV)", 100, 0, 1000)
    h_nsjAK8 = ROOT.TH1F("h_nsjAK8", "AK8 CMS Top Tagger N_{subjets};N_{subjets}", 5, 0, 5)
    h_tau21AK8 = ROOT.TH1F("h_tau21AK8", "AK8 Jet #tau_{2} / #tau_{1};Mass#tau_{21}", 100, 0, 1.0)
    h_tau32AK8 = ROOT.TH1F("h_tau32AK8", "AK8 Jet #tau_{3} / #tau_{2};Mass#tau_{32}", 100, 0, 1.0)



    ##      ____.       __    _________                                     __  .__                      
    ##     |    | _____/  |_  \_   ___ \  __________________   ____   _____/  |_|__| ____   ____   ______
    ##     |    |/ __ \   __\ /    \  \/ /  _ \_  __ \_  __ \_/ __ \_/ ___\   __\  |/  _ \ /    \ /  ___/
    ## /\__|    \  ___/|  |   \     \___(  <_> )  | \/|  | \/\  ___/\  \___|  | |  (  <_> )   |  \\___ \ 
    ## \________|\___  >__|    \______  /\____/|__|   |__|    \___  >\___  >__| |__|\____/|___|  /____  >
    ##               \/               \/                          \/     \/                    \/     \/ 

    ROOT.gSystem.Load('libCondFormatsJetMETObjects')
    jecAK4_B = createJEC('JECs/Fall17_17Nov2017B_V6_DATA', ['L2Relative', 'L3Absolute', 'L2L3Residual'], 'AK4PFPuppi')
    jecAK8_B = createJEC('JECs/Fall17_17Nov2017B_V6_DATA', ['L2Relative', 'L3Absolute', 'L2L3Residual'], 'AK8PFPuppi')
    jecUncAK4_B = ROOT.JetCorrectionUncertainty(ROOT.std.string('JECs/Fall17_17Nov2017B_V6_DATA_Uncertainty_AK4PFPuppi.txt'))
    jecUncAK8_B = ROOT.JetCorrectionUncertainty(ROOT.std.string('JECs/Fall17_17Nov2017B_V6_DATA_Uncertainty_AK8PFPuppi.txt'))
    
    jecAK4_C = createJEC('JECs/Fall17_17Nov2017C_V6_DATA', ['L2Relative', 'L3Absolute', 'L2L3Residual'], 'AK4PFPuppi')
    jecAK8_C = createJEC('JECs/Fall17_17Nov2017C_V6_DATA', ['L2Relative', 'L3Absolute', 'L2L3Residual'], 'AK8PFPuppi')
    jecUncAK4_C = ROOT.JetCorrectionUncertainty(ROOT.std.string('JECs/Fall17_17Nov2017C_V6_DATA_Uncertainty_AK4PFPuppi.txt'))
    jecUncAK8_C = ROOT.JetCorrectionUncertainty(ROOT.std.string('JECs/Fall17_17Nov2017C_V6_DATA_Uncertainty_AK8PFPuppi.txt'))
    
    jecAK4_D = createJEC('JECs/Fall17_17Nov2017D_V6_DATA', ['L2Relative', 'L3Absolute', 'L2L3Residual'], 'AK4PFPuppi')
    jecAK8_D = createJEC('JECs/Fall17_17Nov2017D_V6_DATA', ['L2Relative', 'L3Absolute', 'L2L3Residual'], 'AK8PFPuppi')
    jecUncAK4_D = ROOT.JetCorrectionUncertainty(ROOT.std.string('JECs/Fall17_17Nov2017D_V6_DATA_Uncertainty_AK4PFPuppi.txt'))
    jecUncAK8_D = ROOT.JetCorrectionUncertainty(ROOT.std.string('JECs/Fall17_17Nov2017D_V6_DATA_Uncertainty_AK8PFPuppi.txt'))
    
    jecAK4_E = createJEC('JECs/Fall17_17Nov2017E_V6_DATA', ['L2Relative', 'L3Absolute', 'L2L3Residual'], 'AK4PFPuppi')
    jecAK8_E = createJEC('JECs/Fall17_17Nov2017E_V6_DATA', ['L2Relative', 'L3Absolute', 'L2L3Residual'], 'AK8PFPuppi')
    jecUncAK4_E = ROOT.JetCorrectionUncertainty(ROOT.std.string('JECs/Fall17_17Nov2017E_V6_DATA_Uncertainty_AK4PFPuppi.txt'))
    jecUncAK8_E = ROOT.JetCorrectionUncertainty(ROOT.std.string('JECs/Fall17_17Nov2017E_V6_DATA_Uncertainty_AK8PFPuppi.txt'))
    
    jecAK4_F = createJEC('JECs/Fall17_17Nov2017F_V6_DATA', ['L2Relative', 'L3Absolute', 'L2L3Residual'], 'AK4PFPuppi')
    jecAK8_F = createJEC('JECs/Fall17_17Nov2017F_V6_DATA', ['L2Relative', 'L3Absolute', 'L2L3Residual'], 'AK8PFPuppi')
    jecUncAK4_F = ROOT.JetCorrectionUncertainty(ROOT.std.string('JECs/Fall17_17Nov2017F_V6_DATA_Uncertainty_AK4PFPuppi.txt'))
    jecUncAK8_F = ROOT.JetCorrectionUncertainty(ROOT.std.string('JECs/Fall17_17Nov2017F_V6_DATA_Uncertainty_AK8PFPuppi.txt'))
    
    jecAK4_MC = createJEC('JECs/Fall17_17Nov2017_V6_MC', ['L2Relative', 'L3Absolute'], 'AK4PFPuppi')
    jecAK8_MC = createJEC('JECs/Fall17_17Nov2017_V6_MC', ['L2Relative', 'L3Absolute'], 'AK8PFPuppi')
    jecUncAK4_MC = ROOT.JetCorrectionUncertainty(ROOT.std.string('JECs/Fall17_17Nov2017_V6_MC_Uncertainty_AK4PFPuppi.txt'))
    jecUncAK8_MC = ROOT.JetCorrectionUncertainty(ROOT.std.string('JECs/Fall17_17Nov2017_V6_MC_Uncertainty_AK8PFPuppi.txt'))

    runnr_B = 299329
    runnr_C = 302029
    runnr_D = 303434
    runnr_E = 304826
    runnr_F = 306462


    ## __________.__.__                        __________                     .__       .__     __  .__                
    ## \______   \__|  |   ____  __ ________   \______   \ ______  _  __ ____ |__| ____ |  |___/  |_|__| ____    ____  
    ##  |     ___/  |  | _/ __ \|  |  \____ \   |       _// __ \ \/ \/ // __ \|  |/ ___\|  |  \   __\  |/    \  / ___\ 
    ##  |    |   |  |  |_\  ___/|  |  /  |_> >  |    |   \  ___/\     /\  ___/|  / /_/  >   Y  \  | |  |   |  \/ /_/  >
    ##  |____|   |__|____/\___  >____/|   __/   |____|_  /\___  >\/\_/  \___  >__\___  /|___|  /__| |__|___|  /\___  / 
    ##                        \/      |__|             \/     \/            \/  /_____/      \/             \//_____/  

    # Obtained on lxplus using this recipe:
    # https://twiki.cern.ch/twiki/bin/view/CMS/PileupJSONFileforData#2015_Pileup_JSON_Files
    # cmsrel (bla bla bla)
    # cp /afs/cern.ch/cms/CAF/CMSCOMM/COMM_DQM/certification/Collisions15/13TeV/PileUp/pileup_latest.txt .
    # cp /afs/cern.ch/cms/CAF/CMSCOMM/COMM_DQM/certification/Collisions15/13TeV/Cert_246908-260627_13TeV_PromptReco_Collisions15_25ns_JSON_Silver_v2.txt .
    # pileupCalc.py -i Cert_246908-260627_13TeV_PromptReco_Collisions15_25ns_JSON_Silver_v2.txt \
    #       --inputLumiJSON pileup_latest.txt --calcMode true --minBiasXsec 69000 --maxPileupBin 50 \
    #       --numPileupBins 50 MyDataPileupHistogram.root
    #
    # Then we compute our pileup distribution in MC ourselves, and divide data/MC, with these commands:
    # python makepu_fwlite.py --files inputfiles/ttjets.txt --maxevents 100000 
    # python makepuhist.py --file_data MyDataPileupHistogram.root --file_mc pumc.root --file_out purw.root
    #
    
    if not options.isData and not options.disablePileup:
        pileupReweightFile = ROOT.TFile('purw.root', 'READ')
        purw = pileupReweightFile.Get('pileup')


    # Lepton efficiencies and systematic uncertainties
    if not options.isData: 
        muonIDSFFile = ROOT.TFile('MuonID_Sys.root', 'READ')
        muonID_SFs = muonIDSFFile.Get('NUM_HighPtID_DEN_genTracks_pair_newTuneP_probe_pt_abseta')
        muonIsoSFFile = ROOT.TFile('MuonIso_Sys.root', 'READ')
        muonIso_SFs = muonIsoSFFile.Get('NUM_LooseRelTkIso_DEN_HighPtIDandIPCut_pair_newTuneP_probe_pt_abseta')
        muonTrigSFFile = ROOT.TFile('MuonTrigger_SF.root', 'READ')
        muonTrig_SFs = muonTrigSFFile.Get('Mu50_PtEtaBins/pt_abseta_ratio')

        
    ## ___________                    __    .____                         
    ## \_   _____/__  __ ____   _____/  |_  |    |    ____   ____ ______  
    ##  |    __)_\  \/ // __ \ /    \   __\ |    |   /  _ \ /  _ \\____ \ 
    ##  |        \\   /\  ___/|   |  \  |   |    |__(  <_> |  <_> )  |_> >
    ## /_______  / \_/  \___  >___|  /__|   |_______ \____/ \____/|   __/ 
    ##         \/           \/     \/               \/            |__|    


    # IMPORTANT : Run one FWLite instance per file. Otherwise,
    # FWLite aggregates ALL of the information immediately, which
    # can take a long time to parse. 

    def processEvent(iev, event):
        #print '--------- NEW EVENT ----------'

        evWeight = 1.0
        puWeight = 1.0
        genWeight = 1.0
        LepWeightID = 1.0
        LepWeightIDUnc = 0.0
        LepWeightIso = 1.0
        LepWeightIsoUnc = 0.0
        LepWeightTrig = 1.0
        LepWeightTrigUnc = 0.0
        runnr = event.eventAuxiliary().run()


        ##   ___ ___ .____  ___________                    .___ ___________.__.__   __                       
        ##  /   |   \|    | \__    ___/ _____    ____    __| _/ \_   _____/|__|  |_/  |_  ___________  ______
        ## /    ~    \    |   |    |    \__  \  /    \  / __ |   |    __)  |  |  |\   __\/ __ \_  __ \/  ___/
        ## \    Y    /    |___|    |     / __ \|   |  \/ /_/ |   |     \   |  |  |_|  | \  ___/|  | \/\___ \ 
        ##  \___|_  /|_______ \____|    (____  /___|  /\____ |   \___  /   |__|____/__|  \___  >__|  /____  >
        ##        \/         \/              \/     \/      \/       \/                      \/           \/
        if not options.disableTree:
            SemiLeptTrig.clear()
            for i in xrange(len(trigsToRun)):
                SemiLeptTrig.push_back(False)
        passTrig = False

        # Perform trigger selection
        event.getByLabel(triggerBitLabel, triggerBits)
        event.getByLabel(metfiltBitLabel, metfiltBits)
        

        if options.verbose:
            print "\nProcessing %d: run %6d, lumi %4d, event %12d" % (iev,event.eventAuxiliary().run(), event.eventAuxiliary().luminosityBlock(),event.eventAuxiliary().event())
            print "\n === TRIGGER PATHS ==="

        # Check the names of the triggers to see if any of "our" trigger fired
        names = event.object().triggerNames(triggerBits.product())

        # Get list of triggers that fired
        firedTrigs = []
        for itrig in xrange(triggerBits.product().size()):
            if triggerBits.product().accept(itrig):
                firedTrigs.append( itrig )

        for trig in firedTrigs:
            trigName = names.triggerName(trig)
            for itrigToRun in xrange(0,len(trigsToRun)):
                if trigsToRun[itrigToRun] in trigName:
                    if options.verbose:
                        print "Trigger ", trigName,  " PASSED "
                    passTrig = True
                    SemiLeptTrig[itrigToRun] = True

        if options.verbose:
            print "\n === MET FILTER PATHS ==="
        names2 = event.object().triggerNames(metfiltBits.product())
        passFilters = True

        for itrig in xrange(metfiltBits.product().size()):            
            if names2.triggerName(itrig) == "Flag_goodVertices" and not metfiltBits.product().accept(itrig):
                passFilters = False            
            if names2.triggerName(itrig) == "Flag_globalTightHalo2016Filter" and not metfiltBits.product().accept(itrig):
                passFilters = False            
            if names2.triggerName(itrig) == "Flag_HBHENoiseFilter" and not metfiltBits.product().accept(itrig):
                passFilters = False            
            if names2.triggerName(itrig) == "Flag_HBHENoiseIsoFilter" and not metfiltBits.product().accept(itrig):
                passFilters = False            
            if names2.triggerName(itrig) == "Flag_EcalDeadCellTriggerPrimitiveFilter" and not metfiltBits.product().accept(itrig):
                passFilters = False            
            if names2.triggerName(itrig) == "Flag_BadPFMuonFilter" and not metfiltBits.product().accept(itrig):
                passFilters = False            
            if names2.triggerName(itrig) == "Flag_BadChargedCandidateFilter" and not metfiltBits.product().accept(itrig):
                passFilters = False            
            if names2.triggerName(itrig) == "Flag_eeBadScFilter" and not metfiltBits.product().accept(itrig) and options.IsData:
                passFilters = False            
            if names2.triggerName(itrig) == "Flag_ecalBadCalibFilter" and not metfiltBits.product().accept(itrig):
                passFilters = False



        if not passFilters:
            return

        if not passTrig:
            return

        ##   ________                __________.__          __          
        ##  /  _____/  ____   ____   \______   \  |   _____/  |_  ______
        ## /   \  ____/ __ \ /    \   |     ___/  |  /  _ \   __\/  ___/
        ## \    \_\  \  ___/|   |  \  |    |   |  |_(  <_> )  |  \___ \ 
        ##  \______  /\___  >___|  /  |____|   |____/\____/|__| /____  >
        ##         \/     \/     \/                                  \/
        if not options.isData: 
            haveGenSolution = False
            isGenPresent = event.getByLabel( genLabel, gens )
            if isGenPresent:
                topQuark = None
                antitopQuark = None
                for igen,gen in enumerate( gens.product() ):
                    #if options.verbose:
                    #    print 'GEN id=%.1f, pt=%+5.3f' % ( gen.pdgId(), gen.pt() )
                    if gen.pdgId() == 6:
                        topQuark = gen
                    elif gen.pdgId() == -6:
                        antitopQuark = gen

                if topQuark != None and antitopQuark != None:
                    ttbarCandP4 = topQuark.p4() + antitopQuark.p4()
                    h_mttbar_true.Fill( ttbarCandP4.mass() )
                    haveGenSolution = True
                else:
                    if options.verbose:
                        print 'No top quarks, not filling mttbar'
            event.getByLabel( genInfoLabel, genInfo )
            genWeight = genInfo.product().weight()
            #print 'evWeight before multiplying with genWeight: %f' % (evWeight) 
            #evWeight *= genWeight
            #print 'evWeight after multiplying with genWeight: %f' % (evWeight) 

        ## ____   ____             __                    _________      .__                 __  .__               
        ## \   \ /   /____________/  |_  ____ ___  ___  /   _____/ ____ |  |   ____   _____/  |_|__| ____   ____  
        ##  \   Y   // __ \_  __ \   __\/ __ \\  \/  /  \_____  \_/ __ \|  | _/ __ \_/ ___\   __\  |/  _ \ /    \ 
        ##   \     /\  ___/|  | \/|  | \  ___/ >    <   /        \  ___/|  |_\  ___/\  \___|  | |  (  <_> )   |  \
        ##    \___/  \___  >__|   |__|  \___  >__/\_ \ /_______  /\___  >____/\___  >\___  >__| |__|\____/|___|  /
        ##               \/                 \/      \/         \/     \/          \/     \/                    \/ 


        event.getByLabel(vertexLabel, vertices)
        # Vertices
        NPV = len(vertices.product())
        if len(vertices.product()) == 0 or vertices.product()[0].ndof() < 4:
            if options.verbose:
                print "Event has no good primary vertex."
            return
        else:
            PV = vertices.product()[0]
            if options.verbose:
                print "PV at x,y,z = %+5.3f, %+5.3f, %+6.3f (ndof %.1f)" % (PV.x(), PV.y(), PV.z(), PV.ndof())

        ##   __________.__.__                        __________                     .__       .__     __  .__                
        ##   \______   \__|  |   ____  __ ________   \______   \ ______  _  __ ____ |__| ____ |  |___/  |_|__| ____    ____  
        ##    |     ___/  |  | _/ __ \|  |  \____ \   |       _// __ \ \/ \/ // __ \|  |/ ___\|  |  \   __\  |/    \  / ___\ 
        ##    |    |   |  |  |_\  ___/|  |  /  |_> >  |    |   \  ___/\     /\  ___/|  / /_/  >   Y  \  | |  |   |  \/ /_/  >
        ##    |____|   |__|____/\___  >____/|   __/   |____|_  /\___  >\/\_/  \___  >__\___  /|___|  /__| |__|___|  /\___  / 
        ##                          \/      |__|             \/     \/            \/  /_____/      \/             \//_____/  

        if not options.isData:
            event.getByLabel(pileuplabel, pileups)

            TrueNumInteractions = 0
            if len(pileups.product())>0:
                TrueNumInteractions = pileups.product()[0].getTrueNumInteractions()
            else:
                print 'Event has no pileup information, setting TrueNumInteractions to 0.'

            if not options.isData and not options.disablePileup:
                puWeight = purw.GetBinContent( purw.GetXaxis().FindBin( TrueNumInteractions ) )
                #print 'evWeight before multiplying with puWeight: %f' % (evWeight) 
                evWeight *= puWeight
                #print 'evWeight after multiplying with puWeight: %f' % (evWeight) 

        ## __________.__             ____   ____      .__                 
        ## \______   \  |__   ____   \   \ /   /____  |  |  __ __   ____  
        ##  |       _/  |  \ /  _ \   \   Y   /\__  \ |  | |  |  \_/ __ \ 
        ##  |    |   \   Y  (  <_> )   \     /  / __ \|  |_|  |  /\  ___/ 
        ##  |____|_  /___|  /\____/     \___/  (____  /____/____/  \___  >
        ##         \/     \/                        \/                 \/ 
        event.getByLabel(rhoLabel, rhos)
        # Rhos
        if len(rhos.product()) == 0:
            print "Event has no rho values."
            return
        else:
            rho = rhos.product()[0]
            if options.verbose:
                print 'rho = {0:6.2f}'.format( rho )



        ## .____                  __                    _________      .__                 __  .__               
        ## |    |    ____ _______/  |_  ____   ____    /   _____/ ____ |  |   ____   _____/  |_|__| ____   ____  
        ## |    |  _/ __ \\____ \   __\/  _ \ /    \   \_____  \_/ __ \|  | _/ __ \_/ ___\   __\  |/  _ \ /    \ 
        ## |    |__\  ___/|  |_> >  | (  <_> )   |  \  /        \  ___/|  |_\  ___/\  \___|  | |  (  <_> )   |  \
        ## |_______ \___  >   __/|__|  \____/|___|  / /_______  /\___  >____/\___  >\___  >__| |__|\____/|___|  /
        ##         \/   \/|__|                    \/          \/     \/          \/     \/                    \/ 



        event.getByLabel( muonLabel, muons )
        event.getByLabel( electronLabel, electrons )




        # Select tight good muons
        goodmuons = []
        if len(muons.product()) > 0:
            for i,muon in enumerate( muons.product() ):
                if muon.pt() > options.minMuonPt and abs(muon.eta()) < options.maxMuonEta and muon.muonBestTrack().dz(PV.position()) < 5.0 and muon.isHighPtMuon(PV) and muon.isolationR03().sumPt/muon.pt() < 0.1 :
                    goodmuons.append( muon )
                    if options.verbose:
                        print "muon %2d: pt %4.1f, eta %+5.3f phi %+5.3f dz(PV) %+5.3f, POG loose id %d, tight id %d, highpt id %d." % (
                            i, muon.pt(), muon.eta(), muon.phi(), muon.muonBestTrack().dz(PV.position()), muon.isLooseMuon(), muon.isHighPtMuon(PV))



        # Veto on dilepton events
        # Also keep track of the PF index of the lepton
        # for lepton-jet cleaning (see below)
        theLeptonObjKey = -1

        #if len(goodmuons) + len(goodelectrons) != 1:
            #return
        #elif len(goodmuons) > 0:
        if len(goodmuons) >= 1:
            theLeptonCand = goodmuons[0]
            theLepton = ROOT.TLorentzVector( goodmuons[0].px(),
                                             goodmuons[0].py(),
                                             goodmuons[0].pz(),
                                             goodmuons[0].energy() )
            theLeptonObjKey = goodmuons[0].originalObjectRef().key()
            leptonType = 13

            # Get the muon ID, Iso, and trigger scale factors for simulation
            # Start off with ID
            if not options.isData:
                pt = goodmuons[0].pt()
                eta = abs(goodmuons[0].eta())

                # ID scale factors
                overflow = False
                if pt >=120:
                    pt=119.9
                    overflow =True
                LepWeightID = muonID_SFs.GetBinContent( muonID_SFs.GetXaxis().FindBin( pt ), muonID_SFs.GetYaxis().FindBin( eta ) )
                LepWeightIDUnc =  muonID_SFs.GetBinError( muonID_SFs.GetXaxis().FindBin( pt ), muonID_SFs.GetYaxis().FindBin( eta ) )
                if overflow:
                    LepWeightIDUnc *=2
                #print 'evWeight before multiplying with LepWeightID: %f' % (evWeight) 
                evWeight *= LepWeightID
                #print 'evWeight after multiplying with LepWeightID: %f' % (evWeight) 



                # Muon Isolation scale factors
                overflow = False
                if pt >=120:
                    pt=119.9
                    overflow =True
                LepWeightIso = muonIso_SFs.GetBinContent( muonIso_SFs.GetXaxis().FindBin( pt ), muonIso_SFs.GetYaxis().FindBin( eta ) )
                LepWeightIsoUnc =  muonIso_SFs.GetBinError( muonIso_SFs.GetXaxis().FindBin( pt ), muonIso_SFs.GetYaxis().FindBin( eta ) )
                if overflow:
                    LepWeightIsoUnc *=2
                #print 'evWeight before multiplying with LepWeightIso: %f' % (evWeight) 
                evWeight *= LepWeightIso
                #print 'evWeight after multiplying with LepWeightIso: %f' % (evWeight) 

                # Muon trigger scale factors
                overflow = False
                if pt >=1200:
                    pt=1119.9
                    overflow =True
                LepWeightTrig = muonTrig_SFs.GetBinContent( muonTrig_SFs.GetXaxis().FindBin( pt ), muonTrig_SFs.GetYaxis().FindBin( eta ) )
                LepWeightTrigUnc =  muonTrig_SFs.GetBinError( muonTrig_SFs.GetXaxis().FindBin( pt ), muonTrig_SFs.GetYaxis().FindBin( eta ) )
                if overflow:
                    LepWeightTrigUnc *=2
                #print 'evWeight before multiplying with LepWeightTrig: %f' % (evWeight) 
                evWeight *= LepWeightTrig
                #print 'evWeight after multiplying with LepWeightTrig: %f' % (evWeight) 

        
        else:
            #print 'Event kicked because there are no good muons.'
            return

        # now get a list of the PF candidates used to build this lepton, so to exclude them
        footprint = set()
        for i in xrange(theLeptonCand.numberOfSourceCandidatePtrs()):
            footprint.add(theLeptonCand.sourceCandidatePtr(i).key()) # the key is the index in the pf collection




        ##      ____.       __      _________      .__                 __  .__               
        ##     |    | _____/  |_   /   _____/ ____ |  |   ____   _____/  |_|__| ____   ____  
        ##     |    |/ __ \   __\  \_____  \_/ __ \|  | _/ __ \_/ ___\   __\  |/  _ \ /    \ 
        ## /\__|    \  ___/|  |    /        \  ___/|  |_\  ___/\  \___|  | |  (  <_> )   |  \
        ## \________|\___  >__|   /_______  /\___  >____/\___  >\___  >__| |__|\____/|___|  /
        ##               \/               \/     \/          \/     \/                    \/ 

        #
        #
        #
        # Here, we have TWO jet collections, AK4 and AK8. The
        # AK4 jets are used for b-tagging, while the AK8 jets are used
        # for top-tagging.
        # In the future, the AK8 jets will contain "subjet b-tagging" in
        # miniAOD but as of now (Dec 2014) this is not ready so we
        # need to adjust.
        #
        #
        # In addition, we must perform "lepton-jet" cleaning.
        # This is because the PF leptons are actually counted in the
        # list of particles sent to the jet clustering.
        # Therefore, we need to loop over the jet constituents and
        # remove the lepton. 

        # use getByLabel, just like in cmsRun
        event.getByLabel (jetLabel, jets)          # For b-tagging
        event.getByLabel (ak8jetLabel, ak8jets)    # For top-tagging

        # loop over jets and fill hists
        ijet = 0

        # These will hold all of the jets we need for the selection
        ak4JetsGood = []
        ak8JetsGood = []
        ak4JetsGoodP4 = []
        ak8JetsGoodP4 = []
        ak4JetsGoodSysts = []
        ak8JetsGoodSysts = []

        # For selecting leptons, look at 2-d cut of dRMin, ptRel of
        # lepton and nearest jet that has pt > 30 GeV
        dRMin = 9999.0
        inearestJet = -1    # Index of nearest jet
        nearestJet = None   # Nearest jet


        ############################################
        # Get the AK4 jet nearest the lepton:
        ############################################
        for i,jet in enumerate(jets.product()):
            # Get the jet p4
            jetP4Raw = ROOT.TLorentzVector( jet.px(), jet.py(), jet.pz(), jet.energy() )
            # Get the correction that was applied at RECO level for MINIADO
            jetJECFromMiniAOD = jet.jecFactor(0)
            # Remove the old JEC's to get raw energy
            jetP4Raw *= jetJECFromMiniAOD
            # Apply jet ID
            nhf = jet.neutralHadronEnergy() / jetP4Raw.E()
            nef = jet.neutralEmEnergy() / jetP4Raw.E()
            chf = jet.chargedHadronEnergy() / jetP4Raw.E()
            cef = jet.chargedEmEnergy() / jetP4Raw.E()
            nconstituents = jet.numberOfDaughters()
            nch = jet.chargedMultiplicity()
            goodJet = \
              nhf < 0.99 and \
              nef < 0.99 and \
              chf > 0.00 and \
              cef < 0.99 and \
              nconstituents > 1 and \
              nch > 0

            if not goodJet:
                if options.verbose:
                    print 'bad jet pt = {0:6.2f}, y = {1:6.2f}, phi = {2:6.2f}, m = {3:6.2f}, bdisc = {4:6.2f}'.format (
                        jetP4Raw.Perp(), jetP4Raw.Rapidity(), jetP4Raw.Phi(), jetP4Raw.M(), jet.bDiscriminator( options.bdisc )
                        )
                continue



            if options.verbose:
                print 'raw jet pt = {0:6.2f}, y = {1:6.2f}, phi = {2:6.2f}, m = {3:6.2f}, bdisc = {4:6.2f}'.format (
                    jetP4Raw.Perp(), jetP4Raw.Rapidity(), jetP4Raw.Phi(), jetP4Raw.M(), jet.bDiscriminator( options.bdisc )
                    )


            # Remove the lepton from the list of constituents for lepton/jet cleaning
            # Speed up computation, only do this for DR < 0.6
            cleaned = False
            if theLepton.DeltaR(jetP4Raw) < 0.6:
                # Check all daughters of jets close to the lepton
                pfcands = jet.daughterPtrVector()
                for ipf,pf in enumerate( pfcands ):

                    # If any of the jet daughters matches the good lepton, remove the lepton p4 from the jet p4
                    if pf.key() in footprint:
                        if options.verbose:
                            print 'REMOVING LEPTON, pt/eta/phi = {0:6.2f},{1:6.2f},{2:6.2f}'.format(
                                theLepton.Perp(), theLepton.Eta(), theLepton.Phi()
                                )
                        if jetP4Raw.Energy() > theLepton.Energy():
                            jetP4Raw -= theLepton
                        else:
                            jetP4Raw -= theLepton
                            jetP4Raw.SetE(0.0)
                        cleaned = True
                        break

            # Apply new JEC's
            # Different JEC needs to be applied for each run period
            if not options.isData:
                (newJEC, corrDn, corrUp) = getJEC(jecAK8_MC, jecUncAK8_MC, jetP4Raw, jet.jetArea(), rho, NPV)
            elif runnr <= runnr_B:
                (newJEC, corrDn, corrUp) = getJEC(jecAK8_B, jecUncAK8_B, jetP4Raw, jet.jetArea(), rho, NPV)
            elif runnr <= runnr_C:
                (newJEC, corrDn, corrUp) = getJEC(jecAK8_C, jecUncAK8_C, jetP4Raw, jet.jetArea(), rho, NPV)
            elif runnr <= runnr_D:
                (newJEC, corrDn, corrUp) = getJEC(jecAK8_D, jecUncAK8_D, jetP4Raw, jet.jetArea(), rho, NPV)
            elif runnr <= runnr_E:
                (newJEC, corrDn, corrUp) = getJEC(jecAK8_E, jecUncAK8_E, jetP4Raw, jet.jetArea(), rho, NPV)
            elif runnr <= runnr_F:
                (newJEC, corrDn, corrUp) = getJEC(jecAK8_F, jecUncAK8_F, jetP4Raw, jet.jetArea(), rho, NPV)

            # If MC, get jet energy resolution
            ptsmear   = 1.0
            ptsmearUp = 1.0
            ptsmearDn = 1.0
            if not options.isData:
                # ---------------------------------------
                # JER
                # ---------------------------------------
                eta = jetP4Raw.Eta()
                if eta>=5.0:
                    eta=4.999
                if eta<=-5.0:
                    eta=-4.999
                smear     = getJER( eta,  0) 
                smearUp   = getJER( eta,  1) 
                smearDn   = getJER( eta, -1) 
                recopt    = jetP4Raw.Perp() * newJEC
                if jet.genJet() != None:
                    genpt     = jet.genJet().pt()
                    deltapt   = (recopt-genpt)*(smear-1.0)
                    deltaptUp = (recopt-genpt)*(smearUp-1.0)
                    deltaptDn = (recopt-genpt)*(smearDn-1.0)
                    ptsmear   = max(0.0, (recopt+deltapt)/recopt)
                    ptsmearUp = max(0.0, (recopt+deltaptUp)/recopt)
                    ptsmearDn = max(0.0, (recopt+deltaptDn)/recopt)


            jetP4 = jetP4Raw * newJEC * ptsmear
                
            # Now perform jet kinematic cuts
            if jetP4.Perp() < options.minAK4Pt or abs(jetP4.Rapidity()) > options.maxAK4Rapidity:
                continue

            # Get the jet nearest the lepton
            dR = jetP4.DeltaR(theLepton )
            ak4JetsGood.append(jet)
            ak4JetsGoodP4.append( jetP4 )
            ak4JetsGoodSysts.append( [corrUp, corrDn, ptsmearUp, ptsmearDn] )
            if options.verbose:
                print 'corrjet pt = {0:6.2f}, y = {1:6.2f}, phi = {2:6.2f}, m = {3:6.2f}, bdisc = {4:6.2f}'.format (
                    jetP4.Perp(), jetP4.Rapidity(), jetP4.Phi(), jetP4.M(), jet.bDiscriminator( options.bdisc )
                    )

            if dR < dRMin:
                inearestJet = ijet
                nearestJet = jet
                nearestJetP4 = jetP4
                dRMin = dR


        ############################################
        # Require at least one leptonic-side jet, and 2d isolation cut
        ############################################ 
        if nearestJet == None:
            return

        # Finally get the METs
        event.getByLabel( metLabel, mets )
        met = mets.product()[0]

        theLepJet = nearestJetP4
        theLepJetBDisc = nearestJet.bDiscriminator( options.bdisc )

        # Fill some plots related to the jets
        h_ptAK4.Fill( theLepJet.Perp(), evWeight )
        h_etaAK4.Fill( theLepJet.Eta(), evWeight )
        h_phiAK4.Fill( theLepJet.Phi(), evWeight )
        h_yAK4.Fill( theLepJet.Rapidity(), evWeight )
        h_mAK4.Fill( theLepJet.M(), evWeight )
        h_BDiscAK4.Fill( theLepJetBDisc, evWeight )
        # Fill some plots related to the lepton, the MET, and the 2-d cut
        ptRel = theLepJet.Perp( theLepton.Vect() )
        h_ptLep.Fill(theLepton.Perp(), evWeight)
        h_etaLep.Fill(theLepton.Eta(), evWeight)
        h_met.Fill(met.pt(), evWeight)
        h_ptRel.Fill( ptRel, evWeight )
        h_dRMin.Fill( dRMin, evWeight )
        h_2DCut.Fill( dRMin, ptRel, evWeight )
        pass2D = ptRel > 20.0 or dRMin > 0.4
        if options.verbose:
            print '2d cut : dRMin = {0:6.2f}, ptRel = {1:6.2f}, pass = {2:6d}'.format( dRMin, ptRel, pass2D )
        if not pass2D:
            return

        ############################################
        # Get the AK8 jet away from the lepton
        ############################################
        for i,jet in enumerate(ak8jets.product()):


            # perform jet ID with UNCORRECTED jet energy
            jetP4 = ROOT.TLorentzVector( jet.px(), jet.py(), jet.pz(), jet.energy() )
            jetP4Raw = copy.copy(jetP4)
            jetP4Raw *= jet.jecFactor(0)

            if not jet.isPFJet(): 
                return
            nhf = jet.neutralHadronEnergy() / jetP4Raw.E()
            nef = jet.neutralEmEnergy() / jetP4Raw.E()
            chf = jet.chargedHadronEnergy() / jetP4Raw.E()
            cef = jet.chargedEmEnergy() / jetP4Raw.E()
            nconstituents = jet.numberOfDaughters()
            nch = jet.chargedMultiplicity()
            goodJet = \
              nhf < 0.99 and \
              nef < 0.99 and \
              chf > 0.00 and \
              cef < 0.99 and \
              nconstituents > 1 and \
              nch > 0

            if not goodJet:
                return

            if not options.isData:
                (newJEC, corrDn, corrUp) = getJEC(jecAK8_MC, jecUncAK8_MC, jetP4Raw, jet.jetArea(), rho, NPV)
            elif runnr <= runnr_B:
                (newJEC, corrDn, corrUp) = getJEC(jecAK8_B, jecUncAK8_B, jetP4Raw, jet.jetArea(), rho, NPV)
            elif runnr <= runnr_C:
                (newJEC, corrDn, corrUp) = getJEC(jecAK8_C, jecUncAK8_C, jetP4Raw, jet.jetArea(), rho, NPV)
            elif runnr <= runnr_D:
                (newJEC, corrDn, corrUp) = getJEC(jecAK8_D, jecUncAK8_D, jetP4Raw, jet.jetArea(), rho, NPV)
            elif runnr <= runnr_E:
                (newJEC, corrDn, corrUp) = getJEC(jecAK8_E, jecUncAK8_E, jetP4Raw, jet.jetArea(), rho, NPV)
            elif runnr <= runnr_F:
                (newJEC, corrDn, corrUp) = getJEC(jecAK8_F, jecUncAK8_F, jetP4Raw, jet.jetArea(), rho, NPV)

            # If MC, get jet energy resolution
            ptsmear   = 1.0
            ptsmearUp = 1.0
            ptsmearDn = 1.0
            if not options.isData:
                # ---------------------------------------
                # JER
                # ---------------------------------------
                eta = jetP4Raw.Eta()
                if eta>=5.0:
                    eta=4.999
                if eta<=-5.0:
                    eta=-4.999
                smear     = getJER( eta,  0) 
                smearUp   = getJER( eta,  1) 
                smearDn   = getJER( eta, -1) 
                recopt    = jetP4Raw.Perp() * newJEC
                if jet.genJet() != None:
                    genpt     = jet.genJet().pt()
                    deltapt   = (recopt-genpt)*(smear-1.0)
                    deltaptUp = (recopt-genpt)*(smearUp-1.0)
                    deltaptDn = (recopt-genpt)*(smearDn-1.0)
                    ptsmear   = max(0.0, (recopt+deltapt)/recopt)
                    ptsmearUp = max(0.0, (recopt+deltaptUp)/recopt)
                    ptsmearDn = max(0.0, (recopt+deltaptDn)/recopt)

            jetP4 = jetP4Raw * newJEC * ptsmear   # Nominal JEC, nominal JER

            # Now perform jet kinematic cuts
            if jetP4.Perp() < options.minAK8Pt or abs(jetP4.Rapidity()) > options.maxAK8Rapidity:
                continue

            # Only keep AK8 jets "away" from the lepton, so we do not need
            # lepton-jet cleaning here. There's no double counting. 
            dR = jetP4.DeltaR(theLepton )
            if dR > ROOT.TMath.Pi()/2.0:
                ak8JetsGood.append(jet)
                ak8JetsGoodP4.append( jetP4 )
                ak8JetsGoodSysts.append( [corrUp, corrDn, ptsmearUp, ptsmearDn] )

        ## ___________                     .__                
        ## \__    ___/____     ____   ____ |__| ____    ____  
        ##   |    |  \__  \   / ___\ / ___\|  |/    \  / ___\ 
        ##   |    |   / __ \_/ /_/  > /_/  >  |   |  \/ /_/  >
        ##   |____|  (____  /\___  /\___  /|__|___|  /\___  / 
        ##                \//_____//_____/         \//_____/  

        ############################################
        # Investigate the b-tagging and t-tagging
        ############################################
        if len(ak4JetsGoodP4) < 1 or len(ak8JetsGoodP4) < 1:
            return


        tJets = []
        for ijet,jet in enumerate(ak8JetsGood):
            if jet.pt() < options.minAK8Pt:
                continue

            mAK8Softdrop = jet.userFloat('ak8PFJetsPuppiSoftDropMass')

            h_ptAK8.Fill( jet.pt(), evWeight )
            h_etaAK8.Fill( jet.eta(), evWeight )
            h_phiAK8.Fill( jet.phi(), evWeight )
            h_yAK8.Fill( jet.rapidity(), evWeight )
            h_mAK8.Fill( jet.mass(), evWeight )
            h_msoftdropAK8.Fill( mAK8Softdrop, evWeight )



            tJets.append( jet )


        ## ___________.__.__  .__    ___________                      
        ## \_   _____/|__|  | |  |   \__    ___/______   ____   ____  
        ##  |    __)  |  |  | |  |     |    |  \_  __ \_/ __ \_/ __ \ 
        ##  |     \   |  |  |_|  |__   |    |   |  | \/\  ___/\  ___/ 
        ##  \___  /   |__|____/____/   |____|   |__|    \___  >\___  >
        ##      \/                                          \/     \/ 
        if not options.disableTree:
            candToPlot = 0

            # Make sure there are top tags if we want to plot them
            tagInfoLabels = ak8JetsGood[candToPlot].tagInfoLabels()
            # Get n-subjettiness "tau" variables
            tau1 = ak8JetsGood[candToPlot].userFloat('NjettinessAK8Puppi:tau1')
            tau2 = ak8JetsGood[candToPlot].userFloat('NjettinessAK8Puppi:tau2')
            tau3 = ak8JetsGood[candToPlot].userFloat('NjettinessAK8Puppi:tau3')
            if tau1 > 0.0001:
                tau21 = tau2 / tau1
                h_tau21AK8.Fill( tau21, evWeight )
            else:
                h_tau21AK8.Fill( -1.0, evWeight )
            if tau2 > 0.0001:
                tau32 = tau3 / tau2
                h_tau32AK8.Fill( tau32, evWeight )
            else:
                h_tau32AK8.Fill( -1.0, evWeight )

            # Get the subjets 
            # The heaviest should correspond to the W and the lightest
            # should correspond to the b. 
            subjets = ak8JetsGood[candToPlot].subjets('SoftDropPuppi')
            subjetW = None
            subjetB = None
            if len(subjets) >= 2:
                if subjets[0].mass() > subjets[1].mass():
                    subjetW = subjets[0]
                    subjetB = subjets[1]
                else:
                    subjetB = subjets[0]
                    subjetW = subjets[1]
            else:
                return
            
            # calculate minimum pairwise mass of subjets
            minpwmass = 999999
            pwmass = 99999
            for idx_heavy in range(len(subjets)):
                for idx_light in range(len(subjets)):
                    if idx_heavy <= idx_light: continue
                    subjet_heavy_P4 = ROOT.TLorentzVector( subjets[idx_heavy].px(), subjets[idx_heavy].py(), subjets[idx_heavy].pz(), subjets[idx_heavy].energy() )
                    subjet_light_P4 = ROOT.TLorentzVector( subjets[idx_light].px(), subjets[idx_light].py(), subjets[idx_light].pz(), subjets[idx_light].energy() )
                    pwmass = (subjet_heavy_P4 + subjet_light_P4).M()
                if pwmass < minpwmass:
                    minpwmass = pwmass

            h_minmassAK8.Fill( minpwmass , evWeight )
            h_nsjAK8.Fill( len(subjets), evWeight )

            SemiLeptWeight      [0] = evWeight
            PUWeight            [0] = puWeight
            LeptonIDWeight      [0] = LepWeightID
            LeptonIDWeightUnc   [0] = LepWeightIDUnc
            LeptonIsoWeight     [0] = LepWeightIso
            LeptonIsoWeightUnc  [0] = LepWeightIsoUnc
            LeptonTrigWeight    [0] = LepWeightTrig
            LeptonTrigWeightUnc [0] = LepWeightTrigUnc
            GenWeight           [0] = genWeight
            FatJetPt            [0] = ak8JetsGoodP4[candToPlot].Perp()
            FatJetEta           [0] = ak8JetsGoodP4[candToPlot].Eta()
            FatJetPhi           [0] = ak8JetsGoodP4[candToPlot].Phi()
            FatJetRap           [0] = ak8JetsGoodP4[candToPlot].Rapidity()
            FatJetEnergy        [0] = ak8JetsGoodP4[candToPlot].Energy()
            FatJetMass          [0] = ak8JetsGoodP4[candToPlot].M()
            FatJetBDisc         [0] = ak8JetsGood[candToPlot].bDiscriminator(options.bdisc)
            FatJetMassSoftDrop  [0] = ak8JetsGood[candToPlot].userFloat('ak8PFJetsPuppiSoftDropMass')
            FatJetTau32         [0] = tau32
            FatJetTau21         [0] = tau21
            FatJetJECUpSys      [0] = ak8JetsGoodSysts[candToPlot][0]
            FatJetJECDnSys      [0] = ak8JetsGoodSysts[candToPlot][1]
            FatJetJERUpSys      [0] = ak8JetsGoodSysts[candToPlot][2]
            FatJetJERDnSys      [0] = ak8JetsGoodSysts[candToPlot][3]
            FatJetDeltaPhiLep   [0] = ak8JetsGoodP4[candToPlot].DeltaR(theLepton)
            if subjetW != None:
                FatJetSDBDiscW      [0] = subjetW.bDiscriminator(options.bdisc)
                FatJetSDBDiscB      [0] = subjetB.bDiscriminator(options.bdisc)
                FatJetSDsubjetWpt   [0] = subjetW.pt()
                FatJetSDsubjetWmass [0] = subjetW.mass()
                FatJetSDsubjetBpt   [0] = subjetB.pt()
                FatJetSDsubjetBmass [0] = subjetB.mass()
            LeptonType          [0] = leptonType
            LeptonPt            [0] = theLepton.Perp()  
            LeptonEta           [0] = theLepton.Eta()
            LeptonPhi           [0] = theLepton.Phi()
            LeptonEnergy        [0] = theLepton.E()
            LeptonPtRel         [0] = nearestJetP4.Perp(theLepton.Vect())
            LeptonDRMin         [0] = nearestJetP4.DeltaR(theLepton)
            SemiLepMETpt        [0] = met.pt()
            SemiLepMETphi       [0] = met.phi()   
            SemiLepNvtx         [0] = NPV
            NearestAK4JetBDisc  [0] = nearestJet.bDiscriminator(options.bdisc)
            NearestAK4JetPt     [0] = nearestJetP4.Perp()
            NearestAK4JetEta    [0] = nearestJetP4.Eta()
            NearestAK4JetPhi    [0] = nearestJetP4.Phi()
            NearestAK4JetMass   [0] = nearestJetP4.M()
            NearestAK4JetJECUpSys      [0] = ak4JetsGoodSysts[candToPlot][0]
            NearestAK4JetJECDnSys      [0] = ak4JetsGoodSysts[candToPlot][1]
            NearestAK4JetJERUpSys      [0] = ak4JetsGoodSysts[candToPlot][2]
            NearestAK4JetJERDnSys      [0] = ak4JetsGoodSysts[candToPlot][3]
            SemiLeptRunNum      [0] = event.object().id().run()
            SemiLeptLumiNum     [0] = event.object().luminosityBlock()
            SemiLeptEventNum    [0] = event.object().id().event()

            TreeSemiLept.Fill()
            #print 'Filled Tree!!'


    #########################################
    # Main event loop

    nevents = 0
    maxevents = int(options.maxevents)
    for ifile in getInputFiles(options):
        print 'Processing file ' + ifile
        events = Events (ifile)
        if maxevents > 0 and nevents > maxevents:
            break

        # loop over events in this file
        for iev, event in enumerate(events):

            if maxevents > 0 and nevents > maxevents:
                break
            nevents += 1

            if nevents % 1000 == 0:
                print '==============================================='
                print '    ---> Event ' + str(nevents)
            elif options.verbose:
                print '    ---> Event ' + str(nevents)

            processEvent(iev, events)

    f.cd()
    f.Write()
    f.Close()


if __name__ == "__main__":
    b2gdas_fwlite(sys.argv)
