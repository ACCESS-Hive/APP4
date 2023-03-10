#!/bin/bash
set -a 
################################################################
#
# This is the ACCESS Post-Processor, v4.1
# 24/01/2022
# 
# Developed by Chloe Mackallah, CSIRO Aspendale
# based on prior work by Peter Uhe and others at CSIRO
#
################################################################
#
# CUSTOM MODE - USE THIS FOR NON-CMIP6 EXPERIMENTS (I.E. CUSTOM METADATA)
#
# THE APP4 WILL INSERT THE DETAILS DEFINED BELOW INTO THE CMIP6_CV.JSON FILE
# TO ENABLE NON-CMIP6 EXPERIMENTS TO BE CMORISED
#
# see https://git.nci.org.au/cm2704/ACCESS-Archiver for related tools
#
################################################################
#
# USER OPTIONS

# Details of local experiment to process:
# DATA_LOC must point to dir above experiment; and experiment subdir must contain history/atm/[,ocn/,ice/]
#
DATA_LOC=/g/data/p73/archive/non-CMIP/ACCESS-CM2/
EXP_TO_PROCESS=bx994                         # local name of experiment
VERSION=CM2                                  # select one of: [CM2, ESM, OM2[-025]]
START_YEAR=1970                              # internal year to begin CMORisation
END_YEAR=2014                                # internal year to end CMORisation (inclusive)
REFERENCE_YEAR=1970                          # reference date for time units (set as 'default' to use START_YEAR)
CONTACT=access_csiro@csiro.au                # please insert your contact email
# Please provide a short description of the experiment. For those created from the p73 archive, it's ok to just link to the Archive Wiki.
EXP_DESCRIPTION="Pacemaker, Topical Atlantic, HadISST obs. see: https://confluence.csiro.au/display/ACCESS/ACCESS+Model+Output+Archive+%28p73%29+Wiki"

# Standard experiment details:
#
experiment_id=hist-control                   # standard experiment name (e.g. piControl)
activity_id=PacemakerMIP                     # activity/MIP name (e.g. CMIP)
realization_index=1                          # "r1"[i1p1f1] (e.g. 1)
initialization_index=1                       # [r1]"i1"[p1f1] (e.g. 1)
physics_index=1                              # [r1i1]"p1"[f1] (e.g. 1)
forcing_index=1                              # [r1i1p1]"f1" (e.g. 1)
source_type=AOGCM                            # see input_files/custom_mode_cmor-tables/Tables/CMIP6_CV.json
branch_time_in_child=0D0                     # specifies the difference between the time units base and the first internal year (e.g. 365D0)

# Parent experiment details:
# if parent=false, all parent fields are automatically set to "no parent". If true, defined values are used.
#
parent=true 
parent_experiment_id=piControl               # experiment name of the parent (e.g. piControl-spinup)
parent_activity_id=CMIP                      # activity/MIP name of the parent (e.g. CMIP)
parent_time_units="days since 0950-01-01"    # time units of the parent (e.g. "days since 0001-01-01")
branch_time_in_parent=0D0                    # internal time of the parent at which the branching occured (e.g. 0D0)
parent_variant_label=r1i1p1f1                # variable label of the parent (e.g. r1i1p1f1)

# Variables to CMORise: 
# CMIP6 table/variable to process; default is 'all'. Or create a file listing variables to process (VAR_SUBSET[_LIST]).
#
DREQ=default                                 # default=input_files/dreq/cmvme_all_piControl_3_3.csv
TABLE_TO_PROCESS=all                         # CMIP6 table to process. Default is 'all'
VARIABLE_TO_PROCESS=all                      # CMIP6 variable to process. Default is 'all'
SUBDAILY=false                               # subdaily selection options - select one of: [true, false, only]
VAR_SUBSET=false                             # use a sub-set list of variables to process, as defined by 'VAR_SUBSET_LIST'
VAR_SUBSET_LIST=input_files/var_subset_lists/var_subset_ACS.csv

# Additional NCI information:
# OUTPUT_LOC defines directory for all generated data (CMORISED files & logs)
#
OUTPUT_LOC=/scratch/$PROJECT/$USER/APP4_output 
PROJECT=$PROJECT                             # NCI project to charge compute; $PROJECT = your default project
ADDPROJS=( p73 p66 )                         # additional NCI projects to be included in the storage flags
QUEUE=hugemem                                # NCI queue to use; hugemem is recommended
MEM_PER_CPU=24                               # memory (GB) per CPU (recommended: 24 for daily/monthly; 48 for subdaily) 

#
#
#
#
#
#

################################################################
# SETTING UP ENVIROMENT, VARIABLE MAPS, AND DATABASE
################################################################
# exit back to check_app4 script if being used
if [[ $check_app4 == 'true' ]] ; then return ; fi

# Set up environment
MODE=custom
HISTORY_DATA=$DATA_LOC/$EXP_TO_PROCESS/history
source ./subroutines/setup_env.sh

# Cleanup output_files
./subroutines/cleanup.sh $OUT_DIR

# Create json file which contains metadata info
python ./subroutines/custom_json_editor.py
#exit

# Create variable maps
python ./subroutines/dreq_mapping.py --multi
#exit

# Create database
python ./subroutines/database_manager.py
#exit

# FOR TESTING
#python ./subroutines/app_wrapper.py; exit
#

################################################################
# CREATE JOB
################################################################
echo -e '\ncreating job...'

for addproj in ${ADDPROJS[@]}; do
  addstore="${addstore}+scratch/${addproj}+gdata/${addproj}"
done
#
NUM_ROWS=$( cat $OUT_DIR/database_count.txt )
if (($NUM_ROWS <= 24)); then
  NUM_CPUS=$NUM_ROWS
else
  NUM_CPUS=24
fi
NUM_MEM=$(echo "${NUM_CPUS} * ${MEM_PER_CPU}" | bc)
if ((${NUM_MEM} >= 1470)); then
  NUM_MEM=1470
fi
#
#NUM_CPUS=48
#NUM_MEM=1470
echo "number of files to create: ${NUM_ROWS}"
echo "number of cpus to to be used: ${NUM_CPUS}"
echo "total amount of memory to be used: ${NUM_MEM}Gb"

cat << EOF > $APP_JOB
#!/bin/bash
#PBS -P $PROJECT
#PBS -q $QUEUE
#PBS -l storage=scratch/$PROJECT+gdata/$PROJECT+gdata/hh5+gdata/access${addstore}
#PBS -l ncpus=${NUM_CPUS},walltime=24:00:00,mem=${NUM_MEM}Gb,wd
#PBS -j oe
#PBS -o ${JOB_OUTPUT}
#PBS -e ${JOB_OUTPUT}
#PBS -N custom_app4_${EXP_TO_PROCESS}
module purge
set -a
# pre
EXP_TO_PROCESS=${EXP_TO_PROCESS}
OUTPUT_LOC=$OUTPUT_LOC
MODE=$MODE
CONTACT=$CONTACT
CDAT_ANONYMOUS_LOG=no
source ./subroutines/setup_env.sh
# main
python ./subroutines/app_wrapper.py
# post
python ${OUT_DIR}/database_updater.py
sort ${SUCCESS_LISTS}/${EXP_TO_PROCESS}_success.csv \
    > ${SUCCESS_LISTS}/${EXP_TO_PROCESS}_success_sorted.csv
mv ${SUCCESS_LISTS}/${EXP_TO_PROCESS}_success_sorted.csv \
    ${SUCCESS_LISTS}/${EXP_TO_PROCESS}_success.csv
sort ${SUCCESS_LISTS}/${EXP_TO_PROCESS}_failed.csv \
    > ${SUCCESS_LISTS}/${EXP_TO_PROCESS}_failed_sorted.csv 2>/dev/null
mv ${SUCCESS_LISTS}/${EXP_TO_PROCESS}_failed_sorted.csv \
    ${SUCCESS_LISTS}/${EXP_TO_PROCESS}_failed.csv
echo "APP completed for exp ${EXP_TO_PROCESS}."
EOF

/bin/chmod 775 ${APP_JOB}
echo "app job script: ${APP_JOB}"
qsub ${APP_JOB}
