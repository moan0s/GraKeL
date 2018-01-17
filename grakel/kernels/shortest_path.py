"""Shortest path kernel as defined in :cite:`Borgwardt2005ShortestpathKO`."""

import itertools
import numpy as np

from grakel.graph import graph


def shortest_path(X, Y, Lx, Ly, algorithm_type="dijkstra", **kargs):
    r"""Calculate the shortest path kernel.

    See :cite:`Borgwardt2005ShortestpathKO`.

    Parameters
    ----------
    X,Y : *valid-graph-format*
        The pair of graphs on which the kernel is applied.

    algorithm_type : str, default={"dijkstra", "floyd_warshall", "auto"}
        Apply the dijkstra or floyd_warshall algorithm for calculating
        shortest path, or chose automatically ("auto") based on the
        current graph format ("auto").

    as_attributes : bool, default=False
        The labels are considered as attributes. The computational
        efficiency is decreased to :math:`O(|V|^4)`

    attribute_kernel : function, default=:math:`f(x,y)=\sum_{i}x_{i}*y_{i}`,
    case_of_existence=(as_attributes==True)
        A kernel function applied between attributes.

    case_of_existence=(as_attributes==True)
        The kernel applied between attributes of the graph labels.
        The user must provide a kernel based on the format of the provided
        labels (considered as attributes).

    with_labels : bool, default=True, case_of_existence=(as_attributes==True)
        Calculate shortest path using graph labels.

    Returns
    -------
    kernel : number
        The kernel value.

    """
    g_x = graph(X, Lx)
    g_y = graph(Y, Ly)
    if kargs.get("as_attributes", False):
        return shortest_path_pair_attributes(
            g_x, g_y, algorithm_type,
            attribute_kernel=kargs.get("attribute_kernel",
                                       lambda x, y: np.dot(x, y)))
    else:
        return shortest_path_matrix({0: g_x},
                                    {0: g_y},
                                    algorithm_type,
                                    with_labels=kargs.get(
                                        "with_labels",
                                        True)
                                    )[0, 0]


def shortest_path_matrix(Graphs_x,
                         Graphs_y=None,
                         algorithm_type="dijkstra",
                         with_labels=True):
    r"""Calculate the shortest path kernel matrix.

    See :cite:`Borgwardt2005ShortestpathKO`.

    Parameters
    ----------
    Graphs_{x,y} : dict, default_y=None
        Enumerative dictionary of graph type objects with keys from 0 to the
        number of values. If value of Graphs_y is None the kernel matrix is
        computed between all pairs of Graphs_x where in another case the
        kernel_matrix rows correspond to elements of Graphs_y, and columns
        to the elements of Graphs_x.

    algorithm_type : str, default={"dijkstra", "floyd_warshall", "auto"}
        Apply the dijkstra or floyd_warshall algorithm for calculating
        shortest path, or chose automatically ("auto") based on the
        current graph format ("auto").

    with_labels : bool, default=True
        Calculate shortest path using graph labels.

    Returns
    -------
    kernel_matrix : np.array
        The kernel matrix. If the Graphs_y is not None the rows correspond
        to Graphs_y and the cols to the Graphs_x (based on the given order).

    Complexity
    ----------
    :math:`O(n*N*|\cup_{i}L_{i}|^{2})`, where :math:`n` the number of graph,
    :math:`N` the number of vertices of the **biggest** Graph and
    :math:`|\cup_{i}L_{i}|` the number of all distinct labels.

    """
    # calculate shortest path matrix
    nx = len(Graphs_x.keys())

    if Graphs_y is None:
        ng = nx
        Gs = Graphs_x
    else:
        ng = nx + len(Graphs_y.keys())
        Gs = {i: g for (i, g) in enumerate(
            itertools.chain(Graphs_x.values(), Graphs_y.values()))}

    if with_labels:
        lt = "vertex"
        lhash = lambda S, u, v, *args: (args[0][u], args[0][v], S[u, v])
    else:
        lt = "none"
        lhash = lambda S, u, v, *args: S[u, v]

    enum = dict()
    sp_counts = dict()
    for i in range(ng):
        sp_counts[i] = dict()
        S, *L = Gs[i].build_shortest_path_matrix(algorithm_type,
                                                 labels=lt)
        for u in range(S.shape[0]):
            for v in range(S.shape[0]):
                if u == v or S[u, v] == float("Inf"):
                    continue
                label = lhash(S, u, v, *L)
                if label not in enum:
                    enum[label] = len(enum)
                idx = enum[label]

                if idx in sp_counts[i]:
                    sp_counts[i][idx] += 1
                else:
                    sp_counts[i][idx] = 1

    phi_x = np.zeros((nx, len(enum)))
    for i in range(nx):
        for (j, v) in sp_counts[i].items():
            phi_x[i, j] = v

    if Graphs_y is None:
        phi_y = phi_x.T
    else:
        phi_y = np.zeros((len(enum), ng-nx))
        for i in range(nx, ng):
            for (j, v) in sp_counts[i].items():
                phi_y[j, i-nx] = v

    return np.dot(phi_x, phi_y).T


def shortest_path_pair_attributes(
    gx, gy, algorithm_type="dijkstra",
        attribute_kernel=lambda x, y: np.dot(x, y)):
    """Calculate the shortest path kernel, for attributed graphs.

    Parameters
    ----------
    g{x,y} : graph
        The pair graphs on which the kernel is applied.

    algorithm_type : str, default={"dijkstra", "floyd_warshall", "auto"}
        Apply the dijkstra or floyd_warshall algorithm for calculating
        shortest path, or chose automatically ("auto") based on the
        current graph format ("auto").

    Returns
    -------
    kernel : number.
        The kernel value.

    Complexity
    ----------
    :math:`O(n^4*O(Complexity(k_{attr}))`, where the number of vertices is
    :math:`n` and the default :math:`Complexity(k_{attr})=O(m)`
    is the maximum length of an attribute vector.

    """
    # calculate shortest path matrix
    Sx, phi_x = gx.build_shortest_path_matrix(algorithm_type)
    Sy, phi_y = gy.build_shortest_path_matrix(algorithm_type)

    # Initialise
    kernel = 0
    dimx = Sx.shape[0]
    dimy = Sy.shape[0]
    for i in range(dimx):
        for j in range(dimx):
            if i == j:
                continue
            for k in range(dimy):
                for m in range(dimy):
                    if k == m:
                        continue
                    if Sx[i, j] == Sy[k, m] and Sx[i, j] != float('Inf'):
                        kernel += attribute_kernel(phi_x[i], phi_y[k]) *\
                            attribute_kernel(phi_x[j], phi_y[m])

    return kernel
