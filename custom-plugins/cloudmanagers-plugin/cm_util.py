import ConfigParser
from synapse.logger import logger
from synapse.resources.resources import ResourceException

log = logger('cm_util')

def read_config_file(file_name):
    '''
    Returns a parsed configuration file.

    @param file_name: the path to the configuration file
    @type file_name: str
    '''
    log.info("fonction read_config_file")
    config = ConfigParser.ConfigParser()

    try:
        ret = config.read(file_name)
        if not ret:
            raise ResourceException("The configuration file '%s' doesn't exist"
                                    % file_name)
    except ConfigParser.MissingSectionHeaderError:
        raise ResourceException("Couldn't parse configuration file '%s'" %
                                file_name)

    return config
    
#-----------------------------------------------------------------------------


def get_config_option(res_id, option, config_path):
    '''
    Retrieves an option in a configuration file.

    @param res_id: the hypervisor's id corresponding to a section in the
                    configuration file
    @type res_id: str

    @param option: the option to retrieve the value
    @type option: str

    @param config_path: the path to the configuration file
    @type config_path: str
    '''
    # Retrive the configuration file
    config = read_config_file(config_path)

    # If the section exists in the configuration file
    if config.has_section(res_id):
        try:
            # Return the value of the given option
            return config.get(res_id, option)
        except ConfigParser.NoOptionError:
            raise ResourceException("The option '%s' doesn't exist in "
                                    "libvirt configuration file." % option)
    else:
        raise ResourceException("The cloud manager '%s' doesn't exist in the "
                                "configuration file." % res_id)

#-----------------------------------------------------------------------------
