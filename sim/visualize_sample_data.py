import numpy as np
import matplotlib.pyplot as plt


def iq_plot(
    time_sec,
    re_signal,
    im_signal,
    n_samples,
):
    plt.figure()
    plt.subplot(1, 1, 1)
    plt.xlabel("Time (usec)")
    plt.grid()
    plt.plot(time_sec[:n_samples], re_signal[:n_samples], "y-o", label="I signal")
    plt.plot(time_sec[:n_samples], im_signal[:n_samples], "g-o", label="Q signal")

    plt.legend()


def plot_fft(
    samples,
    in_signal,
    n_samples,
):
    plt.figure()
    plt.subplot(1, 1, 1)
    plt.xlabel("Frequency")
    plt.grid()
    plt.plot(samples[:n_samples], in_signal[:n_samples], "y-", label="Signal")
    # plt.plot(time_sec[:n_samples]*1e6,in_signal[:n_samples],'y-',label='Signal')
    plt.legend()


# Set capture parameters
fs = 24

# Load the samples
wave = np.fromfile("samples.dat", dtype=np.int16)
n_samples = len(wave) // 2

print("Number of samples: ", n_samples)

T = n_samples / fs

# Time vector in seconds
t = np.linspace(0, T, n_samples, endpoint=False)

imag = wave[::2]
real = wave[1::2]

iq_plot(t, real, imag, n_samples)

plt.show()

# c_data = np.array(real) + 1j * np.array(imag)
# z = np.fft.fft(c_data, n_samples)
# ns = np.linspace(0, fs, n_samples, endpoint=False)
# plot_fft(ns, abs(z), n_samples)

# plt.show()
