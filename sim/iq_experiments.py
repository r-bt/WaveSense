import numpy as np
import matplotlib.pyplot as plt


def generate_iq_samples(frequency, sample_rate, duration):
    """
    Generate IQ samples for a sine wave.

    :param frequency: Frequency of the sine wave in Hz
    :param sample_rate: Sampling rate in Hz
    :param duration: Duration of the signal in seconds
    :return: Tuple of I and Q components (arrays)
    """
    t = np.arange(0, duration, 1 / sample_rate)  # Time vector
    i_samples = np.cos(2 * np.pi * frequency * t)  # In-phase component
    q_samples = np.sin(2 * np.pi * frequency * t)  # Quadrature component
    return i_samples, q_samples


# Parameters
frequency = 500  # Frequency of the sine wave (1 kHz)
sample_rate = 10000  # Sampling rate (10 kHz)
duration = 0.01  # Duration of the signal (10 ms)

# Generate IQ samples
i_samples, q_samples = generate_iq_samples(frequency, sample_rate, duration)
