import copy

import numpy as np
import scipy.signal
import h5py
import matplotlib.pyplot as plt

e = 1.602176462e-19
hbar = 1.05457159682e-34
m = 9.1093818872e-31
eps0 = 8.854187817e-12
kB = 1.380650324e-23
c = 299792458

figureSize = [30,12]
tickSize = 48
fontSize = 55
lineWidth = 6
legendFontSize = 41
axisLineWidth = 3

def check_equal_length(*arg):

    n = len(arg[0])
    for v in arg:
        if len(v) != n:
            print(v)
            print('Error: vector size mismatch')
            raise Exception('Vector size mismatch')

def fourier_transform(TimeV, FieldV):   # complex!!!

    freq = np.fft.fftfreq(TimeV.size, d=TimeV[1]-TimeV[0])
    fft = np.fft.fft(FieldV)
    return freq, fft

def inverse_fourier_transform(freq, fullSpectrum):  # complex!!!

    timeV = np.fft.fftfreq(len(freq), freq[1]-freq[0])
    if len(timeV)%2 == 0:
        timeV = np.concatenate((timeV[int(len(timeV)/2):], timeV[:int(len(timeV)/2)]))
    else:
        timeV = np.concatenate((timeV[int((len(timeV)+1)/2):], timeV[:int((len(timeV)+1)/2)]))
    fieldV = np.fft.ifft(fullSpectrum)

    return timeV, fieldV

class LunaResult:
    """Loads and handles the Luna simulation result.

    The result must be in the HDF5 format using the saving option in the Luna.Interface.prop_capillary() function [filepath="..."].
    As opposed to most of the analysis routines here, units are in SI!

    Attributes:
        z: position along the fiber (for the field data)
        fieldFT: complex FFT of the field (positive freq axis); shape: (n_z, n_modes, n_freq) [or (n_z, n_freq) after mode selection/averaging]
        omega: angular frequency axis for the FFT field; shape: (n_z, n_modes, n_freq) [or (n_z, n_freq) after mode selection/averaging]

        stats_z: position along the fiber (for stats data)
        stats_density: particle density along the fiber (m^-3)
        stats_electrondensity: electron density along the fiber (m^-3)
        stats_pressure: gas pressure profile along the fiber (bar)
        stats_energy: pulse energy along the fiber (J)
        stats_peakpower: peak power of the pulse along the fiber (W)
        stats_peakintensity: peak intensity of the pulse along the fiber
        stats_peak_ionization_rate: peak ionization rate along the fiber
        """
    def __init__(self, filename):
        """Constructor of class LunaResult.

        Args:
            filename: saved result, file path
            """

        self.filename = filename
        self.fieldFT = None
        self.omega = None
        self.z = None

        self.stats_z = None
        self.stats_energy = None
        self.stats_electrondensity = None
        self.stats_density = None
        self.stats_pressure = None
        self.stats_peakpower = None
        self.stats_peakintensity = None
        self.stats_zdw = None
        self.stats_peak_ionization_rate = None

        self.open_Luna_result(filename)

    def open_Luna_result(self, filename):
        """Opens the Luna result file and loads the data"""
        with h5py.File(filename, 'r') as data:

            # FIELD DATA
            self.fieldFT = np.array(data['Eω'])
            self.omega = np.array(data['grid']['ω'])
            self.z = np.array(data['z'])

            # STATS
            self.stats_z = np.array(data['stats']['z'])
            self.stats_energy = np.array(data['stats']['energy'])
            self.stats_electrondensity = np.array(data['stats']['electrondensity'])
            self.stats_density = np.array(data['stats']['density'])
            self.stats_pressure = np.array(data['stats']['pressure'])
            self.stats_peakpower = np.array(data['stats']['peakpower'])
            self.stats_peakintensity = np.array(data['stats']['peakintensity'])
            self.stats_zdw = np.array(data['stats']['zdw'])
            self.stats_peak_ionization_rate = np.array(data['stats']['peak_ionisation_rate'])

    def average_modes(self):
        """Averages the propagation modes in the Luna result file"""
        if len(self.fieldFT.shape) == 3:
            self.fieldFT = np.sum(self.fieldFT, axis=1)
            self.stats_zdw = None
            self.stats_peakpower = None
            self.stats_energy = np.sum(self.stats_energy, axis=1)

    def select_mode(self, mode: int):
        if len(self.fieldFT.shape) < 3:
            print("WARNING: No mode to select")
        elif mode >= self.fieldFT.shape[1] or mode < 0:
            print("WARNING: mode ", mode, " is out of range")
        else:
            self.fieldFT = self.fieldFT[:, mode, :]
            self.stats_zdw = self.stats_zdw[:, mode]
            self.stats_peakpower = self.stats_peakpower[:, mode]
            self.stats_energy = self.stats_energy[:, mode]

    def get_time_field(self, position=None):
        """Get the electric field in time from the Luna result file. If no mode was previously selected, the method computes the average of all modes.
        Therefore, after calling get_time_field(), mode selection is not possible any more.

        Args:
            position (float): position along the fiber in m. If None, the end of the fiber is used.

        Returns:
            timeV (numpy.ndarray): time axis in seconds
            fieldV (numpy.ndarray): electric field in V/m
        """
        self.average_modes()
        if position is None:
            position = self.z[-1]
        index = np.argmin(np.abs(self.z - position))
        if position > np.max(self.z) or position < np.min(self.z):
            print("WARNING: position ", position, "m is out of range")
        check_equal_length(self.fieldFT[index], self.omega)
        fieldFFT = np.concatenate((self.fieldFT[index, :], np.conjugate(self.fieldFT[index, :][::-1])*0))
        freq = np.concatenate((self.omega, -self.omega[::-1])) / 2 / np.pi
        timeV, fieldV = inverse_fourier_transform(freq, fieldFFT)
        return timeV, np.real(fieldV)

    def get_wavelength_spectrum(self, position=None):
        """Get the spectrum from the Luna result file (|FFT|^2 * (2 * pi * c / λ^2))

        Args:
            position (float): position along the fiber in m. If None, the end of the fiber is used.

        Returns:
            wvl (numpy.ndarray): wavelength axis in m
            wvlSpectrum (numpy.ndarray): electric field spectrum in V/m
        """
        self.average_modes()
        if position is None:
            position = self.z[-1]
        index = np.argmin(np.abs(self.z - position))
        if position > np.max(self.z) or position < np.min(self.z):
            print("WARNING: position ", position, "m is out of range")
        wvl = 2 * np.pi * c / self.omega[::-1]
        wvlSpectrum = np.abs(self.fieldFT[index, ::-1])**2 * (2 * np.pi * c/wvl**2 )
        return wvl, wvlSpectrum


    def get_spectral_phase(self, position=None):
        """Get the spectral phase from the Luna result file

        Args:
            position (float): position along the fiber in m. If None, the end of the fiber is used.

        Returns:
            wvl (numpy.ndarray): wavelength axis in m
            phase (numpy.ndarray): spectral phase in rad
        """
        self.average_modes()
        if position is None:
            position = self.z[-1]
        index = np.argmin(np.abs(self.z - position))
        if position > np.max(self.z) or position < np.min(self.z):
            print("WARNING: position ", position, "m is out of range")
        wvl = 2 * np.pi * c / self.omega[::-1]
        phase = np.angle(self.fieldFT[index, ::-1])
        return wvl, phase

    def plot_propagation(self, mode: int = None, normalize_spectra: bool = False, wavelength_representation: bool = True, logscale: bool = False):
        """Plots the propagation of the field in the Luna result file.

        Args:
            mode (int): mode to plot. If None, the average of all modes is plotted.
        """
        if mode is not None:
            self.select_mode(mode)
        else:
            self.average_modes()
        if self.fieldFT is None or self.omega is None or self.z is None:
            print("ERROR: No field data loaded")
            return
        fig, ax = plt.subplots()
        if wavelength_representation:
            wvl = 2 * np.pi * c / self.omega[self.omega != 0]
            if normalize_spectra:
                spectral_data = copy.deepcopy(np.abs(self.fieldFT[:, self.omega != 0])**2 * (2 * np.pi * c / wvl**2))
                for spectrum in spectral_data:
                    spectrum /= np.max(spectrum)
            else:
                spectral_data = np.abs(self.fieldFT[:,self.omega != 0])**2 * (2 * np.pi * c / wvl**2)
            if logscale:
                spectral_data = np.log(spectral_data + np.max(spectral_data) * 1e-10)
            ax.pcolormesh(wvl/1e-9, self.z, spectral_data, shading='nearest')
            ax.set_xlabel("wavelength (nm)")
            ax.set_ylabel("position along the fiber (m)")
            ax.set_xlim([40, 1200])
        else:
            if normalize_spectra:
                spectral_data = copy.deepcopy(np.abs(self.fieldFT)**2)
                for spectrum in spectral_data:
                    spectrum /= np.max(spectrum)
            else:
                spectral_data = np.abs(self.fieldFT)**2
            if logscale:
                spectral_data = np.log(spectral_data + np.max(spectral_data) * 1e-10)
            ax.pcolormesh(self.omega/2/np.pi/1e15, self.z, spectral_data, shading='nearest')
            ax.set_xlabel("frequency (PHz)")
            ax.set_ylabel("position along the fiber (m)")
            ax.set_xlim([0.02, 3.0])
        return fig

    def plot_stats(self):
        """Plots the 'stats_' attributes of the simulation stored in the present object."""

        fig, axs = plt.subplots(2, 2, figsize=[7, 5])
        axs[0,0].plot(self.stats_z, self.stats_pressure)
        axs[0,0].set_xlabel("z (m)")
        axs[0,0].set_ylabel("gas pressure (bar)")
        ax2 = axs[0,0].twinx()
        ax2.plot(self.stats_z, self.stats_density, color='r')
        ax2.set_ylabel('gas particle density ($m^{-3}$)', color='r')
        ax2.tick_params(axis='y', colors='r')
        ax2.yaxis.label.set_color('r')
        axs[0,1].plot(self.stats_z, self.stats_electrondensity)
        axs[0,1].set_xlabel("z (m)")
        axs[0,1].set_ylabel("electron density ($m^{-3}$)")
        ax2 = axs[0,1].twinx()
        if len(self.stats_energy.shape) == 2:
            ax2.plot(self.stats_z, np.sum(self.stats_energy, axis=1)*1e6, color='r')
        else:
            ax2.plot(self.stats_z, self.stats_energy*1e6, color='r')
        ax2.set_ylabel('pulse energy ($\mu J$)', color='r')
        ax2.tick_params(axis='y', colors='r')
        ax2.yaxis.label.set_color('r')
        if self.stats_peakpower is not None:
            if len(self.stats_peakpower.shape) ==2:
                axs[1,0].plot(self.stats_z, self.stats_peakpower[:, 0])
                axs[1,0].set_xlabel("z (m)")
                axs[1,0].set_ylabel("peak power (W)")
            elif len(self.stats_peakpower.shape) ==1:
                axs[1,0].plot(self.stats_z, self.stats_peakpower)
                axs[1,0].set_xlabel("z (m)")
                axs[1,0].set_ylabel("peak power (W)")
        axs[1,1].plot(self.stats_z, self.stats_peak_ionization_rate)
        axs[1,1].set_xlabel("z (m)")
        axs[1,1].set_ylabel("peak ionization rate")
        plt.tight_layout()

        return fig
