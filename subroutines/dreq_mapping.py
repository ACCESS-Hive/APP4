# This script compares a CMIP6 data request with the master variable mapping file
# to determine how to process each variable requested for each experiment
# 
# Added to the APP for the ACCESS-CMIP6 sumbission by Chloe Mackallah
# March 2019
#
import numpy as np
import csv
import glob
import os
import re
import sys
import ast
import argparse
np.set_printoptions(threshold=sys.maxsize)

parser = argparse.ArgumentParser(description='Create variable mapping files')
parser.add_argument('--multi', dest='multi', default=False, action='store_true',
                    help='For use when running APP in parallel')
args = parser.parse_args()

UM_realms=['atmos','land','aerosol','atmosChem','landIce']
MOM_realms=['ocean','ocnBgchem']
CICE_realms=['seaIce']
UM_tables=['3hr','AERmon','AERday','CFmon',\
    'Eday','Eyr','fx','6hrLev','Amon','E3hr','Efx',\
    'LImon','day','6hrPlev','6hrPlevPt','CF3hr','E3hrPt','Emon',\
    'Lmon','EdayZ','EmonZ']
MOM_tables=['Oclim','Omon','Oday','Oyr','Ofx','Emon','Eyr','3hr']   
CICE_tables=['SImon','SIday']
CMIP_tables=UM_tables+MOM_tables+CICE_tables

#multilist=os.environ.get('MULTI_LIST')
priorityonly=os.environ.get('PRIORITY_ONLY')
prioritylist=os.environ.get('PRIORITY_LIST')
restricttoincomplete=os.environ.get('RESTRICT_TO_INCOMPLETE')
subdaily=os.environ.get('SUBDAILY')
yearly=os.environ.get('YEARLY')
daymon=os.environ.get('DAYMON')
co2amon=os.environ.get('CO2AMON')
completedlist=os.environ.get('COMPLETED_LIST')
experimentstable=os.environ.get('EXPERIMENTS_TABLE')
exptoprocess=os.environ.get('EXP_TO_PROCESS')
tabletoprocess=os.environ.get('TABLE_TO_PROCESS')
variabletoprocess=os.environ.get('VARIABLE_TO_PROCESS')
master_map=os.environ.get('MASTER_MAP')
outpath=os.environ.get('VARIABLE_MAPS')
forcedreq=os.environ.get('FORCE_DREQ')
try:    tabletoprocess
except:    tabletoprocess='all'
try:    variabletoprocess
except:    variabletoprocess='all'

try:
    with open(experimentstable,'r') as f:
        reader=csv.reader(f, delimiter=',')
        for row in reader:
            try: row[0]
            except: row='#'
            if row[0].startswith('#'): pass
            elif row[0] == exptoprocess:
                access_version=row[7]
                if forcedreq.lower() in ['yes','true','1']: 
                    dreq='input_files/dreq/cmvme_all_piControl_3_3.csv'
                else: dreq=row[3]
                reference_date=row[4]
                start_year=row[5]
                end_year=row[6]
                local_exp_dir=row[1]
    f.close()
    if access_version.find('OM2') != -1:
        print('ACCESS-OM2, using master_map_om2.csv')
        master_map=master_map.replace('.csv','_om2.csv')
    dreq
except:
    if os.path.exists(experimentstable):
        sys.exit('E: check experiment and experiments table')
    else:
        sys.exit('E: no experiments table')

if os.path.exists(local_exp_dir+'/atm/netCDF/link/'): atm_file_struc='/atm/netCDF/link/'
else: atm_file_struc='/atm/netCDF/'

priority_vars=[]
try:
    with open(prioritylist,'r') as p:
        reader=csv.reader(p, delimiter=',')
        for row in reader:
            try: row[0]
            except: row='#'
            if row[0].startswith('#'): pass
            else:
                priority_vars.append([row[0],row[1]])
    p.close()
except:
    if priorityonly.lower() in ['yes','true','1']:
        print 'no priority list for local experiment \'{}\', processing all variables'.format(exptoprocess)

completed_vars=[]
try:
    with open(completedlist,'r') as c:
        reader=csv.reader(c, delimiter=',')
        for row in reader:
            try: row[0]
            except: row='#'
            if row[0].startswith('#'): pass
            else:
                completed_vars.append([row[0],row[1],row[2],row[3]])
    c.close()
except:
    if restricttoincomplete.lower() in ['yes','true','1']:
        print 'no completed list for local experiment \'{}\', processing all variables'.format(exptoprocess)

def check_table():
    if tabletoprocess in CMIP_tables:
        pass
    elif tabletoprocess == 'all':
        pass
    else:
        sys.exit('table \'{}\' not in CMIP_tables list. Check spelling of table, or CMIP_tables list in \'{}\''.format(tabletoprocess,os.path.basename(__file__)))

def check_output_directory(path):
    if len(glob.glob('{}/*.csv'.format(path))) == 0:
        print 'variable map directory: \'{}\''.format(path)
    else:
        for file in glob.glob('{}/*.csv'.format(path)):
            os.remove('{}'.format(file))
        print 'variable maps deleted from directory \'{}\''.format(path)

def check_path(path):
    if os.path.exists('{}'.format(path)):
        print 'found directory \'{}\''.format(path)
    else:
        try:
            os.makedirs('{}'.format(path))
            print 'created directory \'{}\''.format(path)
        except OSError as e:
            sys.exit('failed to create directory \'{}\'; please create manually. \nexiting.'.format(path))

def check_file(file):
    if os.path.exists('{}'.format(file)):
        print 'found file \'{}\''.format(file)
    else:
        sys.exit('file \'{}\' does not exist!'.format(file))

def find_cmip_tables(dreq):
    tables=[]
    with open(dreq,'r') as f:
        reader=csv.reader(f, delimiter='\t')
        for row in reader:
            if not row[0] in tables:
                if (row[0] != 'Notes') and (row[0] != 'MIP table') and (row[0] != '0'):
                    if (row[0].find('hr') != -1):
                        if (subdaily.lower() in ['yes','true','1']): tables.append(row[0])
                    elif (row[0].find('yr') != -1):
                        if (yearly.lower() in ['yes','true','1']): tables.append(row[0])
                    else: 
                        if (daymon.lower() in ['yes','true','1']): tables.append(row[0])
    f.close()
    return tables

def special_cases(exptoprocess,cmipvar,freq,axes_modifier,calculation,realm,realm2,table,timeshot,access_vars,skip,access_version):
    #tasmin/tasmax:
    if cmipvar in ['tasmin','tasmax']:
        if freq == 'mon':
            freq='day'
        else:
            axes_modifier=''
            calculation=''
    #prsn:
    if cmipvar == 'prsn':
        if realm2 == 'ocean':
            if table == 'Omon':
                realm='ocean'
                skip=''
            elif table != 'Omon':
                skip='skip'
        elif realm2 == 'atmos':
            if table == 'Omon':
                skip='skip'
            elif table != 'Omon':
                realm='atmos'
                skip=''
    #sea_ice vars in UM output:
    if realm in CICE_realms:
        if access_vars.find('fld_') != -1:
            realm='atmos'
    #6hrLev cases:
    if cmipvar in ['ta','ua','va','hus']:
        if table.find('6hrLev') != -1:
            if axes_modifier.find('6hrLev') != -1:
                skip=''
            else:
                skip='skip'
        elif table.find('3hr') != -1:
            if axes_modifier.find('3hr') != -1:
                skip=''
            else:
                skip='skip'
        else:
            if axes_modifier.find('6hrLev') != -1 or axes_modifier.find('3hr') != -1:
                skip='skip'
            else:
                skip=''
    #3hr cases:
    if cmipvar in ['ts']:
        if table.find('3hr') != -1: skip='skip'
        else: pass        
    if cmipvar in ['tos']:
        if table.find('3hr') != -1:
            if axes_modifier.find('3hr') != -1:
                skip=''
                realm='atmos'
            else:
                skip='skip'
        else:
            if axes_modifier.find('3hr') != -1:
                skip='skip'
            else:
                skip=''
    #[O,E]yr cases:
    if table.find('yr') != -1:
        if access_vars.find('_raw') != -1 or access_version == 'OM2-025':
            pass
        elif timeshot == 'inst':
            axes_modifier='{} yrpoint'.format(axes_modifier)
        else:
            axes_modifier='{} mon2yr'.format(axes_modifier)
    #sfdsi:
    if cmipvar == 'sfdsi':
        if realm == 'ocean':
            if realm2 == 'ocean':
                skip=''
            else:
                skip='skip'
        elif realm == 'seaIce':
            if realm2 == 'seaIce':
                skip=''
            else:
                skip='skip'
    #ocnbgchem in CM2:
    if realm == 'ocnBgchem' and access_version == 'CM2':
        skip='skip'
    #prra:
    if cmipvar == 'prra':
        realm='ocean'
    #sbl:
    if cmipvar == 'sbl':
        if table.find('LImon') != -1: 
            if axes_modifier.find('LImon') != -1:
                skip=''
            else:
                skip='skip'
        else: 
            if axes_modifier.find('LImon') != -1:
                skip='skip'
            else:
                skip=''
    #nbp:
    if cmipvar == 'nbp':
        if exptoprocess.find('-EDC-') != -1:
            access_vars='fld_s03i100'
            calculation='landmask(var[0])*-12/44'
        elif exptoprocess.find('PI-') != -1:
            access_vars='fld_s03i262 fld_s03i293'
            calculation='var[0]-var[1]'
        else: pass
    #SIday in ESM:
    if table.find('SIday') != -1 and access_version.find('ESM') != -1:
        skip='skip'
    #E[day,mon]z:
    if (table.find('EdayZ') != -1) or (table.find('EmonZ') != -1):
        if calculation == '':
            calculation='zonal_mean(var[0])'
            axes_modifier='{} dropX'.format(axes_modifier)
        else:
            calculation='zonal_mean({})'.format(calculation)
            axes_modifier='{} dropX'.format(axes_modifier)
    #co2,Amon:
    if cmipvar == 'co2' and table == 'Amon':
        if not (co2amon.lower() in ['yes','true','1']): 
            skip='skip'
    return freq,axes_modifier,calculation,realm,realm2,timeshot,access_vars,skip

def determine_dimension(freq,dimensions,timeshot,realm,table,skip):
    if skip == 'skip':
        dimension=''
    elif (freq == 'fx') or (dimensions.find('time') == -1):
        dimension='fx'
    elif (timeshot == 'clim') or (dimensions.find('time2') != -1):
        dimension='clim'
    elif len(dimensions.split()) == 1:
        dimension='scalar'
    elif dimensions.find('alev') != -1:
        if realm in UM_realms:
            dimension='3Dalev'
        else:
            raise Exception('E: realm not identified')
    elif dimensions.find('plev') != -1:
        if realm in UM_realms:
            dimension='3Datmos'
        else:
            raise Exception('E: realm not identified')
    elif dimensions.find('olev') != -1:
        if realm in MOM_realms:
            dimension='3Docean'
        else:
            raise Exception('E: realm not identified')
    elif dimensions.find('sdepth') != -1:
        if realm in UM_realms:
            if dimensions.find('sdepth1') != -1:
                dimension='2Datmos'
            else:
                dimension='3Datmos'
        else:
            raise Exception('E: realm not identified')
    else:
        if realm in UM_realms:
            dimension='2Datmos'
        elif realm in MOM_realms:
            dimension='2Docean'
        elif realm in CICE_realms:
            dimension='2Dseaice'
        else:
            raise Exception('E: no dimension identified')
    return dimension

def reallocate_years(years,reference_date):
    reference_date=int(reference_date)
    if reference_date < 1850:
        years=[year-1850+reference_date for year in years]
    else: pass
    return years
        
def read_dreq_vars(dreq,table):
    with open(dreq,'r') as f:
        reader=csv.reader(f, delimiter='\t')
        dreq_variables=[]
        for row in reader:
            try:
                if (row[0] == table) and (row[12] != ''):
                    dimensions=row[11]
                    cmorname=row[12]
                    freq=row[14]
                    cfname=row[7]
                    realms=row[13]
                    try: realm=realms.split()[0]
                    except: realm='uncertain'
                    try:
                        if row[31].find('range') != -1:
                            years=reallocate_years(eval(row[31]),reference_date)
                            years='"{}"'.format(years)
                        elif row[31].find('All') != -1:
                            years='all'
                        else:
                            try: 
                                years=ast.literal_eval(row[31])
                                years=reallocate_years(years,reference_date)
                                years='"{}"'.format(years)
                            except: years='all'
                    except: years='all'
                    if variabletoprocess.lower() == 'all':
                        dreq_variables.append([cmorname,realm,freq,cfname,years,dimensions])
                    else:
                        if cmorname == variabletoprocess:
                            dreq_variables.append([cmorname,realm,freq,cfname,years,dimensions])
            except: pass
    f.close()
    return dreq_variables

def priority_check(cmipvar,table):
    priority_ret=0
    if priorityonly.lower() in ['yes','true','1']:
        for item in priority_vars:
            if (cmipvar == item[0]) and (table == item[1]):
                priority_ret=1
            else:
                pass
    else:
        priority_ret=1
    return priority_ret

def completed_check(cmipvar,table):
    completed_ret=1
    if restricttoincomplete.lower() in ['yes','true','1']:
        for item in completed_vars:
            if (cmipvar == item[1]) and (table == item[0]):
                completed_ret=0
            else:
                pass
    else:
        pass
    return completed_ret

def find_matches(table,master_map,cmorname,realm,freq,cfname,years,dimensions,matches,nomatches):
    matchlist=[]
    skiplist=[]
    if 'Pt' in freq:
        timeshot='inst'
        freq=str(freq)[:-2]
    elif freq == 'monC':
        timeshot='clim'
        freq='mon'
    else:
        timeshot='mean'
    with open(master_map,'r') as g:
        champ_reader=csv.reader(g, delimiter=',')
        for row in champ_reader:
            skip=''
            try: row[0]
            except: row='#'
            if row[0].startswith('#'): pass
            elif (row[0] == cmorname) and ((row[7] == access_version) or (row[7] == 'both')):
                cmipvar=row[0]
                definable=row[1]
                access_vars=row[2]
                calculation=row[3]
                if ',' in calculation:
                    calculation='"{}"'.format(calculation)
                units=row[4]
                axes_modifier=row[5]
                positive=row[6]
                realm2=row[8].split()[0]
                if realm == 'uncertain': realm = realm2
                #elif realm != realm2: realm = realm2
                var_notes=row[9]
                #check for special cases
                freq,axes_modifier,calculation,realm,realm2,timeshot,access_vars,skip=special_cases(exptoprocess,cmipvar,freq,axes_modifier,calculation,realm,realm2,table,timeshot,access_vars,skip,access_version)
                try: dimension=determine_dimension(freq,dimensions,timeshot,realm,table,skip)
                except: raise Exception('E: realm not identified')
                priority_ret=priority_check(cmipvar,table)
                completed_ret=completed_check(cmipvar,table)
                if priority_ret == 0 or completed_ret == 0:
                    skip='skip'
                if skip == 'skip':
                    file_structure=None
                    if not cmorname in skiplist:
                        skiplist.append(cmipvar)
                elif realm in UM_realms:
                    if freq in ['yr','mon','fx']:
                        file_structure=atm_file_struc+'*_mon.nc'
                    elif freq == 'day':
                        if table.find('EdayZ') != -1:
                            #file_structure='/atm/netCDF/plev19_daily/link/*_dai.nc'
                            file_structure=atm_file_struc+'*_dai.nc_zonal'
                        else:
                            file_structure=atm_file_struc+'*_dai.nc'
                    elif freq == '3hr':
                        file_structure=atm_file_struc+'*_3h.nc'
                    elif freq == '6hr':
                        file_structure=atm_file_struc+'*_6h.nc'
                    else:
                        #Unknown atmospheric frequency
                        file_structure=None
                elif realm == 'ocean':
                    if 'scalar' in axes_modifier:
                        file_structure='/ocn/ocean_scalar.nc-*'
                    elif freq == 'mon':
                        file_structure='/ocn/ocean_month.nc-*'
                    elif freq == 'yr':
                        if access_version == 'OM2-025':
                            file_structure='/ocn/ocean_budget.nc-*'
                        else:
                            file_structure='/ocn/ocean_month.nc-*'
                    elif freq == 'fx':
                        if access_version == 'OM2-025':
                            file_structure='/ocn/ocean_grid.nc-*'
                        else:
                            file_structure='/ocn/ocean_month.nc-*'
                    elif freq == 'day':
                        file_structure='/ocn/ocean_daily.nc-*'
                    else:
                        #Unknown ocean frequency
                        file_structure=None
                elif realm == 'ocnBgchem':
                    if access_vars.find('_raw') != -1:
                        if freq in ['mon']:
                            file_structure='/ocn/ocean_bgc_mth.nc-*'
                        elif freq in ['yr']:
                            file_structure='/ocn/ocean_bgc_ann.nc-*'
                        elif freq in ['day']:
                            file_structure='/ocn/ocean_bgc_daily.nc-*'
                        else:
                            #Unknown ocnBgchem frequency
                            file_structure=None
                    else:
                        file_structure='/ocn/ocean_bgc.nc-*'
                elif realm in CICE_realms:
                    if freq == 'mon':
                        if access_version == 'CM2':
                            file_structure='/ice/iceh_m.????-??.nc'
                        elif access_version == 'ESM':
                            file_structure='/ice/iceh.????-??.nc'
                    elif freq == 'day':
                        if access_version == 'CM2':
                            file_structure='/ice/iceh_d.????-??.nc'
                        elif access_version == 'ESM':
                            file_structure='/ice/iceh_day.????-??.nc'
                    else:
                        #Unknown sea ice frequency
                        file_structure=None
                else:
                    file_structure=None
                #print(cmipvar,realm,freq)
                if file_structure != None:
                    matches.append('{},{},{},{},{},{},{},{},{},{},{},{},{}'.format(cmipvar,definable,access_vars,file_structure,calculation,units,axes_modifier,positive,timeshot,years,var_notes,cfname,dimension))
                    if not cmorname in matchlist:
                        matchlist.append(cmipvar)
                elif (file_structure == None) and (skip != 'skip'):
                    if not cmorname in nomatches:
                        nomatches.append(cmorname)
    if not cmorname in matchlist:
        if not cmorname in skiplist:
            if not cmorname in nomatches:
                priority_ret=priority_check(cmorname,table)
                if priority_ret == 1:
                    nomatches.append(cmorname)
                elif priority_ret == 0:
                    pass
    g.close()
    return matches,nomatches

def write_variable_map(outpath,table,matches):
    with open('{}/{}.csv'.format(outpath,table),'w') as h:
        h.write('#cmip table: {},,,,,,,,,,,,\n'.format(table))
        h.write('#cmipvar,definable,access_vars,file_structure,calculation,units,axes_modifier,positive,timeshot,years,var_notes,cfname,dimension\n')
        for line in matches:
            print '  {}'.format(line)
            h.write('{}\n'.format(line))
    h.close()
    #if args.multi:
    #    with open('{}'.format(multilist),'a+') as j:
    #        for line in matches:
    #            j.write('{},{}\n'.format(table,line.split(',')[0]))
    #    j.close()

def create_variable_map(dreq,master_map,outpath,table):
    dreq_variables=read_dreq_vars(dreq,table)
    matches=[]
    nomatches=[]
    for cmorname,realm,freq,cfname,years,dimensions in dreq_variables:
        matches,nomatches=find_matches(table,master_map,cmorname,realm,freq,cfname,years,dimensions,matches,nomatches)
    if matches == []:
        print '\n{}:'.format(table)
        print'  no ACCESS variables found'.format(table)
    else: 
        print '\n{}:'.format(table)
        write_variable_map(outpath,table,matches)
    if nomatches != []:
        print '    variables in table \'{}\' that were not identified in the master variable map:'.format(table)
        print '      {}'.format(nomatches)
        #for item in nomatches:
        #    print '      {}'.format(item)
    else: 
        print '    success: all variables in table \'{}\' were identified in the master variable map'.format(table)

def main():
    print '\nstarting dreq_mapping...'
    print 'experiment to process: {}'.format(exptoprocess)
    print 'table to process: {}'.format(tabletoprocess)
    print 'variable to process: {}'.format(variabletoprocess)
    print 'years to process: {}-{}'.format(start_year,end_year)
    check_table()
    check_path(outpath)
    check_file(dreq)
    check_file(master_map)
    if priorityonly.lower() in ['yes','true','1']:
        check_file(prioritylist)
    check_output_directory(outpath)
    print 'beginning creation of variable maps in directory \'{}\''.format(outpath)
    tables=find_cmip_tables(dreq)
    if tabletoprocess.lower() == 'all':
        for table in tables:
            create_variable_map(dreq,master_map,outpath,table)
    else:
        table=tabletoprocess
        create_variable_map(dreq,master_map,outpath,table)
    
if __name__ == "__main__":
    main()