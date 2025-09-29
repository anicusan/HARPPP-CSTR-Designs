#!/bin/bash
#SBATCH --time 8:0:0
#SBATCH --qos bbdefault
#SBATCH --mail-type NONE
#SBATCH --ntasks 32
#SBATCH --nodes 1
#SBATCH --account windowcr-med-granutools
#SBATCH --constraint sapphire
#SBATCH --wait



        # Commands you'd add in the sbatch script, after `#`
        module purge; module load bluebear

        # Load OpenFOAM version needed
        module load bear-apps/2022b
        module load OpenFOAM/v2312-foss-2022b

        # Environment with our Python libraries
        module load Miniforge3/24.1.2-0
        PYENV=wind-$BB_CPU

        # Configure environment
        source ${FOAM_BASH}

        echo "Environment variables:"
        echo $WM_PROJECT_DIR
        echo $WM_THIRD_PARTY_DIR
    

# Run a single function evaluation with all command-line arguments redirected to Python
/rds/homes/a/aln705/.conda/envs/wind-sapphire/bin/python $*
