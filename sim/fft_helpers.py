import numpy as np
import matplotlib.pyplot as plt


def generate_sample_data(fs: int, f0: int, f1: int, num_samples: int):
    """
    Generate complex waveform data for FFT: the first 16 bits for the real part,
    the second 16 bits for the imaginary part, each represented as a 32-bit complex number.
    """
    # Time vector
    t = np.arange(num_samples) / fs

    # Generate the real and imaginary parts as sine waves
    real_part = np.sin(2 * np.pi * f0 * t) + np.sin(2 * np.pi * f1 * t)

    real_part /= 2

    # Scale the real part to 16-bit integer rang
    real_int = np.int16(np.round(real_part * (2**15 - 1)))

    # Combine the real and imaginary parts into a single 32-bit complex sample array
    complex_samples = np.uint32(real_int) << 16

    return complex_samples


def get_results_fft(values):
    magnitudes = []

    # Extract real and imaginary parts
    for real_part, imag_part in values:

        if real_part > 2**15:
            real_part -= 2**16
        if imag_part > 2**15:
            imag_part -= 2**16

        real_part = np.int32(real_part)
        imag_part = np.int32(imag_part)

        magnitudes.append(np.sqrt(real_part**2 + imag_part**2))

    return magnitudes


def plot_results(values, num_samples, fs):

    magnitudes = get_results_fft(values)

    freqs = np.fft.fftfreq(num_samples, 1 / fs)

    # Plot the FFT
    plt.figure(figsize=(10, 6))
    plt.plot(
        freqs[: num_samples // 2],
        magnitudes[: num_samples // 2],
        label="FFT",
        color="b",
    )
    plt.title("FFT of the Signal")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude")
    plt.legend()
    plt.grid(True)
    plt.show()


def plot_waveform(complex_samples, num_samples, fs):
    # Extract real part
    real_part = (complex_samples >> 16) & 0xFFFF  # Shift and mask to get the real part
    real_part = np.int16(real_part)

    # Plot the real part (time domain)
    plt.figure(figsize=(10, 6))
    plt.subplot(2, 1, 1)
    plt.plot(real_part, label="Wave", color="b", alpha=0.7)
    plt.title("Generated Sine Wave - Time Domain")
    plt.xlabel("Sample Index")
    plt.ylabel("Amplitude")
    plt.legend()
    plt.grid(True)

    # Compute the FFT of the real part (frequency domain)
    fft_result = np.fft.fft(real_part)
    fft_freq = np.fft.fftfreq(num_samples, 1 / fs)

    # Plot the magnitude of the FFT (frequency domain)
    plt.subplot(2, 1, 2)
    plt.plot(
        fft_freq[: num_samples // 2],
        np.abs(fft_result)[: num_samples // 2],
        label="FFT",
        color="r",
    )
    plt.title("FFT of the Signal - Frequency Domain")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude")
    plt.legend()
    plt.grid(True)

    # Show the plots
    plt.tight_layout()
    plt.show()
