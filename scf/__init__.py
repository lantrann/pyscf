#!/usr/bin/env python
# -*- coding: utf-8
# Author: Qiming Sun <osirpt.sun@gmail.com>

'''Non-relativistic and relativistic Hartree-Fock

Simple usage::

    >>> from pyscf import gto, scf
    >>> mol = gto.M(atom='H 0 0 0; H 0 0 1')
    >>> mf = scf.RHF(mol)
    >>> mf.scf()

:func:`scf.RHF` returns an instance of SCF class.  There are some parameters
to control the SCF method.

    verbose : int
        Print level.  Default value equals to :class:`Mole.verbose`
    max_memory : float or int
        Allowed memory in MB.  Default value equals to :class:`Mole.max_memory`
    chkfile : str
        checkpoint file to save MOs, orbital energies etc.
    conv_tol : float
        converge threshold.  Default is 1e-10
    max_cycle : int
        max number of iterations.  Default is 50
    init_guess : str
        initial guess method.  It can be one of 'minao', 'atom', '1e', 'chkfile'.
        Default is 'minao'
    DIIS : class listed in :mod:`scf.diis`
        Default is :class:`diis.SCF_DIIS`. Set it to None/False to turn off DIIS.
    diis : bool
        whether to do DIIS.  Default is True.
    diis_space : int
        DIIS space size.  By default, 8 Fock matrices and errors vector are stored.
    diis_start_cycle : int
        The step to start DIIS.  Default is 0.
    level_shift_factor : float or int
        Level shift (in AU) for virtual space.  Default is 0.
    direct_scf : bool
        Direct SCF is used by default.
    direct_scf_tol : float
        Direct SCF cutoff threshold.  Default is 1e-13.
    callback : function
        callback function takes one dict as the argument which is
        generated by the builtin function :func:`locals`, so that the
        callback function can access all local variables in the current
        envrionment.

    nelec : (int,int), for UHF/ROHF class
        freeze the number of (alpha,beta) electrons.

    irrep_nelec : dict, for symmetry- RHF/ROHF/UHF class only
        to indicate the number of electrons for each irreps.
        In RHF, give {'ir_name':int, ...} ;
        In ROHF/UHF, give {'ir_name':(int,int), ...} .
        It is effective when :attr:`Mole.symmetry` is set ``True``.

    auxbasis : str, for density fitting SCF only
        Auxiliary basis for density fitting.  Default is 'Weigend' fitting basis.
        It is effective when the SCF class is decoreated by :func:`density_fit`::

        >>> mf = scf.density_fit(scf.UHF(mol))
        >>> mf.scf()

        Density fitting can be applied to all non-relativistic HF class.

    with_ssss : bool, for Dirac-Hartree-Fock only
        If False, ignore small component integrals (SS|SS).  Default is True.
    with_gaunt : bool, for Dirac-Hartree-Fock only
        If False, ignore Gaunt interaction.  Default is False.

Saved results

    converged : bool
        SCF converged or not
    e_tot : float
        Total HF energy (electronic energy plus nuclear repulsion)
    mo_energy : 
        Orbital energies
    mo_occ
        Orbital occupancy
    mo_coeff
        Orbital coefficients

'''

from pyscf.scf import hf
from pyscf.scf import hf as rhf
from pyscf.scf import rohf
from pyscf.scf import hf_symm
from pyscf.scf import hf_symm as rhf_symm
from pyscf.scf import uhf
from pyscf.scf import uhf_symm
from pyscf.scf import dhf
from pyscf.scf import chkfile
from pyscf.scf import addons
from pyscf.scf.uhf import spin_square
from pyscf.scf.hf import get_init_guess
from pyscf.scf.addons import *
from pyscf.scf import x2c
from pyscf.scf.x2c import sfx2c1e, sfx2c
from pyscf.scf import newton_ah



def RHF(mol, *args):
    '''This is a wrap function to decide which SCF class to use, RHF or ROHF
    '''
    if mol.nelectron == 1:
        if mol.symmetry:
            return rhf_symm.HF1e(mol)
        else:
            return rhf.HF1e(mol)
    elif not mol.symmetry or mol.groupname is 'C1':
        if mol.spin > 0:
            return rohf.ROHF(mol, *args)
        else:
            return rhf.RHF(mol, *args)
    else:
        if mol.spin > 0:
            return rhf_symm.ROHF(mol, *args)
        else:
            return rhf_symm.RHF(mol, *args)

def ROHF(mol, *args):
    '''This is a wrap function to decide which ROHF class to use.
    '''
    if mol.nelectron == 1:
        if mol.symmetry:
            return rhf_symm.HF1e(mol)
        else:
            return rhf.HF1e(mol)
    elif not mol.symmetry or mol.groupname is 'C1':
        return rohf.ROHF(mol, *args)
    else:
        return hf_symm.ROHF(mol, *args)

def UHF(mol, *args):
    '''This is a wrap function to decide which UHF class to use.
    '''
    if mol.nelectron == 1:
        return RHF(mol)
    elif not mol.symmetry or mol.groupname is 'C1':
        return uhf.UHF(mol, *args)
    else:
        return uhf_symm.UHF(mol, *args)

def DHF(mol, *args):
    '''This is a wrap function to decide which Dirac-Hartree-Fock class to use.
    '''
    if mol.nelectron == 1:
        return dhf.HF1e(mol)
    else:
        return dhf.UHF(mol, *args)

def X2C(mol, *args):
    return x2c.UHF(mol, *args)

def density_fit(mf, auxbasis='weigend+etb', with_df=None):
    return mf.density_fit(auxbasis, with_df)

def newton(mf):
    '''augmented hessian for Newton Raphson

    Examples:

    >>> mol = gto.M(atom='H 0 0 0; H 0 0 1.1', basis='cc-pvdz')
    >>> mf = scf.RHF(mol).run(conv_tol=.5)
    >>> mf = scf.newton(mf).set(conv_tol=1e-9)
    >>> mf.kernel()
    -1.0811707843774987
    '''
    return newton_ah.newton(mf)

def fast_newton(mf, mo_coeff=None, mo_occ=None, dm0=None,
                auxbasis=None, **newton_kwargs):
    '''Wrap function to quickly setup and call Newton solver.
    Newton solver attributes [max_cycle_inner, max_stepsize, ah_start_tol,
    ah_conv_tol, ah_grad_trust_region, ...] can be passed through **newton_kwargs.
    '''
    from pyscf.lib import logger
    from pyscf import df
    if auxbasis is None:
        auxbasis = df.addons.aug_etb_for_dfbasis(mf.mol, 'ahlrichs', beta=2.5)
    mf1 = density_fit(newton(mf), auxbasis)
    for key in newton_kwargs:
        setattr(mf1, key, newton_kwargs[key])
    if hasattr(mf, 'grids'):
        import copy
        from pyscf.dft import gen_grid
        approx_grids = gen_grid.Grids(mf.mol)
        approx_grids.verbose = 0
        approx_grids.level = 0
        mf1.grids = approx_grids

        approx_numint = copy.copy(mf._numint)
        mf1._numint = approx_numint

    if dm0 is not None:
        mo_coeff, mo_occ = mf1.from_dm(dm0)
    elif mo_coeff is None or mo_occ is None:
        logger.note(mf, '========================================================')
        logger.note(mf, 'Generating initial guess with DIIS-SCF for newton solver')
        logger.note(mf, '========================================================')
        mf0 = density_fit(mf, auxbasis)
        mf0.conv_tol = .25
        mf0.conv_tol_grad = .5
        if mf0.level_shift == 0:
            mf0.level_shift = .3
        if hasattr(mf, 'grids'):
            mf0.grids = approx_grids
            mf0._numint = approx_numint
# Note: by setting small_rho_cutoff, dft.get_veff_ function may overwrite
# approx_grids and approx_numint.  It will further changes the corresponding
# mf1 grids and _numint.  If inital guess dm0 or mo_coeff/mo_occ were given,
# dft.get_veff_ are not executed so that more grid points may be found in
# approx_grids.
            mf0.small_rho_cutoff = 1e-5
        mf0.kernel()

        mf1._cderi = mf0._cderi
        mf1._naoaux = mf0._naoaux
        mo_coeff, mo_occ = mf0.mo_coeff, mf0.mo_occ
        logger.note(mf, '============================')
        logger.note(mf, 'Generating initial guess end')
        logger.note(mf, '============================')

    mf1.kernel(mo_coeff, mo_occ)
    mf.converged = mf1.converged
    mf.e_tot     = mf1.e_tot
    mf.mo_energy = mf1.mo_energy
    mf.mo_coeff  = mf1.mo_coeff
    mf.mo_occ    = mf1.mo_occ

    def mf_kernel(*args, **kwargs):
        from pyscf.lib import logger
        logger.warn(mf, "fast_newton is a wrap function to quickly setup and call Newton solver. "
                    "There's no need to call kernel function again for fast_newton.")
        return mf.e_tot
    mf.kernel = mf_kernel
    return mf

def fast_scf(mf):
    from pyscf.lib import logger
    logger.warn(mf, 'NOTE function fast_scf will be removed in the next release. '
                'Use function fast_newton instead')
    return fast_newton(mf)


def RKS(mol, *args):
    from pyscf import dft
    return dft.RKS(mol)

def ROKS(mol, *args):
    from pyscf import dft
    return dft.ROKS(mol)

def UKS(mol, *args):
    from pyscf import dft
    return dft.UKS(mol)

