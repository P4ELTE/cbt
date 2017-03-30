import os
import logger as l
from invoke import invoke
import flow_rules_preparator as flow_prep

def configure_remote_vnf(nfpa, vnf_function, traffictype):
    '''
    Configure the remote vnf via pre-installed tools located on the
    same machine where NFPA is.

    :return: True - if success, False - if not

    '''

    config = nfpa.config
    log = l.getLogger(__name__, config['LOG_LEVEL'], config['app_start_date'],
                      config['LOG_PATH'])
    invoke1 = lambda cmd: invoke(command=cmd, logger=log,
                                 email_adapter=config['email_adapter'])
    
    #the path to the openflow rules
    of_path = config["MAIN_ROOT"] + "/of_rules/"
    # temporary variable for bidir status - it is needed for flow_rules_preparator
    bidir = False

    # first, delete the flows
    ofctl_cmd = config["control_path"] + " " + \
                config["control_args"] +\
                " <C> " + \
                config["control_mgmt"] + " "
    cmd = ofctl_cmd.replace("<C>", "del-flows")
    log.debug("control cmd: %s" % cmd)
    invoke1(cmd)
    log.info("Flow rules deleted")

    # second, delete groups
    cmd = ofctl_cmd.replace("<C>", "del-groups")
    log.debug("control cmd: %s" % cmd)
    invoke1(cmd)
    log.info("Groups deleted")

    #OK, flows are deleted, so replace 'del-flows' to 'add-flows' for
    # easier usage later
    cmd = ofctl_cmd.replace("<C>", "add-flows")
    #first check vnf_function, if it is bridge, then no special stuff needs
    #to be setup regardless of the traces
    ############     BRIDGE ###########
    if config["vnf_function"].lower() == "bridge":
        #add birdge rules - located under of_rules
        scenario_path = vnf_function + "_unidir.flows"
        if not (os.path.isfile(str(of_path + scenario_path))):
            log.error("Missing flow rule file: %s" % scenario_path)
            log.error("NFPA does not know how to configure VNF to act as a bridge")
            log.error("More info: http://ios.tmit.bme.hu/nfpa")
            if (config['email_adapter'] is not None) and \
                (not config['email_adapter'].sendErrorMail()):
                log.error("Sending ERROR email did not succeed...")
            exit(-1)

        if config["biDir"] == 1:
            #change flow rule file if bidir was set
            scenario_path = scenario_path.replace("unidir","bidir")
            bidir=True

        #prepare flow rule file
        scenario_path = flow_prep.prepareOpenFlowRules(log,
                                                       of_path,
                                                       scenario_path,
                                                       config["control_vnf_inport"],
                                                       config["control_vnf_outport"],
                                                       bidir)
        cmd = ofctl_cmd.replace("<C>","add-flows") + scenario_path
        log.info("add-flows via '%s'" % cmd)
        invoke1(cmd)
        # print out stdout if any
        log.info("Flows added")
        return True
    ############    =============   ###########


    ############     OTHER CASES    ###########
    #check whether flow rules exists?
    #convention vnf_function.trace_direction.flows
    scenario_path = vnf_function + "." + traffictype + "_unidir.flows"
    if not (os.path.isfile(str(of_path + scenario_path))):
        log.error("Missing flow rule file: %s" % scenario_path)
        log.error("NFPA does not know how to configure VNF to act as " + \
                       "%s for the given trace %s" % (vnf_function,traffictype))
        log.error("More info: http://nfpa.tmit.bme.hu")
        if (config['email_adapter'] is not None) and \
            (not config['email_adapter'].sendErrorMail()):
            log.error("Sending ERROR email did not succeed...")
        exit(-1)


    #If flow file exists try to find corresponding groups
    scenario_path = scenario_path.replace(".flows",".groups")
    log.info("Looking for group file: %s" % scenario_path)
    if (os.path.isfile(str(of_path + scenario_path))):
        log.info("Group file found for this scenario: %s" % scenario_path)
        #prepare group file, i.e., replace port related meta data
        group_path = flow_prep.prepareOpenFlowRules(log,
                                                       of_path,
                                                       scenario_path,
                                                       config["control_vnf_inport"],
                                                       config["control_vnf_outport"],
                                                       False) #TODO: bidir handling here
        cmd = ofctl_cmd.replace("<C>","add-groups")
        cmd += " " + group_path
        log.info("add-groups via '%s'" % cmd)
        invoke1(cmd)
    else:
        log.info("No group file was found...continue")

    #change back to the .flows file from .groups
    scenario_path = scenario_path.replace(".groups", ".flows")

    #if biDir is set, then other file is needed where the same rules are present
    #in the reverse direction
    if (int(config["biDir"]) == 1):
        #biDir for remote vnf configuration is currently not supported!
        log.error("Configuring your VNF by NFPA for bi-directional scenario " +
                       "is currently not supported")
        log.error("Please verify your nfpa.cfg")
        if (config['email_adapter'] is not None) and \
            (not config['email_adapter'].sendErrorMail()):
            log.error("Sending ERROR email did not succeed...")
        exit(-1)
        #save biDir setting in a boolean to later use for flow_prep.prepareOpenFlowRules()
        # bidir = True
        # scenario_path=scenario_path.replace("unidir","bidir")
        # if not (os.path.isfile(str(of_path + scenario_path))):
        #     log.error("Missing flow rule file: %s" % scenario_path)
        #     log.error("NFPA does not know how to configure VNF to act as " + \
        #                    "%s for the given trace %s in bi-directional mode" %
        #                    (vnf_function,traffictype))
        #     log.error("More info: http://ios.tmit.bme.hu/nfpa")
        #     exit(-1)

    #replace metadata in flow rule files
    scenario_path = flow_prep.prepareOpenFlowRules(log,
                                                   of_path,
                                                   scenario_path,
                                                   config["control_vnf_inport"],
                                                   config["control_vnf_outport"],
                                                   bidir)
    #assemble command ovs-ofctl
    cmd = ofctl_cmd.replace("<C>","add-flows") + scenario_path
    log.info("add-flows via '%s'" % cmd)
    log.info("This may take some time...")
    invoke1(cmd)
    log.info("Flows added")
    return True
