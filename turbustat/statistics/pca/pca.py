# Licensed under an MIT open source license - see LICENSE


import numpy as np


class PCA(object):

    '''
    Implementation of Principal Component Analysis (Heyer & Brunt, 2002)

    Parameters
    ----------

    cube : numpy.ndarray
        Data cube.
    n_eigs : int
        Number of eigenvalues to compute.
    '''

    def __init__(self, cube, n_eigs=50):
        super(PCA, self).__init__()
        self.cube = cube
        self.n_eigs = n_eigs

        # Remove NaNs
        self.cube[np.isnan(self.cube)] = 0

        self.n_velchan = self.cube.shape[0]
        self.pca_matrix = np.zeros((self.n_velchan, self.n_velchan))
        self.eigvals = None

    def compute_pca(self, normalize=True):
        '''
        Create the covariance matrix and its eigenvalues.

        Parameters
        ----------
        normalize : bool, optional
            Normalize the set of eigenvalues by the 0th component.
        '''

        cube_mean = np.nansum(self.cube) / np.sum(np.isfinite(self.cube))
        norm_cube = self.cube - cube_mean

        for i in range(self.n_velchan):
            for j in range(i):
                self.pca_matrix[i, j] = np.nansum(norm_cube[i, :, :] *
                                                  norm_cube[j, :, :]) / \
                    np.sum(np.isfinite(norm_cube[i, :, :] *
                                       norm_cube[j, :, :]))
        self.pca_matrix = self.pca_matrix + self.pca_matrix.T

        all_eigsvals, eigvecs = np.linalg.eig(self.pca_matrix)
        all_eigsvals.sort()  # Sort by maximum
        if normalize:
            self.eigvals = all_eigsvals[:self.n_eigs] / all_eigsvals[0]
        else:
            self.eigvals = all_eigsvals[:self.n_eigs]

        return self

    def run(self, verbose=False, normalize=True):
        '''
        Run method. Needed to maintain package standards.

        Parameters
        ----------
        verbose : bool, optional
            Enables plotting.
        normalize : bool, optional
            See ```compute_pca```.
        '''

        self.compute_pca(normalize=normalize)

        if verbose:
            import matplotlib.pyplot as p

            p.imshow(self.pca_matrix, origin="lower", interpolation="nearest")
            p.colorbar()
            p.show()


class PCA_Distance(object):

    '''
    Compare two data cubes based on the eigenvalues of the PCA decomposition.
    The distance is the Euclidean distance between the eigenvalues.

    Parameters
    ----------
    cube1 : numpy.ndarray
        Data cube.
    cube2 : numpy.ndarray
        Data cube.
    n_eigs : int
        Number of eigenvalues to compute.
    fiducial_model : PCA
        Computed PCA object. Use to avoid recomputing.
    normalize : bool, optional
        Sets whether to normalize the eigenvalues by the 0th eigenvalue.

    '''

    def __init__(self, cube1, cube2, n_eigs=50, fiducial_model=None,
                 normalize=True):
        super(PCA_Distance, self).__init__()
        self.cube1 = cube1
        self.cube2 = cube2

        if fiducial_model is not None:
            self.pca1 = fiducial_model
        else:
            self.pca1 = PCA(self.cube1, n_eigs=n_eigs)
            self.pca1.run(normalize=normalize)

        self.pca2 = PCA(self.cube2, n_eigs=n_eigs)
        self.pca2.run(normalize=normalize)

        self.distance = None

    def distance_metric(self, verbose=False):
        '''
        Computes the distance between the cubes.

        Parameters
        ----------
        verbose : bool, optional
            Enables plotting.
        '''

        difference = np.abs((self.pca1.eigvals - self.pca2.eigvals) ** 2.)
        self.distance = np.sqrt(np.sum(difference))

        if verbose:
            import matplotlib.pyplot as p

            p.subplot(1, 2, 1)
            p.imshow(
                self.pca1.pca_matrix, origin="lower", interpolation="nearest")
            p.colorbar()
            p.title("PCA1")

            p.subplot(1, 2, 2)
            p.imshow(
                self.pca2.pca_matrix, origin="lower", interpolation="nearest")
            p.colorbar()
            p.title("PCA2")

            p.show()

        return self
