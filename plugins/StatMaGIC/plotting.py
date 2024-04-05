import tempfile
from pathlib import Path

import numpy as np

# TODO: use matplotlib_importer from pythonforge instead?
import matplotlib
import pandas as pd
from statmagic_backend.maths.clustering import unpack_fullK

import logging
logger = logging.getLogger("statmagic_gui")

matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt

def makePCAplot(Kdict, pca_axis_1, pca_axis_2, plotsubVal, data_sel):
    # Create two plots, the first will show the projection of the data onto two PCA components, the second will show
    # the average value of each PCA component for each cluster

    if data_sel == 0:
        labels, km, pca, ras_dict, bool_arr, fitdat, rasBands, nclust = unpack_fullK(Kdict)
    elif data_sel == 1:
        labels, km, pca, ras_dict, bool_arr, fitdat, rasBands, nclust = unpack_fullK(Kdict)[0:8]
    elif data_sel == 2:
        labels, km, pca, ras_dict, bool_arr, fitdat, rasBands, nclust = unpack_fullK(Kdict)
    else:
        logger.debug('invalid selection')

    fig, axs = plt.subplots(1, 1, figsize=(8, 8), constrained_layout=True)

    fig1, axs1 = plt.subplots(1, 1, figsize=(8, 8), constrained_layout=True)

    pca_components = pca.components_

    # Save the PCA and clustering results in a pandas dataframe
    colnames = ['PC' + str(x + 1) for x in np.arange(fitdat.shape[1])]
    colnames.insert(0, 'Cluster')
    df = pd.DataFrame(np.c_[labels, fitdat], columns=colnames)

    levels, categories = pd.factorize(df['Cluster'])
    colors = [plt.cm.Set1(i) for i in levels]

    # Compute the by cluster means and variances
    df_means = df.groupby('Cluster').mean()
    df_vars = df.groupby('Cluster').var()

    # Plot the average value of each PCA component for each cluster
    cluster_labels = df_means.index.values
    for cluster_label in cluster_labels:
        vars = df_vars.loc[cluster_label].values
        stds = np.sqrt(vars)
        axs.errorbar(range(1, len(df_means.keys().values) + 1), df_means.loc[cluster_label].values,
                     yerr=stds, capsize=3, fmt='-o', label=cluster_label)

    axs.set_title("PCA: " + str(pca.n_components_) + ", Clusters: " + str(nclust))

    # Plot the projection of the data onto two PCA components
    # Takes the every Nth row
    df[::plotsubVal].plot(kind='scatter', x='PC' + str(pca_axis_1), y='PC' + str(pca_axis_2), c='Cluster', s=3, cmap=plt.cm.Set1,
                  ax=axs1, alpha=0.5)
    axs1.set_title("PCA: " + str(pca.n_components_) + ", Clusters: " + str(nclust))

    # Add arrows to the plot to show the direction of each band in PCA space

    for k, band in enumerate(rasBands):
        logger.debug(k, band)
        # Scale up the size of the arrows
        scale = 10
        axs1.arrow(0, 0, scale * pca_components[pca_axis_1 - 1, k], scale * pca_components[pca_axis_2 - 1, k])
        axs1.text(scale * pca_components[pca_axis_1 - 1, k], scale * pca_components[pca_axis_2 - 1, k], rasBands[k])

    # Set the display limits for the plots.  Could set the limits based on the STD of the data along each axis
    axs1.set_xlim([-5, 5])
    axs1.set_ylim([-5, 5])

    # Print the projection of each band axis on the two PCA axes we are plotting
    logger.debug(pca_components[pca_axis_1 - 1, :])
    logger.debug(pca_components[pca_axis_2 - 1, :])

    tfol = tempfile.mkdtemp()  # maybe this should be done globally at the init??
    plotfile = Path(tempfile.mkstemp(dir=tfol, suffix='.png', prefix='PCAmeanplot')[1])
    plotfile1 = Path(tempfile.mkstemp(dir=tfol, suffix='.png', prefix='scatPlot_')[1])

    fig.savefig(plotfile)
    fig1.savefig(plotfile1)
    plt.show()


def multispec_scatter(df: pd.DataFrame, plot_file: Path):
    """
    Builds a grid of plots showing the distribution of values per spectral band and colored by class ('type_id' column of Dataframe)
    :param df: Multispectral dataframe to plot, should have one column named 'type_id' and the rest different spectral bands
    :param plot_file: Path to save the resulting plot
    :return:
    """

    # logger.debug("Starting MultiSpec Scatter Plotter")
    # logger.debug("DF =\n", df.head())
    num_records = df.shape[0]
    # logger.debug("# records = ", num_records)

    # Figure out how many bands are in the dataset
    bands = list(df.keys())
    bands.remove('type_id')
    bands.remove('fid')
    num_bands = len(bands)
    # logger.debug(num_bands, " bands = ", bands)

    # Figure out how many classes exist
    classes = list(df['type_id'].unique())
    num_classes = len(classes)
    # logger.debug(num_classes, " classes = ", classes)

    # Need to do if there's only 1 class, than to use FID as the coloramp
    # Build a categorical colormap for the classes
    if num_classes == 1:
        levels, categories = pd.factorize(df['fid'])
        logger.debug(len(categories), "#  Cats")
        if len(categories) < 10:
            colors = [plt.cm.Set1(i) for i in levels]
            handles = [matplotlib.patches.Patch(color=plt.cm.Set1(i), label=c) for i, c in enumerate(categories)]
        else:
            colors = [plt.cm.tab20(i) for i in levels]
            handles = [matplotlib.patches.Patch(color=plt.cm.tab20(i), label=c) for i, c in enumerate(categories)]
    else:
        levels, categories = pd.factorize(df['type_id'])
        colors = [plt.cm.Set1(i) for i in levels]
        handles = [matplotlib.patches.Patch(color=plt.cm.Set1(i), label=c) for i, c in enumerate(categories)]

    # Figure out how many plots we need in a rectangular grid
    Lx = int(np.ceil(np.sqrt(num_bands)))
    Ly = Lx
    while Lx*Ly > num_bands:
        Lx -= 1
        if Lx*Ly > num_bands:
            Ly -= 1
        else:
            if Lx*Ly < num_bands:
                Lx += 1
            break

    # Create the subplots
    fig, axs = plt.subplots(Ly, Lx, figsize=(8, 8), constrained_layout=True)
    x_pos = np.random.random(size=num_records)

    # Plots that data
    for n, band in enumerate(bands):
        # Figure out which subplot holds this band
        j = n % Lx
        i = int(np.floor(n/Lx))

        axs[i, j].grid(axis='y', color='black', alpha=0.2)
        axs[i, j].scatter(x_pos, df[band], c=colors, s=5, alpha=0.5)
        axs[i, j].set_title(band)
        axs[i, j].xaxis.set_ticks([])
        axs[i, j].set_facecolor('0.9')

    axs[0, 0].set_ylabel('Value')
    axs[0, 0].legend(handles=handles, loc=2)
    # plt.suptitle(plot_file.stem)

    # Save and show the plot
    plt.savefig(plot_file)
    plt.show()