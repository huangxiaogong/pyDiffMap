"""
A class to implement diffusion kernels.
"""

import numpy as np
from scipy.misc import logsumexp
from scipy.optimize import minimize_scalar 
from sklearn.neighbors import NearestNeighbors


class Kernel(object):
    """
    Class abstracting the evaluation of kernel functions on the dataset.

    Parameters
    ----------
    type : string, optional
        Type of kernel to construct. Currently the only option is 'gaussian', but more will be implemented.
    epsilon : scalar, optional
        Value of the length-scale parameter.
    k : int, optional
        Number of nearest neighbors over which to construct the kernel.
    choose_eps : string, optional
        Method for choosing the epsilon.  Currently, the only option is 'fixed' (i.e. don't).
    metric : string, optional
        Distance metric to use in constructing the kernel.  This can be selected from any of the scipy.spatial.distance metrics, or a callable function returning the distance.
    metric_params : dict or None, optional
        Optional parameters required for the metric given.
    """

    def __init__(self, type='gaussian', epsilon=1.0, k=64, metric='euclidean', metric_params=None):
        self.type = type
        self.epsilon = epsilon
        self.metric = metric
        self.k = k

    def fit(self, X):
        """
        Fits the kernel to the data X, constructing the nearest neighbor tree.

        Parameters
        ----------
        X : array-like, shape (n_query, n_features)
            Data upon which to fit the nearest neighbor tree.

        Returns
        -------
        self : the object itself
        """
        self.k0 = min(self.k, np.shape(X)[0])
        self.data = X
        self.neigh = NearestNeighbors(metric=self.metric).fit(X)
        return self

    def compute(self, Y=None):
        """
        Computes the sparse kernel matrix.

        Parameters
        ----------
        Y : array-like, shape (n_query, n_features), optional.
            Data against which to calculate the kernel values.  If not provided, calculates against the data provided in the fit.

        Returns
        -------
        K : array-like, shape (n_query_X, n_query_Y)
            Values of the kernel matrix.

        """
        if Y is None:
            Y = self.data
        # perform k nearest neighbour search on X and Y and construct sparse matrix
        K = self.neigh.kneighbors_graph(Y, n_neighbors=self.k0, mode='distance')
        # retrieve all nonzero elements and apply kernel function to it
        v = K.data
        if (self.type == 'gaussian'):
            K.data = np.exp(-v**2/self.epsilon)
        else:
            raise("Error: Kernel type not understood.")
        return K

def get_optimal_epsilon_BGH(scaled_distsq, epsilons=None, h=0.1, maxiter=100):
    """
    Calculates the optimal bandwidth for kernel density estimation according to 
    the criteria in Berry, Giannakis, and Harlim.

    Parameters
    ----------
    scaled_distsq : scipy sparse matrix
        Matrix of scaled distance square values (The exponent in the Gaussian).
    epsilons : array-like, optional
        Values of epsilon from which to choose the optimum.  If not provided, uses all powers of 2. from 2^-40 to 2^40

    Returns
    -------
    epsilon : float
        Estimated value of the optimal bandwidth.
    d : int
        Estimated dimensionality of the system.

    Notes
    -----
    Erik sez : I have a suspicion that the derivation here explicitly assumes that
    the kernel is Gaussian.  However, I'm not sure.  Also, we should perhaps replace
    this with some more intelligent optimization routine.  Here, I'm just 
    picking from several values as a first step.

    References
    ----------
    The algorithm given is based on [1]_.  If you use this code, please cite them.

    .. [1] T. Berry, D. Giannakis, and J. Harlim, Physical Review E 91, 032915 
       (2015).
    """
    if epsilons is None:
        epsilons = 2**np.arange(-40.,41.,1.)
    
    epsilons = np.sort(epsilons).astype('float')
    print epsilons
    log_T = [logsumexp(-scaled_distsq/eps) for eps in epsilons]
    log_eps = np.log(epsilons)
    log_deriv = np.diff(log_T)/np.diff(log_eps)
    max_loc = np.argmax(log_deriv)
    epsilon = np.max([np.exp(log_eps[max_loc]), np.exp(log_eps[max_loc+1])])
    d = np.round(2.*log_deriv[max_loc])
    return epsilon, d, log_deriv
