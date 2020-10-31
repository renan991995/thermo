# -*- coding: utf-8 -*-
'''Chemical Engineering Design Library (ChEDL). Utilities for process modeling.
Copyright (C) 2016, 2017, 2018, 2019, 2020 Caleb Bell <Caleb.Andrew.Bell@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.'''

from __future__ import division
from fluids.numerics import numpy as np
from thermo.activity import GibbsExcess
from math import log, exp
from fluids.constants import R

__all__ = ['NRTL', 'NRTL_gammas']


class NRTL(GibbsExcess):
    def __init__(self, T, xs, tau_coeffs=None, alpha_coeffs=None,
                 ABEFGHCD=None):
        self.T = T
        self.xs = xs

        if ABEFGHCD is not None:
            (self.tau_coeffs_A, self.tau_coeffs_B, self.tau_coeffs_E,
            self.tau_coeffs_F, self.tau_coeffs_G, self.tau_coeffs_H,
            self.alpha_coeffs_c, self.alpha_coeffs_d) = ABEFGHCD
            self.N = N = len(self.tau_coeffs_A)
        else:
            if tau_coeffs is not None:
                self.tau_coeffs_A = [[i[0] for i in l] for l in tau_coeffs]
                self.tau_coeffs_B = [[i[1] for i in l] for l in tau_coeffs]
                self.tau_coeffs_E = [[i[2] for i in l] for l in tau_coeffs]
                self.tau_coeffs_F = [[i[3] for i in l] for l in tau_coeffs]
                self.tau_coeffs_G = [[i[4] for i in l] for l in tau_coeffs]
                self.tau_coeffs_H = [[i[5] for i in l] for l in tau_coeffs]
            else:
                raise ValueError("`tau_coeffs` is required")

            if alpha_coeffs is not None:
                self.alpha_coeffs_c = [[i[0] for i in l] for l in alpha_coeffs]
                self.alpha_coeffs_d = [[i[1] for i in l] for l in alpha_coeffs]
            else:
                raise ValueError("`alpha_coeffs` is required")

            self.N = N = len(self.tau_coeffs_A)

        self.cmps = range(N)

    @property
    def zero_coeffs(self):
        try:
            return self._zero_coeffs
        except AttributeError:
            pass
        N = self.N
        self._zero_coeffs = [[0.0]*N for _ in range(N)]
        return self._zero_coeffs


    def to_T_xs(self, T, xs):
        new = self.__class__.__new__(self.__class__)
        new.T = T
        new.xs = xs
        new.N = self.N
        new.cmps = self.cmps
        (new.tau_coeffs_A, new.tau_coeffs_B, new.tau_coeffs_E,
         new.tau_coeffs_F, new.tau_coeffs_G, new.tau_coeffs_H,
         new.alpha_coeffs_c, new.alpha_coeffs_d) = (self.tau_coeffs_A, self.tau_coeffs_B, self.tau_coeffs_E,
                         self.tau_coeffs_F, self.tau_coeffs_G, self.tau_coeffs_H,
                         self.alpha_coeffs_c, self.alpha_coeffs_d)

        if T == self.T:
            try:
                new._taus = self._taus
            except AttributeError:
                pass
            try:
                new._dtaus_dT = self._dtaus_dT
            except AttributeError:
                pass
            try:
                new._d2taus_dT2 = self._d2taus_dT2
            except AttributeError:
                pass
            try:
                new._d3taus_dT3 = self._d3taus_dT3
            except AttributeError:
                pass
            try:
                new._alphas = self._alphas
            except AttributeError:
                pass
            try:
                new._Gs = self._Gs
            except AttributeError:
                pass
            try:
                new._dGs_dT = self._dGs_dT
            except AttributeError:
                pass
            try:
                new._d2Gs_dT2 = self._d2Gs_dT2
            except AttributeError:
                pass
            try:
                new._d3Gs_dT3 = self._d3Gs_dT3
            except AttributeError:
                pass

        try:
            new._zero_coeffs = self.zero_coeffs
        except AttributeError:
            pass

        return new

    def GE(self):
        try:
            return self._GE
        except AttributeError:
            pass
        cmps = self.cmps
        xj_Gs_jis_inv, xj_Gs_taus_jis = self.xj_Gs_jis_inv(), self.xj_Gs_taus_jis()
        T, xs = self.T, self.xs

        tot = 0.0
        for i in cmps:
            tot += xs[i]*xj_Gs_taus_jis[i]*xj_Gs_jis_inv[i]
        self._GE = GE = T*R*tot
        return GE

    def gammas(self):
        try:
            return self._gammas
        except AttributeError:
            pass
        try:
            taus = self._taus
        except AttributeError:
            taus = self.taus()
        try:
            Gs = self._Gs
        except AttributeError:
            Gs = self.Gs()

        xs, cmps = self.xs, self.cmps

        xj_Gs_jis_inv, xj_Gs_taus_jis = self.xj_Gs_jis_inv(), self.xj_Gs_taus_jis()

        self._gammas = gammas = []

        t0s = [xs[j]*xj_Gs_jis_inv[j] for j in cmps]
        t1s = [xj_Gs_taus_jis[j]*xj_Gs_jis_inv[j] for j in cmps]

        for i in cmps:
            tot = xj_Gs_taus_jis[i]*xj_Gs_jis_inv[i]
            Gsi = Gs[i]
            tausi = taus[i]
            for j in cmps:
                # Possible to factor out some terms which depend on j only; or to index taus, Gs separately
                tot += t0s[j]*Gsi[j]*(tausi[j] - t1s[j])

            gammas.append(exp(tot))

#        self._gammas = gammas = NRTL_gammas(xs=self.xs, taus=taus, alphas=alphas)
        return gammas


    def taus(self):
        r'''Calculate the `tau` terms for the NRTL model for a specified
        temperature.

        .. math::
            \tau_{ij}=A_{ij}+\frac{B_{ij}}{T}+E_{ij}\ln T + F_{ij}T
            + \frac{G_{ij}}{T^2} + H_{ij}{T^2}


        These `tau ij` values (and the coefficients) are NOT symmetric
        normally.
        '''
        try:
            return self._taus
        except AttributeError:
            pass
        tau_coeffs_A = self.tau_coeffs_A
        tau_coeffs_B = self.tau_coeffs_B
        tau_coeffs_E = self.tau_coeffs_E
        tau_coeffs_F = self.tau_coeffs_F
        tau_coeffs_G = self.tau_coeffs_G
        tau_coeffs_H = self.tau_coeffs_H

        T, N, cmps = self.T, self.N, self.cmps
        T2 = T*T
        Tinv = 1.0/T
        T2inv = Tinv*Tinv
        logT = log(T)

        # initialize the matrix to be A
        self._taus = taus = [list(l) for l in tau_coeffs_A]
        for i in cmps:
            tau_coeffs_Bi = tau_coeffs_B[i]
            tau_coeffs_Ei = tau_coeffs_E[i]
            tau_coeffs_Fi = tau_coeffs_F[i]
            tau_coeffs_Gi = tau_coeffs_G[i]
            tau_coeffs_Hi = tau_coeffs_H[i]
            tausi = taus[i]
            for j in cmps:
                tausi[j] += tau_coeffs_Bi[j]*Tinv + tau_coeffs_Ei[j]*logT + tau_coeffs_Fi[j]*T + tau_coeffs_Gi[j]*T2inv + tau_coeffs_Hi[j]*T2
        return taus

    def dtaus_dT(self):
        r'''Calculate the temperature derivative of the `tau` terms for the
        NRTL model for a specified temperature.

        .. math::
            \frac{\partial \tau_{ij}} {\partial T}_{P, x_i} =
            - \frac{B_{ij}}{T^{2}} + \frac{E_{ij}}{T} + F_{ij}
            - \frac{2 G_{ij}}{T^{3}} + 2 H_{ij} T

        These `tau ij` values (and the coefficients) are NOT symmetric
        normally.
        '''
        try:
            return self._dtaus_dT
        except AttributeError:
            pass
        # Believed all correct but not tested
        tau_coeffs_B = self.tau_coeffs_B
        tau_coeffs_E = self.tau_coeffs_E
        tau_coeffs_F = self.tau_coeffs_F
        tau_coeffs_G = self.tau_coeffs_G
        tau_coeffs_H = self.tau_coeffs_H
        T, cmps = self.T, self.cmps

        Tinv = 1.0/T
        nT2inv = -Tinv*Tinv
        n2T3inv = 2.0*nT2inv*Tinv
        T2 = T + T

        self._dtaus_dT = dtaus_dT = [list(l) for l in tau_coeffs_F]
        for i in cmps:
            tau_coeffs_Bi = tau_coeffs_B[i]
            tau_coeffs_Ei = tau_coeffs_E[i]
            tau_coeffs_Fi = tau_coeffs_F[i]
            tau_coeffs_Gi = tau_coeffs_G[i]
            tau_coeffs_Hi = tau_coeffs_H[i]
            dtaus_dTi = dtaus_dT[i]
            for j in cmps:
                dtaus_dTi[j] += (nT2inv*tau_coeffs_Bi[j] + Tinv*tau_coeffs_Ei[j]
                + n2T3inv*tau_coeffs_Gi[j] + T2*tau_coeffs_Hi[j])

        return dtaus_dT

    def d2taus_dT2(self):
        r'''Calculate the second temperature derivative of the `tau` terms for
        the NRTL model for a specified temperature.

        .. math::
            \frac{\partial^2 \tau_{ij}} {\partial T^2}_{P, x_i} =
            \frac{2 B_{ij}}{T^{3}} - \frac{E_{ij}}{T^{2}} + \frac{6 G_{ij}}
            {T^{4}} + 2 H_{ij}

        These `tau ij` values (and the coefficients) are NOT symmetric
        normally.
        '''
        try:
            return self._d2taus_dT2
        except AttributeError:
            pass
        tau_coeffs_B = self.tau_coeffs_B
        tau_coeffs_E = self.tau_coeffs_E
        tau_coeffs_G = self.tau_coeffs_G
        tau_coeffs_H = self.tau_coeffs_H
        T, cmps = self.T, self.cmps

        self._d2taus_dT2 = d2taus_dT2 = [[h + h for h in l] for l in tau_coeffs_H]

        Tinv = 1.0/T
        Tinv2 = Tinv*Tinv

        T3inv2 = 2.0*(Tinv2*Tinv)
        nT2inv = -Tinv*Tinv
        T4inv6 = 6.0*(Tinv2*Tinv2)
        for i in cmps:
            tau_coeffs_Bi = tau_coeffs_B[i]
            tau_coeffs_Ei = tau_coeffs_E[i]
            tau_coeffs_Gi = tau_coeffs_G[i]
            d2taus_dT2i = d2taus_dT2[i]
            for j in cmps:
                d2taus_dT2i[j] += (T3inv2*tau_coeffs_Bi[j]
                                   + nT2inv*tau_coeffs_Ei[j]
                                   + T4inv6*tau_coeffs_Gi[j])
        return d2taus_dT2

    def d3taus_dT3(self):
        r'''Calculate the third temperature derivative of the `tau` terms for
        the NRTL model for a specified temperature.

        .. math::
            \frac{\partial^3 \tau_{ij}} {\partial T^3}_{P, x_i} =
            - \frac{6 B_{ij}}{T^{4}} + \frac{2 E_{ij}}{T^{3}}
            - \frac{24 G_{ij}}{T^{5}}

        These `tau ij` values (and the coefficients) are NOT symmetric
        normally.
        '''
        try:
            return self._d3taus_dT3
        except AttributeError:
            pass
        tau_coeffs_B = self.tau_coeffs_B
        tau_coeffs_E = self.tau_coeffs_E
        tau_coeffs_G = self.tau_coeffs_G
        T, N, cmps = self.T, self.N, self.cmps
        self._d3taus_dT3 = d3taus_dT3 = [[0.0]*N for i in cmps]

        Tinv = 1.0/T
        T2inv = Tinv*Tinv

        nT4inv6 = -6.0*T2inv*T2inv
        T3inv2 = 2.0*T2inv*Tinv
        T5inv24 = -24.0*(T2inv*T2inv*Tinv)

        for i in cmps:
            tau_coeffs_Bi = tau_coeffs_B[i]
            tau_coeffs_Ei = tau_coeffs_E[i]
            tau_coeffs_Gi = tau_coeffs_G[i]
            d3taus_dT3i = d3taus_dT3[i]
            for j in cmps:
                d3taus_dT3i[j] = (nT4inv6*tau_coeffs_Bi[j]
                                  + T3inv2*tau_coeffs_Ei[j]
                                  + T5inv24*tau_coeffs_Gi[j])
        return d3taus_dT3



    def alphas(self):
        '''Calculates the `alpha` terms in the NRTL model for a specified
        temperature.

        .. math::
            \alpha_{ij}=c_{ij}+d_{ij}T

        `alpha` values (and therefore `cij` and `dij` are normally symmetrical;
        but this is not strictly required.

        Some sources suggest the c term should be fit to a given system; but
        the `d` term should be fit for an entire chemical family to avoid
        overfitting.

        Recommended values for `cij` according to one source are:

        0.30 Nonpolar substances with nonpolar substances; low deviation from ideality.
        0.20 Hydrocarbons that are saturated interacting with polar liquids that do not associate, or systems that for multiple liquid phases which are immiscible
        0.47 Strongly self associative systems, interacting with non-polar substances

        `alpha_coeffs` should be a list[list[cij, dij]] so a 3d array
        '''
        try:
            return self._alphas
        except AttributeError:
            pass
        T, cmps = self.T, self.cmps
        alpha_coeffs_c, alpha_coeffs_d = self.alpha_coeffs_c, self.alpha_coeffs_d

        self._alphas = alphas = []
        for i in cmps:
            alpha_coeffs_ci = alpha_coeffs_c[i]
            alpha_coeffs_di = alpha_coeffs_d[i]
            alphas.append([alpha_coeffs_ci[j] + alpha_coeffs_di[j]*T for j in cmps])

        return alphas

    def dalphas_dT(self):
        return self.alpha_coeffs_d

    def d2alphas_dT2(self):
        return self.zero_coeffs

    def d3alphas_dT3(self):
        return self.zero_coeffs

    def Gs(self):
        try:
            return self._Gs
        except AttributeError:
            pass
        alphas = self.alphas()
        taus = self.taus()
        cmps = self.cmps

        self._Gs = Gs = []
        for i in cmps:
            alphasi = alphas[i]
            tausi = taus[i]
            Gs.append([exp(-alphasi[j]*tausi[j]) for j in cmps])
        return Gs

    def dGs_dT(self):
        r'''
        .. math::
            \left(- \alpha{\left(T \right)} \frac{d}{d T} \tau{\left(T \right)}
            - \tau{\left(T \right)} \frac{d}{d T} \alpha{\left(T \right)}\right)
            e^{- \alpha{\left(T \right)} \tau{\left(T \right)}}

        from sympy import *
        T = symbols('T')
        alpha, tau = symbols('alpha, tau', cls=Function)

        diff(exp(-alpha(T)*tau(T)), T)
        '''
        try:
            return self._dGs_dT
        except AttributeError:
            pass
        alphas = self.alphas()
        dalphas_dT = self.dalphas_dT()
        taus = self.taus()
        dtaus_dT = self.dtaus_dT()
        Gs = self.Gs()
        cmps = self.cmps

        self._dGs_dT = dGs_dT = []
        for i in cmps:
            alphasi = alphas[i]
            tausi = taus[i]
            dalphasi = dalphas_dT[i]
            dtausi = dtaus_dT[i]
            Gsi = Gs[i]

            dGs_dT.append([(-alphasi[j]*dtausi[j] - tausi[j]*dalphasi[j])*Gsi[j]
                    for j in cmps])
        return dGs_dT

    def d2Gs_dT2(self):
        r'''
        .. math::
            \left(\left(\alpha{\left(T \right)} \frac{d}{d T} \tau{\left(T \right)} + \tau{\left(T \right)} \frac{d}{d T} \alpha{\left(T \right)}\right)^{2} - \alpha{\left(T \right)} \frac{d^{2}}{d T^{2}} \tau{\left(T \right)} - 2 \frac{d}{d T} \alpha{\left(T \right)} \frac{d}{d T} \tau{\left(T \right)}\right) e^{- \alpha{\left(T \right)} \tau{\left(T \right)}}


        from sympy import *
        T = symbols('T')
        alpha, tau = symbols('alpha, tau', cls=Function)
        expr = diff(exp(-alpha(T)*tau(T)), T, 2)
        expr = ((alpha(T)*Derivative(tau(T), T) + tau(T)*Derivative(alpha(T), T))**2 - alpha(T)*Derivative(tau(T), (T, 2)) - 2*Derivative(alpha(T), T)*Derivative(tau(T), T))*exp(-alpha(T)*tau(T))
        simplify(expr)
        '''
        try:
            return self._d2Gs_dT2
        except AttributeError:
            pass
        alphas = self.alphas()
        dalphas_dT = self.dalphas_dT()
        taus = self.taus()
        dtaus_dT = self.dtaus_dT()
        d2taus_dT2 = self.d2taus_dT2()
        Gs = self.Gs()
        cmps = self.cmps

        self._d2Gs_dT2 = d2Gs_dT2 = []
        for i in cmps:
            alphasi = alphas[i]
            tausi = taus[i]
            dalphasi = dalphas_dT[i]
            dtausi = dtaus_dT[i]
            d2taus_dT2i = d2taus_dT2[i]
            Gsi = Gs[i]

            d2Gs_dT2_row = []
            for j in cmps:
                t1 = alphasi[j]*dtausi[j] + tausi[j]*dalphasi[j]
                d2Gs_dT2_row.append((t1*t1 - alphasi[j]*d2taus_dT2i[j]
                                     - 2.0*dalphasi[j]*dtausi[j])*Gsi[j])
            d2Gs_dT2.append(d2Gs_dT2_row)
        return d2Gs_dT2

    def d3Gs_dT3(self):
        '''
        ... math::
            \left(\alpha{\left(T \right)} \frac{d}{d T} \tau{\left(T \right)} + \tau{\left(T \right)} \frac{d}{d T} \alpha{\left(T \right)}\right)^{3} + \left(3 \alpha{\left(T \right)} \frac{d}{d T} \tau{\left(T \right)} + 3 \tau{\left(T \right)} \frac{d}{d T} \alpha{\left(T \right)}\right) \left(\alpha{\left(T \right)} \frac{d^{2}}{d T^{2}} \tau{\left(T \right)} + 2 \frac{d}{d T} \alpha{\left(T \right)} \frac{d}{d T} \tau{\left(T \right)}\right) - \alpha{\left(T \right)} \frac{d^{3}}{d T^{3}} \tau{\left(T \right)} - 3 \frac{d}{d T} \alpha{\left(T \right)} \frac{d^{2}}{d T^{2}} \tau{\left(T \right)}
        '''
        '''
        from sympy import *
        T = symbols('T')
        alpha, tau = symbols('alpha, tau', cls=Function)
        expr = diff(exp(-alpha(T)*tau(T)), T, 3)
        expr.subs(Derivative(alpha(T), T, T, T), 0).subs(Derivative(alpha(T), T, T),  0)
        '''
        try:
            return self._d3Gs_dT3
        except AttributeError:
            pass
        cmps = self.cmps
        alphas = self.alphas()
        dalphas_dT = self.dalphas_dT()
        taus = self.taus()
        dtaus_dT = self.dtaus_dT()
        d2taus_dT2 = self.d2taus_dT2()
        d3taus_dT3 = self.d3taus_dT3()
        Gs = self.Gs()

        self._d3Gs_dT3 = d3Gs_dT3 = []
        for i in cmps:
            alphasi = alphas[i]
            tausi = taus[i]
            dalphasi = dalphas_dT[i]
            dtaus_dTi = dtaus_dT[i]
            d2taus_dT2i = d2taus_dT2[i]
            d3taus_dT3i = d3taus_dT3[i]
            Gsi = Gs[i]
            d3Gs_dT3_row = []
            for j in cmps:
                x0 = alphasi[j]
                x1 = tausi[j]
                x2 = dalphasi[j]

                x3 = d2taus_dT2i[j]
                x4 = dtaus_dTi[j]
                x5 = x0*x4 + x1*x2
                v = Gsi[j]*(-x0*d3taus_dT3i[j] - 3.0*x2*x3 - x5*x5*x5 + 3.0*x5*(x0*x3 + 2.0*x2*x4))
                d3Gs_dT3_row.append(v)
            d3Gs_dT3.append(d3Gs_dT3_row)
        return d3Gs_dT3


    def dGE_dxs(self):
        '''
        from sympy import *
        N = 3
        R, T = symbols('R, T')
        x0, x1, x2 = symbols('x0, x1, x2')
        xs = [x0, x1, x2]

        tau00, tau01, tau02, tau10, tau11, tau12, tau20, tau21, tau22 = symbols(
            'tau00, tau01, tau02, tau10, tau11, tau12, tau20, tau21, tau22', cls=Function)
        tau_ijs = [[tau00(T), tau01(T), tau02(T)],
                   [tau10(T), tau11(T), tau12(T)],
                   [tau20(T), tau21(T), tau22(T)]]


        G00, G01, G02, G10, G11, G12, G20, G21, G22 = symbols(
            'G00, G01, G02, G10, G11, G12, G20, G21, G22', cls=Function)
        G_ijs = [[G00(T), G01(T), G02(T)],
                   [G10(T), G11(T), G12(T)],
                   [G20(T), G21(T), G22(T)]]
        ge = 0
        for i in [2]:#range(0):
            num = 0
            den = 0
            for j in range(N):
                num += tau_ijs[j][i]*G_ijs[j][i]*xs[j]
                den += G_ijs[j][i]*xs[j]
            ge += xs[i]*num/den
        ge = ge#*R*T
        diff(ge, x1), diff(ge, x2)
        '''
        try:
            return self._dGE_dxs
        except AttributeError:
            pass
        T, xs, cmps = self.T, self.xs, self.cmps
        RT = R*T
        taus = self.taus()
        Gs = self.Gs()
        xj_Gs_jis_inv = self.xj_Gs_jis_inv()
        xj_Gs_taus_jis = self.xj_Gs_taus_jis()

        self._dGE_dxs = dGE_dxs = []

        for k in cmps:
            # k is what is being differentiated
            tot = xj_Gs_taus_jis[k]*xj_Gs_jis_inv[k]
            for i in cmps:
                tot += xs[i]*xj_Gs_jis_inv[i]*Gs[k][i]*(taus[k][i] - xj_Gs_jis_inv[i]*xj_Gs_taus_jis[i])
            dGE_dxs.append(tot*RT)
        return dGE_dxs

    def xj_Gs_jis(self):
        # sum1
        try:
            return self._xj_Gs_jis
        except AttributeError:
            pass
        try:
            Gs = self._Gs
        except AttributeError:
            Gs = self.Gs()
        try:
            taus = self._taus
        except AttributeError:
            taus = self.taus()

        xs, cmps = self.xs, self.cmps
        self._xj_Gs_jis = xj_Gs_jis = []
        self._xj_Gs_taus_jis = xj_Gs_taus_jis = []
        for i in cmps:
            tot1 = 0.0
            tot2 = 0.0
            for j in cmps:
                xjGji = xs[j]*Gs[j][i]
                tot1 += xjGji#xs[j]*Gs[j][i]
                tot2 += xjGji*taus[j][i]
            xj_Gs_jis.append(tot1)
            xj_Gs_taus_jis.append(tot2)
        return xj_Gs_jis

    def xj_Gs_jis_inv(self):
        try:
            return self._xj_Gs_jis_inv
        except AttributeError:
            pass

        try:
            xj_Gs_jis = self._xj_Gs_jis
        except AttributeError:
            xj_Gs_jis = self.xj_Gs_jis()

        self._xj_Gs_jis_inv = [1.0/i for i in xj_Gs_jis]
        return self._xj_Gs_jis_inv

    def xj_Gs_taus_jis(self):
        # sum2
        try:
            return self._xj_Gs_taus_jis
        except AttributeError:
            self.xj_Gs_jis()
            return self._xj_Gs_taus_jis

        try:
            Gs = self._Gs
        except AttributeError:
            Gs = self.Gs()

        try:
            taus = self._taus
        except AttributeError:
            taus = self.taus()

        xs, cmps = self.xs, self.cmps
        self._xj_Gs_taus_jis = xj_Gs_taus_jis = []

        for i in cmps:
            tot = 0.0
            for j in cmps:
                # Could use sum1
                tot += xs[j]*Gs[j][i]*taus[j][i]
            xj_Gs_taus_jis.append(tot)
        return xj_Gs_taus_jis


    def xj_dGs_dT_jis(self):
        # sum3
        try:
            return self._xj_dGs_dT_jis
        except AttributeError:
            pass
        try:
            dGs_dT = self._dGs_dT
        except AttributeError:
            dGs_dT = self.dGs_dT()

        xs, cmps = self.xs, self.cmps
        self._xj_dGs_dT_jis = xj_dGs_dT_jis = []
        for i in cmps:
            tot = 0.0
            for j in cmps:
                tot += xs[j]*dGs_dT[j][i]
            xj_dGs_dT_jis.append(tot)
        return xj_dGs_dT_jis

    def xj_taus_dGs_dT_jis(self):
        # sum4
        try:
            return self._xj_taus_dGs_dT_jis
        except AttributeError:
            pass
        xs, cmps = self.xs, self.cmps
        try:
            dGs_dT = self._dGs_dT
        except AttributeError:
            dGs_dT = self.dGs_dT()
        try:
            taus = self._taus
        except AttributeError:
            taus = self.taus()

        self._xj_taus_dGs_dT_jis = xj_taus_dGs_dT_jis = []

        for i in cmps:
            tot = 0.0
            for j in cmps:
                tot += xs[j]*taus[j][i]*dGs_dT[j][i]
            xj_taus_dGs_dT_jis.append(tot)
        return xj_taus_dGs_dT_jis

    def xj_Gs_dtaus_dT_jis(self):
        # sum5
        try:
            return self._xj_Gs_dtaus_dT_jis
        except AttributeError:
            pass
        xs, cmps = self.xs, self.cmps
        try:
            dtaus_dT = self._dtaus_dT
        except AttributeError:
            dtaus_dT = self.dtaus_dT()
        try:
            Gs = self._Gs
        except AttributeError:
            Gs = self.Gs()

        self._xj_Gs_dtaus_dT_jis = xj_Gs_dtaus_dT_jis = []
        for i in cmps:
            tot = 0.0
            for j in cmps:
                tot += xs[j]*Gs[j][i]*dtaus_dT[j][i]
            xj_Gs_dtaus_dT_jis.append(tot)
        return xj_Gs_dtaus_dT_jis

    def d2GE_dxixjs(self):
        r'''

        .. math::
            \frac{\partial^2 g^E}{\partial x_i \partial x_j} = RT\left[
            + \frac{G_{ij}\tau_{ij}}{\sum_m x_m G_{mj}}
            + \frac{G_{ji}\tau_{jiij}}{\sum_m x_m G_{mi}}
            -\frac{(\sum_m x_m G_{mj}\tau_{mj})G_{ij}}{(\sum_m x_m G_{mj})^2}
            -\frac{(\sum_m x_m G_{mi}\tau_{mi})G_{ji}}{(\sum_m x_m G_{mi})^2}
            \sum_k \left(\frac{2x_k(\sum_m x_m \tau_{mk}G_{mk})G_{ik}G_{jk}}{(\sum_m x_m G_{mk})^3}
            - \frac{x_k G_{ik}G_{jk}(\tau_{jk} + \tau_{ik})}{(\sum_m x_m G_{mk})^2}
            \right)
            \right]
        '''
        '''
        from sympy import *
        N = 3
        R, T = symbols('R, T')
        x0, x1, x2 = symbols('x0, x1, x2')
        xs = [x0, x1, x2]

        tau00, tau01, tau02, tau10, tau11, tau12, tau20, tau21, tau22 = symbols(
            'tau00, tau01, tau02, tau10, tau11, tau12, tau20, tau21, tau22', cls=Function)
        tau_ijs = [[tau00(T), tau01(T), tau02(T)],
                   [tau10(T), tau11(T), tau12(T)],
                   [tau20(T), tau21(T), tau22(T)]]


        G00, G01, G02, G10, G11, G12, G20, G21, G22 = symbols(
            'G00, G01, G02, G10, G11, G12, G20, G21, G22', cls=Function)
        G_ijs = [[G00(T), G01(T), G02(T)],
                   [G10(T), G11(T), G12(T)],
                   [G20(T), G21(T), G22(T)]]

        tauG00, tauG01, tauG02, tauG10, tauG11, tauG12, tauG20, tauG21, tauG22 = symbols(
            'tauG00, tauG01, tauG02, tauG10, tauG11, tauG12, tauG20, tauG21, tauG22', cls=Function)
        tauG_ijs = [[tauG00(T), tauG01(T), tauG02(T)],
                   [tauG10(T), tauG11(T), tauG12(T)],
                   [tauG20(T), tauG21(T), tauG22(T)]]


        ge = 0
        for i in range(N):#range(0):
            num = 0
            den = 0
            for j in range(N):
        #         num += G_ijs[j][i]*tau_ijs[j][i]*xs[j]
                num += tauG_ijs[j][i]*xs[j]
                den += G_ijs[j][i]*xs[j]

            ge += xs[i]*num/den
        ge = ge#R*T

        diff(ge, x0, x1)
        '''
        try:
            return self._d2GE_dxixjs
        except AttributeError:
            pass
        T, xs, cmps = self.T, self.xs, self.cmps
        taus = self.taus()
        alphas = self.alphas()
        Gs = self.Gs()
        xj_Gs_jis_inv = self.xj_Gs_jis_inv()
        xj_Gs_taus_jis = self.xj_Gs_taus_jis()
        RT = R*T

        self._d2GE_dxixjs = d2GE_dxixjs = []


        for i in cmps:
            row = []
            for j in cmps:
                tot = 0.0
                # two small terms
                tot += Gs[i][j]*taus[i][j]*xj_Gs_jis_inv[j]
                tot += Gs[j][i]*taus[j][i]*xj_Gs_jis_inv[i]

                # Two large terms
                tot -= xj_Gs_taus_jis[j]*Gs[i][j]*(xj_Gs_jis_inv[j]*xj_Gs_jis_inv[j])
                tot -= xj_Gs_taus_jis[i]*Gs[j][i]*(xj_Gs_jis_inv[i]*xj_Gs_jis_inv[i])

                # Three terms
                for k in cmps:
                    tot += 2.0*xs[k]*xj_Gs_taus_jis[k]*Gs[i][k]*Gs[j][k]*(xj_Gs_jis_inv[k]*xj_Gs_jis_inv[k]*xj_Gs_jis_inv[k])

                # 6 terms
                for k in cmps:
                    tot -= xs[k]*Gs[i][k]*Gs[j][k]*(taus[j][k] + taus[i][k])*xj_Gs_jis_inv[k]*xj_Gs_jis_inv[k]

                tot *= RT
                row.append(tot)
            d2GE_dxixjs.append(row)
        return d2GE_dxixjs


    def d2GE_dTdxs(self):
        r'''
        .. math::
            \frac{\partial^2 g^E}{\partial x_i \partial T} = R\left[-T\left(
            \sum_j \left(
            -\frac{x_j(G_{ij}\frac{\partial \tau_{ij}}{\partial T} + \tau_{ij}\frac{\partial G_{ij}}{\partial T})}{\sum_k x_k G_{kj}}
            + \frac{x_j G_{ij}\tau_{ij}(\sum_k x_k \frac{\partial G_{kj}}{\partial T})}{(\sum_k x_k G_{kj})^2}
            +\frac{x_j \frac{\partial G_{ij}}{\partial T}(\sum_k x_k G_{kj}\tau_{kj})}{(\sum_k x_k G_{kj})^2}
            + \frac{x_jG_{ij}(\sum_k x_k (G_{kj} \frac{\partial \tau_{kj}}{\partial T}  + \tau_{kj} \frac{\partial G_{kj}}{\partial T} ))}{(\sum_k x_k G_{kj})^2}
            -2\frac{x_j G_{ij} (\sum_k x_k \frac{\partial G_{kj}}{\partial T})(\sum_k x_k G_{kj}\tau_{kj})}{(\sum_k x_k G_{kj})^3}
            \right)
            - \frac{\sum_k (x_k G_{ki} \frac{\partial \tau_{ki}}{\partial T}  + x_k \tau_{ki} \frac{\partial G_{ki}}{\partial T}} {\sum_k x_k G_{ki}}
            + \frac{(\sum_k x_k \frac{\partial G_{ki}}{\partial T})(\sum_k x_k G_{ki} \tau_{ki})}{(\sum_k x_k G_{ki})^2}
            \right)
            + \frac{\sum_j x_j G_{ji}\tau_{ji}}{\sum_j x_j G_{ji}} + \sum_j \left(
            \frac{x_j G_{ij}(\sum_k x_k G_{kj}\tau_{kj})}{(\sum_k x_k G_{kj})^2} + \frac{x_j G_{ij}\tau_{ij}}{\sum_k x_k G_{kj}}
            \right)
            \right]
        '''
        try:
            return self._d2GE_dTdxs
        except AttributeError:
            pass

        sum1 = self.xj_Gs_jis_inv()
        sum2 = self.xj_Gs_taus_jis()
        sum3 = self.xj_dGs_dT_jis()
        sum4 = self.xj_taus_dGs_dT_jis()
        sum5 = self.xj_Gs_dtaus_dT_jis()


        T, xs, cmps = self.T, self.xs, self.cmps
        taus = self.taus()
        dtaus_dT = self.dtaus_dT()

        Gs = self.Gs()
        dGs_dT = self.dGs_dT()

        xs_sum1s = [xs[i]*sum1[i] for i in cmps]
        sum1_sum2s = [sum1[i]*sum2[i] for i in cmps]

        self._d2GE_dTdxs = d2GE_dTdxs = []
        for i in cmps:
            others = sum1_sum2s[i]
            tot1 = sum1[i]*(sum3[i]*sum1_sum2s[i] - (sum5[i] + sum4[i])) # Last singleton and second last singleton

            Gsi = Gs[i]
            tausi = taus[i]
            for j in cmps:
                t0 = sum1_sum2s[j]*dGs_dT[i][j]
                t0 += sum1[j]*Gsi[j]*(sum3[j]*(tausi[j] - sum1_sum2s[j] - sum1_sum2s[j]) + sum5[j] + sum4[j]) # Could store and factor this stuff out but just makes it slower
                t0 -= (Gsi[j]*dtaus_dT[i][j] + tausi[j]*dGs_dT[i][j])

                tot1 += t0*xs_sum1s[j]

                others += xs_sum1s[j]*Gsi[j]*(tausi[j] - sum1_sum2s[j])

            dG = -R*(T*tot1 - others)
            d2GE_dTdxs.append(dG)
        return d2GE_dTdxs

    def dGE_dT(self):
        '''from sympy import *
        R, T, x = symbols('R, T, x')
        g, tau = symbols('g, tau', cls=Function)
        m, n, o = symbols('m, n, o', cls=Function)
        r, s, t = symbols('r, s, t', cls=Function)
        u, v, w = symbols('u, v, w', cls=Function)
        diff(T* (m(T)*n(T) + r(T)*s(T) + u(T)*v(T))/(o(T) + t(T) + w(T)), T)
        '''
        try:
            return self._dGE_dT
        except AttributeError:
            pass
        T, xs, cmps = self.T, self.xs, self.cmps

        xj_Gs_jis_inv = self.xj_Gs_jis_inv() # sum1 inv
        xj_Gs_taus_jis = self.xj_Gs_taus_jis() # sum2
        xj_dGs_dT_jis = self.xj_dGs_dT_jis() # sum3
        xj_taus_dGs_dT_jis = self.xj_taus_dGs_dT_jis() # sum4
        xj_Gs_dtaus_dT_jis = self.xj_Gs_dtaus_dT_jis() # sum5

        tot = 0.0
        for i in cmps:
            tot += (xs[i]*(xj_Gs_taus_jis[i] + T*((xj_taus_dGs_dT_jis[i] + xj_Gs_dtaus_dT_jis[i])
                    - (xj_Gs_taus_jis[i]*xj_dGs_dT_jis[i])*xj_Gs_jis_inv[i]))*xj_Gs_jis_inv[i])
        self._dGE_dT = R*tot
        return self._dGE_dT

    def d2GE_dT2(self):
        '''from sympy import *
        R, T, x = symbols('R, T, x')
        g, tau = symbols('g, tau', cls=Function)
        m, n, o = symbols('m, n, o', cls=Function)
        r, s, t = symbols('r, s, t', cls=Function)
        u, v, w = symbols('u, v, w', cls=Function)

        (diff(T*(m(T)*n(T) + r(T)*s(T))/(o(T) + t(T)), T, 2))
        '''
        try:
            return self._d2GE_dT2
        except AttributeError:
            pass
        T, xs, cmps = self.T, self.xs, self.cmps
        taus = self.taus()
        dtaus_dT = self.dtaus_dT()
        d2taus_dT2 = self.d2taus_dT2()

        alphas = self.alphas()
        dalphas_dT = self.dalphas_dT()

        Gs = self.Gs()
        dGs_dT = self.dGs_dT()
        d2Gs_dT2 = self.d2Gs_dT2()

        tot = 0
        for i in cmps:
            sum1 = 0.0
            sum2 = 0.0
            sum3 = 0.0
            sum4 = 0.0
            sum5 = 0.0

            sum6 = 0.0
            sum7 = 0.0
            sum8 = 0.0
            sum9 = 0.0
            for j in cmps:
                tauji = taus[j][i]
                dtaus_dTji = dtaus_dT[j][i]

                Gjixj = Gs[j][i]*xs[j]
                dGjidTxj = dGs_dT[j][i]*xs[j]
                d2GjidT2xj = xs[j]*d2Gs_dT2[j][i]

                sum1 += Gjixj
                sum2 += tauji*Gjixj
                sum3 += dGjidTxj

                sum4 += tauji*dGjidTxj
                sum5 += dtaus_dTji*Gjixj

                sum6 += d2GjidT2xj

                sum7 += tauji*d2GjidT2xj

                sum8 += Gjixj*d2taus_dT2[j][i]

                sum9 += dGjidTxj*dtaus_dTji

            term1 = -T*sum2*(sum6 - 2.0*sum3*sum3/sum1)/sum1
            term2 = T*(sum7 + sum8 + 2.0*sum9)
            term3 = -2*T*(sum3*(sum4 + sum5))/sum1
            term4 = -2.0*(sum2*sum3)/sum1
            term5 = 2*(sum4 + sum5)

            tot += xs[i]*(term1 + term2 + term3 + term4 + term5)/sum1
        self._d2GE_dT2 = d2GE_dT2 = R*tot
        return d2GE_dT2


def NRTL_gammas(xs, taus, alphas):
    r'''Calculates the activity coefficients of each species in a mixture
    using the Non-Random Two-Liquid (NRTL) method, given their mole fractions,
    dimensionless interaction parameters, and nonrandomness constants. Those
    are normally correlated with temperature in some form, and need to be
    calculated separately.

    .. math::
        \ln(\gamma_i)=\frac{\displaystyle\sum_{j=1}^{n}{x_{j}\tau_{ji}G_{ji}}}
        {\displaystyle\sum_{k=1}^{n}{x_{k}G_{ki}}}+\sum_{j=1}^{n}
        {\frac{x_{j}G_{ij}}{\displaystyle\sum_{k=1}^{n}{x_{k}G_{kj}}}}
        {\left ({\tau_{ij}-\frac{\displaystyle\sum_{m=1}^{n}{x_{m}\tau_{mj}
        G_{mj}}}{\displaystyle\sum_{k=1}^{n}{x_{k}G_{kj}}}}\right )}

        G_{ij}=\text{exp}\left ({-\alpha_{ij}\tau_{ij}}\right )

    Parameters
    ----------
    xs : list[float]
        Liquid mole fractions of each species, [-]
    taus : list[list[float]]
        Dimensionless interaction parameters of each compound with each other,
        [-]
    alphas : list[list[float]]
        Nonrandomness constants of each compound interacting with each other, [-]

    Returns
    -------
    gammas : list[float]
        Activity coefficient for each species in the liquid mixture, [-]

    Notes
    -----
    This model needs N^2 parameters.

    One common temperature dependence of the nonrandomness constants is:

    .. math::
        \alpha_{ij}=c_{ij}+d_{ij}T

    Most correlations for the interaction parameters include some of the terms
    shown in the following form:

    .. math::
        \tau_{ij}=A_{ij}+\frac{B_{ij}}{T}+\frac{C_{ij}}{T^{2}}+D_{ij}
        \ln{\left ({T}\right )}+E_{ij}T^{F_{ij}}

    The original form of this model used the temperature dependence of taus in
    the form (values can be found in the literature, often with units of
    calories/mol):

    .. math::
        \tau_{ij}=\frac{b_{ij}}{RT}

    For this model to produce ideal acitivty coefficients (gammas = 1),
    all interaction parameters should be 0; the value of alpha does not impact
    the calculation when that is the case.

    Examples
    --------
    Ethanol-water example, at 343.15 K and 1 MPa:

    >>> NRTL_gammas(xs=[0.252, 0.748], taus=[[0, -0.178], [1.963, 0]],
    ... alphas=[[0, 0.2974],[.2974, 0]])
    [1.9363183763514304, 1.1537609663170014]

    References
    ----------
    .. [1] Renon, Henri, and J. M. Prausnitz. "Local Compositions in
       Thermodynamic Excess Functions for Liquid Mixtures." AIChE Journal 14,
       no. 1 (1968): 135-144. doi:10.1002/aic.690140124.
    .. [2] Gmehling, Jurgen, Barbel Kolbe, Michael Kleiber, and Jurgen Rarey.
       Chemical Thermodynamics for Process Simulation. 1st edition. Weinheim:
       Wiley-VCH, 2012.
    '''
    gammas = []
    cmps = range(len(xs))
    # Gs does not depend on composition
    Gs = []
    for i in cmps:
        alphasi = alphas[i]
        tausi = taus[i]
        Gs.append([exp(-alphasi[j]*tausi[j]) for j in cmps])


    td2s = []
    tn3s = []
    for j in cmps:
        td2 = 0.0
        tn3 = 0.0
        for k in cmps:
            xkGkj = xs[k]*Gs[k][j]
            td2 += xkGkj
            tn3 += xkGkj*taus[k][j]
        td2 = 1.0/td2
        td2xj = td2*xs[j]
        td2s.append(td2xj)
        tn3s.append(tn3*td2*td2xj)

    for i in cmps:
        tn1, td1, total2 = 0., 0., 0.
        Gsi = Gs[i]
        tausi = taus[i]
        for j in cmps:
            xjGji = xs[j]*Gs[j][i]

            td1 += xjGji
            tn1 += xjGji*taus[j][i]
            total2 += Gsi[j]*(tausi[j]*td2s[j] - tn3s[j])

        gamma = exp(tn1/td1 + total2)
        gammas.append(gamma)
    return gammas