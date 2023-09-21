curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh"
bash Mambaforge-$(uname)-$(uname -m).sh -b
mamba activate
mamba create --name statmagic --file pyproject.toml
mamba init
mamba activate statmagic
