"""
Solver calculate functions
--------------------------

This module contains the core functions that are employed during a simulation.

Small, highly optimised computational units written using Numba

"""


import numpy as np
from numba import njit, prange


@njit(parallel=True)
def calculate_nodal_forces(x, u, cell_volume, bondlist, d, c, f_x, f_y, material_law):
    """
    Calculate particle forces - employs bondlist

    Parameters
    ----------
    bondlist : ndarray (int)
        Array of pairwise interactions (bond list)

    x : ndarray (float)
        Material point coordinates in the reference configuration

    u : ndarray (float)
        Nodal displacement

    d : ndarray (float)
        Bond damage (softening parameter). The value of d will range from 0
        to 1, where 0 indicates that the bond is still in the elastic range,
        and 1 represents a bond that has failed

    c : float
        Bond stiffness

    material_law : function

    Returns
    -------
    node_force : ndarray (float)
        Nodal force array

    d : ndarray (float)
        Bond damage (softening parameter). The value of d will range from 0
        to 1, where 0 indicates that the bond is still in the elastic range,
        and 1 represents a bond that has failed

    Notes
    -----
    * Can the constitutive model function be passed in as an argument?
        - See factory functions and closures
    * If the bondlist is loaded from a .mat file:
          node_i = bondlist[k_bond, 0] - 1
          node_j = bondlist[k_bond, 1] - 1

    """

    n_nodes = np.shape(x)[0]
    n_dimensions = np.shape(x)[1]
    n_bonds = np.shape(bondlist)[0]
    node_force = np.zeros((n_nodes, n_dimensions))

    for k_bond in prange(n_bonds):
        node_i = bondlist[k_bond, 0]
        node_j = bondlist[k_bond, 1]

        xi_x = x[node_j, 0] - x[node_i, 0]
        xi_y = x[node_j, 1] - x[node_i, 1]

        xi_eta_x = xi_x + (u[node_j, 0] - u[node_i, 0])
        xi_eta_y = xi_y + (u[node_j, 1] - u[node_i, 1])

        xi = np.sqrt(xi_x**2 + xi_y**2)
        y = np.sqrt(xi_eta_x**2 + xi_eta_y**2)
        stretch = (y - xi) / xi

        d[k_bond] = material_law(stretch, d[k_bond])

        f = stretch * c * (1 - d[k_bond]) * cell_volume
        f_x[k_bond] = f * xi_eta_x / y
        f_y[k_bond] = f * xi_eta_y / y

    # Reduce bond forces to particle forces
    for k_bond in range(n_bonds):
        node_i = bondlist[k_bond, 0]
        node_j = bondlist[k_bond, 1]

        node_force[node_i, 0] += f_x[k_bond]
        node_force[node_j, 0] -= f_x[k_bond]
        node_force[node_i, 1] += f_y[k_bond]
        node_force[node_j, 1] -= f_y[k_bond]

    return node_force, d

@njit
def calculate_node_damage(x, bondlist, d, n_family_members):
    """
    Calculate the nodal damage

    Parameters
    ----------
    x : ndarray (float)
        Material point coordinates in the reference configuration

    bondlist : ndarray (int)
        Array of pairwise interactions (bond list)

    d : ndarray (float)
        Bond damage (softening parameter). The value of d will range from 0
        to 1, where 0 indicates that the bond is still in the elastic range,
        and 1 represents a bond that has failed

    n_family_members : ndarray (int)

    Returns
    -------
    node_damage : ndarray (float)
        The value of node_damage will range from 0 to 1, where 0 indicates that
        all bonds connected to the node are in the elastic range, and 1
        indicates that all bonds connected to the node have failed

    Notes
    -----
    """
    n_nodes = np.shape(x)[0]
    n_bonds = np.shape(bondlist)[0]
    node_damage = np.zeros((n_nodes,))

    for k_bond in range(n_bonds):
        node_i = bondlist[k_bond, 0]
        node_j = bondlist[k_bond, 1]

        node_damage[node_i] += d[k_bond]
        node_damage[node_j] += d[k_bond]

    node_damage = node_damage / n_family_members

    return node_damage