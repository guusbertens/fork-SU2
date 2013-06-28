__all__ = ['Config','read_config','write_config','dump_config']


import os, sys, shutil, copy
import numpy as np
from collections import OrderedDict
from ..util import bunch, ordered_bunch, switch
from .tools import *

inf = 1.0e20

class Config(ordered_bunch):
    """ use 1: initialize by reading config file
            config = SU2.io.Config('filename')
        use 2: initialize from dictionary
            config = SU2.io.Config(param_dict)
        use 3: initialize empty
            config = SU2.io.Config()
        remembers order of config file
        
        parameter access by attribute or item
        ie: config['MESH_FILENAME'] or config.MESH_FILENAME
    """    

    _filename = 'config.cfg'
    
    def __init__(self,*args,**kwarg):
        
        # look for filename in inputs
        if args and isinstance(args[0],str):
            filename = args[0]
            args = args[1:]
        elif kwarg.has_key('filename'):
            filename = kwarg['filename']
            del kwarg['filename']
        else:
            filename = ''
        
        # initialize ordered bunch
        super(Config,self).__init__(*args,**kwarg)
        
        # read config if it exists
        if filename and os.path.exists(filename):
            self.read(filename)
        
        self._filename = filename
    
    def read(self,filename):
        konfig = read_config(filename)
        self.update(konfig)
        
    def write(self,filename=''):
        if not filename: filename = self._filename
        write_config(filename,self)
        
    def dump(self,filename=''):
        if not filename: filename = self._filename
        dump_config(filename,self)
    
    def __getattr__(self,k):
        try:
            return super(Config,self).__getattr__(k)
        except AttributeError:
            raise AttributeError , 'Config parameter not found'
        
    def __getitem__(self,k):
        try:
            return super(Config,self).__getitem__(k)
        except KeyError:
            raise KeyError , 'Config parameter not found'


    def unpack_dvs(self,dv_new,dv_old=[]):
        ''' update config with design variable vectors
            will scale according to each DEFINITION_DV scale parameter
        '''
        
        dv_new = copy.deepcopy(dv_new)
        dv_old = copy.deepcopy(dv_old)
        
        # handle unpacking cases
        def_dv = self['DEFINITION_DV']
        n_dv   = len(def_dv['KIND'])
        if not dv_old: dv_old = [0.0]*n_dv
        assert len(dv_new) == len(dv_old) , 'unexpected design vector length'
        
        # apply scale
        dv_scales = def_dv['SCALE']
        dv_new = [ dv_new[i]*dv_scl for i,dv_scl in enumerate(dv_scales) ]
        dv_old = [ dv_old[i]*dv_scl for i,dv_scl in enumerate(dv_scales) ]
        
        # Change the parameters of the design variables
        self.update({ 'DV_KIND'      : def_dv['KIND']      ,
                      'DV_MARKER'    : def_dv['MARKER'][0] ,
                      'DV_PARAM'     : def_dv['PARAM']     ,
                      'DV_VALUE_OLD' : dv_old              ,
                      'DV_VALUE_NEW' : dv_new              })
        
    def __eq__(self,konfig):
        return super(Config,self).__eq__(konfig)
    def __ne__(self,konfig):
        return super(Config,self).__ne__(konfig)
    
    def diff(self,konfig):
        
        keys = set([])
        keys.update( self.keys() )
        keys.update( konfig.keys() )
        
        konfig_diff = Config()
        
        for key in keys:
            value1 = self.get(key,None)
            value2 = konfig.get(key,None)
            if not value1 == value2:
                konfig_diff[key] = [value1,value2]
        
        return konfig_diff
    
    def dist(self,konfig,keys_check='ALL'):

        konfig_diff = self.diff(konfig)
        
        if keys_check == 'ALL':
            keys_check = konfig_diff.keys()
    
        distance = 0.0
        
        for key in keys_check:
            if konfig_diff.has_key(key):
                
                val1 = konfig_diff[key][0]
                val2 = konfig_diff[key][1]
                
                if key in ['DV_VALUE_NEW',
                           'DV_VALUE_OLD']:
                    val1 = np.array( val1 )
                    val2 = np.array( val2 )
                    this_diff = np.sqrt( np.sum( (val1-val2)**2 ) )
                
                else:
                    print 'Warning, unexpected config difference'
                    this_diff = inf
                    
                distance += this_diff
            
            #: if key different
        #: for each keys_check
        
        return distance
    
    def __repr__(self):
        #return '<Config> %s' % self._filename
        return self.__str__()
    
    def __str__(self):
        output = 'Config: %s' % self._filename
        for k,v in self.iteritems():
            output +=  '\n    %s= %s' % (k,v)
        return output
#: class Config

class OptionError(Exception):
    pass

class Option(object):
    
    def __init__(self):
        self.val = ""

    def __get__(self):
        return self.val

    def __set__(self,newval):
        self.val = newval

#: class Option

class MathProblem(Option):

    def __init__(self,*args,**kwarg):
        super(MathProblem,self).__init__(*args,**kwarg)
        self.validoptions = ['DIRECT','ADJOINT','LINEARIZED']

    def __set__(self,newval):
        if not self.newval in self.validoptions:
            raise OptionError("Invalid option. Valid options are: %s"%self.validoptions)
        super(MathProblem,self).__set__(newval)

#: class MathProblem


# -------------------------------------------------------------------
#  Get SU2 Configuration Parameters
# -------------------------------------------------------------------

def read_config(filename):
      
    # initialize output dictionary
    data_dict = OrderedDict() 
    
    input_file = open(filename)
    
    # process each line
    while 1:
        # read the line
        line = input_file.readline()
        if not line:
            break
        
        # remove line returns
        line = line.strip('\r\n')
        # make sure it has useful data
        if (not "=" in line) or (line[0] == '%'):
            continue
        # split across equals sign
        line = line.split("=",1)
        this_param = line[0].strip()
        this_value = line[1].strip()
        
        assert not data_dict.has_key(this_param) , ('Config file has multiple specifications of %s' % this_param )
        for case in switch(this_param):
            
            # comma delimited lists of strings with or without paren's
            if case("TASKS")          : pass
            if case("GRADIENTS")      : pass
            if case("DV_KIND")        : 
                # remove white space
                this_value = ''.join(this_value.split())   
                # split by comma
                data_dict[this_param] = this_value.split(",")
                break
            
            # semicolon delimited lists of comma delimited lists of floats
            if case("DV_PARAM"):
                # remove white space
                info_General = ''.join(this_value.split())
                # split by semicolon
                info_General = info_General.split(';')
                # build list of dv params, convert string to float
                dv_Parameters = []
                for this_dvParam in info_General:
                    this_dvParam = this_dvParam.strip('()')
                    this_dvParam = [ float(x) for x in this_dvParam.split(",") ]   
                    dv_Parameters = dv_Parameters + [this_dvParam]
                data_dict[this_param] = dv_Parameters
                break     
            
            # comma delimited lists of floats
            if case("DV_VALUE_OLD")    : pass
            if case("DV_VALUE_NEW")    :           
                # remove white space
                this_value = ''.join(this_value.split())                
                # split by comma, map to float, store in dictionary
                data_dict[this_param] = map(float,this_value.split(","))
                break              

            # float parameters
            if case("MACH_NUMBER")            : pass
            if case("AoA")                    : pass
            if case("FIN_DIFF_STEP")          : pass
            if case("WRT_SOL_FREQ")           :
                data_dict[this_param] = float(this_value)
                break   
            
            # boolean parameters
            if case("DECOMPOSED")             :
                this_value = this_value.upper()
                data_dict[this_param] = this_value == "TRUE" or this_value == "1"
                break 
            
            # int parameters
            if case("NUMBER_PART")            : pass
            if case("AVAILABLE_PROC")         : pass
            if case("EXT_ITER")               : pass
            if case("TIME_INSTANCES")         : pass
            if case("ADAPT_CYCLES")           :
                data_dict[this_param] = int(this_value)
                break                
            
            # unitary design variable definition
            if case("DEFINITION_DV"):
                # remove white space
                this_value = ''.join(this_value.split())                
                # split into unitary definitions
                info_Unitary = this_value.split(";")
                # process each Design Variable
                dv_Kind       = []
                dv_Scale      = []
                dv_Markers    = []
                dv_Parameters = []
                for this_General in info_Unitary:
                    if not this_General: continue
                    # split each unitary definition into one general definition
                    info_General = this_General.strip("()").split("|") # check for needed strip()?
                    # split information for dv Kinds
                    info_Kind    = info_General[0].split(",")
                    # pull processed dv values
                    this_dvKind       = get_dvKind( int( info_Kind[0] ) )     
                    this_dvScale      = float( info_Kind[1] )
                    this_dvMarkers    = info_General[1].split(",")
                    if this_dvKind=='MACH_NUMBER' or this_dvKind=='AOA':
                        this_dvParameters = []
                    else:
                        this_dvParameters = [ float(x) for x in info_General[2].split(",") ]                    
                    # add to lists
                    dv_Kind       = dv_Kind       + [this_dvKind]
                    dv_Scale      = dv_Scale      + [this_dvScale]
                    dv_Markers    = dv_Markers    + [this_dvMarkers]
                    dv_Parameters = dv_Parameters + [this_dvParameters]
                # store in a dictionary
                dv_Definitions = { 'KIND'   : dv_Kind       ,
                                   'SCALE'  : dv_Scale      ,
                                   'MARKER' : dv_Markers    ,
                                   'PARAM'  : dv_Parameters }
                # save to output dictionary
                data_dict[this_param] = dv_Definitions
                break  
            
            # unitary objective definition
            if case('OPT_OBJECTIVE'):
                # remove white space
                this_value = ''.join(this_value.split())                
                # split by scale
                this_value = this_value.split("*")
                this_name  = this_value[0]
                this_scale = 1.0
                if len(this_value) > 1:
                    this_scale = float( this_value[1] )
                this_def = { this_name : {'SCALE':this_scale} }
                # save to output dictionary
                data_dict[this_param] = this_def
                break
            
            # unitary constraint definition
            if case('OPT_CONSTRAINT'):
                # remove white space
                this_value = ''.join(this_value.split())                    
                # check for none case
                if this_value == 'NONE':
                    data_dict[this_param] = {'EQUALITY':OrderedDict(), 'INEQUALITY':OrderedDict()}
                    break                    
                # split definitions
                this_value = this_value.split(';')
                this_def = OrderedDict()
                for this_con in this_value:
                    if not this_con: continue # if no definition
                    # defaults
                    this_obj = 'NONE'
                    this_sgn = '='
                    this_scl = 1.0
                    this_val = 0.0
                    # split scale if present
                    this_con = this_con.split('*')
                    if len(this_con) > 1:
                        this_scl = float( this_con[1] )
                    this_con = this_con[0]
                    # find sign
                    for this_sgn in ['<','>','=']:
                        if this_sgn in this_con: break
                    # split sign, store objective and value
                    this_con = this_con.strip('()').split(this_sgn)
                    assert len(this_con) == 2 , 'incorrect constraint definition'
                    this_obj = this_con[0]
                    this_val = float( this_con[1] )
                    # store in dictionary
                    this_def[this_obj] = { 'SIGN'  : this_sgn ,
                                           'VALUE' : this_val ,
                                           'SCALE' : this_scl  }
                #: for each constraint definition
                # sort constraints by type
                this_sort = { 'EQUALITY'   : OrderedDict() ,
                              'INEQUALITY' : OrderedDict()  }
                for key,value in this_def.iteritems():
                    if value['SIGN'] == '=':
                        this_sort['EQUALITY'][key]   = value
                    else:
                        this_sort['INEQUALITY'][key] = value
                #: for each definition                
                # save to output dictionary
                data_dict[this_param] = this_sort
                break
            
            # otherwise
            # string parameters
            if case():
                data_dict[this_param] = this_value
                break              
            
            #: if case DEFINITION_DV
                        
        #: for case
        
    #: for line
            
    return data_dict
    
#: def read_config()



# -------------------------------------------------------------------
#  Set SU2 Configuration Parameters
# -------------------------------------------------------------------

def write_config(filename,param_dict):
    
    temp_filename = "temp.cfg"
    shutil.copy(filename,temp_filename)
    output_file = open(filename,"w")

    # break pointers
    param_dict = copy.deepcopy(param_dict)
    
    for raw_line in open(temp_filename):
        # remove line returns
        line = raw_line.strip('\r\n')
        
        # make sure it has useful data
        if not "=" in line:
            output_file.write(raw_line)
            continue
        
        # split across equals sign
        line = line.split("=")
        this_param = line[0].strip()
        old_value  = line[1].strip()
        
        # skip if parameter unwanted
        if not param_dict.has_key(this_param):
            output_file.write(raw_line)
            continue
        
        # start writing parameter
        new_value = param_dict[this_param] 
        output_file.write(this_param + "= ")
        
        # handle parameter types
        for case in switch(this_param):  
              
            # comma delimited list of floats
            if case("DV_VALUE_NEW") : pass
            if case("DV_VALUE_OLD") :
                n_lists = len(new_value)
                for i_value in range(n_lists):
                    output_file.write("%s" % new_value[i_value])
                    if i_value+1 < n_lists:
                        output_file.write(", ")               
                break
            
            # comma delimited list of strings no paren's
            if case("DV_KIND")            : pass
            if case("TASKS")              : pass
            if case("GRADIENTS")          :            
                if not isinstance(new_value,list):
                    new_value = [ new_value ]
                n_lists = len(new_value)
                for i_value in range(n_lists):
                    output_file.write(new_value[i_value])
                    if i_value+1 < n_lists:
                        output_file.write(", ")               
                break            
            
            # comma delimited list of strings inside paren's
            if case("DV_MARKER") : 
                if not isinstance(new_value,list):
                    new_value = [ new_value ]                
                output_file.write("( ")
                n_lists = len(new_value)
                for i_value in range(n_lists):
                    output_file.write(new_value[i_value])
                    if i_value+1 < n_lists:
                        output_file.write(", ")
                output_file.write(" )") 
                break                
            
            # semicolon delimited lists of comma delimited lists
            if case("DV_PARAM") :
                assert isinstance(new_value,list) , 'incorrect specification of DV_PARAM'
                if not isinstance(new_value[0],list): new_value = [ new_value ]
                for i_value in range(len(new_value)):
                    output_file.write("( ")
                    this_list = new_value[i_value]
                    n_lists = len(new_value[i_value])
                    for j_value in range(n_lists):
                        output_file.write("%s" % this_list[j_value])
                        if j_value+1 < n_lists:
                            output_file.write(", ")   
                    output_file.write(") ")
                    if i_value+1 < len(new_value):
                        output_file.write("; ")            
                break
            
            # int parameters
            if case("NUMBER_PART")            : pass
            if case("ADAPT_CYCLES")           : pass
            if case("TIME_INSTANCES")         : pass
            if case("AVAILABLE_PROC")         : pass
            if case("EXT_ITER")               :
                output_file.write("%i" % new_value)
                break
            
            # boolean parameters
            if case("DECOMPOSED")             :
                new_value = str(new_value).upper()
                output_file.write(new_value)
                break             
            
            if case("DEFINITION_DV") :
                n_dv = len(new_value['KIND'])
                if not n_dv:
                    output_file.write("NONE")
                for i_dv in range(n_dv):
                    this_kind = new_value['KIND'][i_dv]
                    output_file.write("( ")
                    output_file.write("%i , " % get_dvID(this_kind) )
                    output_file.write("%s " % new_value['SCALE'][i_dv])
                    output_file.write("| ")
                    # markers                  
                    n_mark = len(new_value['MARKER'][i_dv])
                    for i_mark in range(n_mark):                       
                        output_file.write("%s " % new_value['MARKER'][i_dv][i_mark])
                        if i_mark+1 < n_mark:
                            output_file.write(", ")
                    #: for each marker
                    if not this_kind in ['AOA','MACH_NUMBER']:
                        output_file.write(" | ")
                        # params                 
                        n_param = len(new_value['PARAM'][i_dv])
                        for i_param in range(n_param):
                            output_file.write("%s " % new_value['PARAM'][i_dv][i_param])
                            if i_param+1 < n_param:
                                output_file.write(", ")
                        #: for each param                    
                    output_file.write(" )")
                    if i_dv+1 < n_dv:
                        output_file.write("; ")
                #: for each dv
                break
            
            if case("OPT_OBJECTIVE"):
                assert len(new_value.keys())==1 , 'only one OPT_OBJECTIVE is currently supported'
                i_name = 0
                for name,value in new_value.iteritems():
                    if i_name>0: output_file.write("; ")
                    output_file.write( "%s * %s" % (name,value['SCALE']) )
                    i_name += 1
                break
            
            if case("OPT_CONSTRAINT"):
                i_con = 0
                for con_type in ['EQUALITY','INEQUALITY']:
                    this_con = new_value[con_type]
                    for name,value in this_con.iteritems():
                        if i_con>0: output_file.write("; ")
                        output_file.write( "( %s %s %s ) * %s" 
                                          % (name, value['SIGN'], value['VALUE'], value['SCALE']) ) 
                        i_con += 1
                    #: for each constraint
                #: for each constraint type
                if not i_con: output_file.write("NONE")
                break
            
            # default, assume string, integer or unformatted float 
            if case():
                output_file.write('%s' % new_value)
                break                         
                
        #: for case
        
        # remove from param dictionary
        del param_dict[this_param]
        
        # next line
        output_file.write("\n")        
        
    #: for each line
    
    # check that all params were used
    for this_param in param_dict.keys():
        if not this_param in ['JOB_NUMBER']:
            print ( 'Warning: Parameter %s not found in config file and was not written' % (this_param) )
        
    output_file.close()
    os.remove( temp_filename )
    
#: def write_config()


def dump_config(filename,config):
    ''' dumps a raw config file with all options in config
    '''
    config_file = open(filename,'w')
    # write dummy file
    for key in config.keys():
        config_file.write( '%s= 0 \n' % key )
    config_file.close()
    # dump data
    write_config(filename,config)    
