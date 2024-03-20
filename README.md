**This document is hosted at https://github.com/DARPA-CRITICALMAAS/mtri-statmagic-gui/README.md**
# statmagic_gui
The QGIS plugin front end for [StatMaGIC](https://github.com/DARPA-CRITICALMAAS/mtri-statmagic-backend).

This user guide is intended to assist in the installation, set-up, and use of the StatMaGIC QGIS Plug-In developed under the DARPA CriticalMAAS for USGS end users.

Last Updated: 2/14/2024

# Table Of Contents

1. [Software Needs](#software)
2. [Plug-In Installation](#installation)
   1. [Setting Up Environment](#environment)
   2. [Cloning Repositories](#cloning)
   3. [Maintaining Repositories](#repositories)
3. [Opening StatMaGIC in QGIS](#openinginqgis)
   1. [Opening QGIS](#openqgis)
   2. [Opening StatMaGIC once in QGIS](#onceopen)

# Software Needs

To run the StatMaGIC plugin, users will need to have the following software downloaded onto their machine or alternatively have access to a remote computer server (such as AWS) that has these software installed. Some software may be contingent on users operating system.

| Name | Description |
|------|-------------|
| Git Bash | Command line emulator (Windows only) which is necessary to pull the latest updates from the CriticalMAAS Github. |
| Mamba | Wrapper around conda (used for environment setup and software installation). Needed on both Windows and Ubuntu. |

<details>
<summary><b>Ubuntu users</b></summary>
<br />

Download mamba:
```bash 
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh"
bash Mambaforge-$(uname)-$(uname -m).sh -b
```

Activate base Mamba environment:
```
source $HOME/mambaforge/bin/activate 
```
</details>
<details>
<summary><b>Windows users</b></summary>

### Git Bash

1. Download the Git Bash installer:

   - Navigate to https://gitforwindows.org in a web browser
   - Click the "Download" button
2. Run the installation wizard by double clicking the `.exe` file you downloaded. Select all of the default options.
3. In the start menu, type "git bash" to launch the "Git Bash" app.

### Mamba
1. Download the mamba installer: https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Windows-x86_64.exe
2. Run the installation wizard by double clicking `Mambaforge-Windows-x86_64.exe`.

   - Select "Just me" and install in the default location, e.g. `C:\Users\djleisma\AppData\Local\mambaforge`
   - Select only the checkbox labeled "Create start menu shortcuts." We'll try to do most everything else manually.
3. In the start menu, type "miniforge" to launch the "Miniforge Prompt" app.
</details>

# Plug-In Installation

A controlled working environment has been created to to ensure that the StatMaGIC plugin works as designed across all machines (step 1). Once that environment has been created, the most recent version of the plugin needs to be cloned from the shared [CriticalMAAS GitHub](https://github.com/DARPA-CRITICALMAAS) onto the users local system (step 2). These two steps should only be required the first time a new user goes to use the plugin. Subsequent use cases, the user needs only to activate the existing `statmagic` environment and check that their repositories are up to date (step 3).

## 1\. Setting Up Environment

### Open a terminal
<details>
  <summary><b>Ubuntu users</b></summary><br />
  
  Hit `Ctrl` + `Alt` + `T` to open a new terminal, or use your terminal emulator of choice.
</details>
<details>
  <summary><b>Windows Users</b></summary><br />
  
  Use the Miniforge prompt for this section.
</details>

### Create new, project-specific environment
<details>
<summary><b>Ubuntu users</b></summary>

```
mamba create --name statmagic qgis scipy scikit-learn pandas gdal numpy matplotlib scikit-image pydantic pygraphviz poetry jsonschema2md erdantic progress awscli rasterio geopandas shapely mapbox-vector-tile mercantile pyqtgraph somoclu seaborn
```
</details>
<details>
<summary><b>Windows users</b></summary>

```
mamba create --name statmagic qgis scipy scikit-learn pandas gdal numpy matplotlib scikit-image pydantic pygraphviz poetry jsonschema2md erdantic progress awscli rasterio geopandas shapely mapbox-vector-tile mercantile pyqtgraph seaborn
```
</details>

### Initialize Mamba
```
mamba init
```

### Prevent mamba from auto-activating the base environment. (Note, the conda, not mamba prefix).
```
conda config --set auto_activate_base false
```

### Activate the project-specific environment
```
mamba activate statmagic
```

## 2\. Cloning Repositories

<details>
<summary><b>Ubuntu Users</b></summary>

Using the same terminal from before:

```
mkdir statmagic; cd statmagic
git clone https://github.com/DARPA-CRITICALMAAS/mtri-statmagic-gui.git
git clone https://github.com/DARPA-CRITICALMAAS/mtri-statmagic-backend.git
```

If you intend to use the Beak or SRI workflows, their software is also necessary:
```
git clone https://github.com/DARPA-CRITICALMAAS/beak-ta3.git
git clone https://github.com/DARPA-CRITICALMAAS/sri-ta3.git
```
Without the necessary code present, the respective `Beak` or `SRI` tabs will not work.

</details>

<details>
<summary><b>Windows Users</b></summary>

1. Open GitHub and navigate to the `mtri-statmagic-backend` repository: https://github.com/DARPA-CRITICALMAAS/mtri-statmagic-backend
2. Select the down arrow near the `<>Code` button and copy the URL by clicking the `Copy url to clipboard` ![Copy URL image](https://github.com/DARPA-CRITICALMAAS/mtri-statmagic-gui/assets/114172102/9a4f2bbd-294d-4bba-b60f-d43f281b3b9a)
3. Open Git Bash from the start menu or search bar
4. In Git Bash, navigate to the folder that you would like to save these repositories into using the change directory `cd` command. For example, I have mine in saved in my local computer's users folder in a directory called `dev` for development. ![Git bash image](https://github.com/DARPA-CRITICALMAAS/mtri-statmagic-gui/assets/114172102/84296d10-110d-47f9-8319-327d11a28f65)
5. Type `git clone` and then right click to paste the copied URL from GitHub ![Git Clone image](https://github.com/DARPA-CRITICALMAAS/mtri-statmagic-gui/assets/114172102/97324ee9-bf35-4ba4-a82e-ac0de21c8a1c)
6. Hit Enter
7. Repeat steps 2-5 with the GitHub `mtri-statmagic-gui` repository: https://github.com/DARPA-CRITICALMAAS/mtri-statmagic-gui
8. If you wish to use Beak's workflow, repeat steps 2-5 using https://github.com/DARPA-CRITICALMAAS/beak-ta3 . The `Beak` tab will not function without Beak's software.
9. If you wish to use SRI's workflow, repeat steps 2-5 using https://github.com/DARPA-CRITICALMAAS/sri-ta3 . The `SRI` tab will not function without SRI's software.
10. Helpful commands:
   * To view the files within a folder use the directory command `dir`
   * To go back a directory use `cd ..`
   * Use the `Tab` key to auto populate path names once you start typing.
   * To see if the repositories have been changes, navigate to be within the repo and use command `git status`

</details>

# Opening StatMaGIC in QGIS

## 0\. First Time Setup

Navigate to the `statmagic_backend` directory

<details><summary><b>Windows Users</b></summary>

1. Open Miniforge prompt
2. `cd dev\statmagic_backend`

</details>

<details>
<summary><b>Ubuntu Users</b></summary>

1. Use the same terminal from before.
2. `cd statmagic_backend`

</details>

If your terminal doesn't say `(statmagic)` at the beginning, you may need to type `mamba activate statmagic` again.

Run the following command **(required for the plugin to function)**:
```
pip install -e .
```
![pip install image](https://github.com/DARPA-CRITICALMAAS/mtri-statmagic-gui/assets/114172102/5efd611a-ff08-4f1c-9135-f865bcb28786)


If you intend to use the `Beak` tab, `cd ../beak-ta3` then run `pip install -e .`.

If you intend to use the `SRI` tab, `cd ../sri-ta3` then run `pip install -e .`.

## 1\. Starting QGIS

<details>
<summary>Starting QGIS in Windows</summary>

1. Open Miniforge Prompt
2. Activate the StatMaGIC environment with `mamba activate statmagic`
3. Navigate to the `statmagic_gui` repository (e.g. `cd dev\statmagic_gui`) _Note once you start typing you can hit the `Tab` key to fill out the rest of the path._
4. Run the `aws_launch_qgis.bat` script from within `statmagic_gui` ![aws_launch_qgis image](https://github.com/DARPA-CRITICALMAAS/mtri-statmagic-gui/assets/114172102/ae0d4fa2-c76a-4bc8-b7ad-56dacd049363)
5. This will prompt a series of commands to open up QGIS.

</details>

<details>
<summary>Starting QGIS in Ubuntu</summary>

1. Open terminal
2. Activate the StatMaGIC environment with `mamba activate statmagic`
3. Navigate to the `statmagic_gui` directory (e.g. `cd dev/statmagic_gui`) _Note once you start typing you can hit the `Tab` key to fill out the rest of the path._
4. Run the `launch_qgis.sh` script from within `statmagic_gui`
5. This will prompt a series of commands to open up QGIS.

</details>

## 2\. Opening StatMaGIC once in QGIS

1. Select a new project by clicking the new project icon (white page in the upper left) or re-open a recent project from the suggestions.

  ![new QGIS project image](https://github.com/DARPA-CRITICALMAAS/mtri-statmagic-gui/assets/114172102/ec2d4a78-9109-4bfe-8486-09a3044e4a70)

2. The StatMaGIC plug-in icon ![plugin icon image](https://github.com/DARPA-CRITICALMAAS/mtri-statmagic-gui/assets/114172102/bebf2529-e66f-43f0-8496-29e77e08c129) will appear at the top of the QGIS project and when clicked on will open the plug-in along the right side of the QGIS project workspace. _Note: Should the StatMaGIC icon not appear automatically on your tool bar, select `Plugins` along the top menu and `Manage and Install Plugins...` In the plugin manager, navigate to the installed plugins and check the box next to the StatMaGIC plugin._

   ![Manage and Install Plugins image](https://github.com/DARPA-CRITICALMAAS/mtri-statmagic-gui/assets/114172102/fc89854a-9b75-4386-89b9-0eef17ebbe73)

3. You are now ready to use the StatMaGIC tools.

